import unittest
import json
from unittest.mock import patch
import sys
import os
import inspect
import xml.etree.ElementTree as ET

import pytest
from smolagents import Model

# Add the repository root so this test can import the application package.
currentdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
parentdir = os.path.dirname(currentdir)
sys.path.insert(0, parentdir)

from agent_system.single_agent import single_agent


# Reuse fixed identifiers and patient data so every test gets repeatable inputs.
PMID = "12345678"
ABSTRACT = "The study reports a mock finding for software testing."
PATIENT = {
    "Patient_ID": "PatientID_0003",
    "Primary Diagnosis": "GBM",
    "Age at diagnosis": 79,
    "Sex at Birth": "Male",
    "Grade of Primary Brain Tumor": "IV",
}


class NeverCalledModel(Model):
    """Model placeholder that makes accidental model calls fail immediately."""

    def __init__(self):
        super().__init__(model_id="deterministic-test-model")

    def generate(self, messages, stop_sequences=None, response_format=None,
                 tools_to_call_from=None, **kwargs):
        raise AssertionError("Tests must not call a live or scripted language model.")


class FakePubMedClient:
    # Return one fixed record so evidence tests do not contact PubMed.
    def search(self, query):
        return ([{
            "pmid": "12345678",
            "title": "Mock GBM evidence",
            "abstract": ABSTRACT,
            "journal": "Test Journal",
            "publication_date": "2025",
            "publication_types": ["Review"],
            "doi": "10.0000/mock",
            "url": "https://pubmed.ncbi.nlm.nih.gov/12345678/",
            "source": "PubMed",
            "evidence_level": "abstract_only",
            "retraction_flags": [],
        }], {})


class FailingPubMedClient:
    # Simulate an upstream service error for evidence failure-path checks.
    def search(self, query):
        raise RuntimeError("Synthetic PubMed outage")


# Construct the real pipeline around a model that prevents accidental inference calls.
def make_pipeline(*, max_revisions=2, pubmed_client=None):
    return single_agent.SingleAgentPipeline(
        model=NeverCalledModel(), max_revisions=max_revisions, pubmed_client=pubmed_client
    )


# Mark patient lookup complete when testing a later pipeline phase in isolation.
def set_patient_state(pipeline, patient=None):
    pipeline.state = single_agent.create_initial_state("Generate a test report")
    pipeline.state["patient_information"].update(
        request_type="individual_patient",
        patient_data=[patient or PATIENT],
        data_source="test fixture",
        status="success",
        error=None,
    )


# Build a complete synthetic upstream state for CDS, verification, and report checks.
def ready_state():
    state = single_agent.create_initial_state("Generate a test report")
    state["patient_information"].update(
        request_type="individual_patient", patient_data=[PATIENT],
        data_source="test fixture", status="success", error=None,
    )
    state["medical_evidence"].update(
        search_queries=["synthetic query"], retrieved_evidence=FakePubMedClient().search("test")[0],
        search_attempts=1,
        evidence_relevance=[{
            "pmid": PMID, "relevance": "high", "rationale": "Synthetic test evidence.",
            "supporting_quote": ABSTRACT, "limitations": "Synthetic evidence only.",
        }],
        status="success", error=None,
    )
    state["clinical_decision_support"].update(
        clinical_considerations=[{
            "consideration": "Synthetic consideration",
            "reasoning": "Recorded for a software test.",
            "context": "Synthetic patient context.",
            "limitations": "Not clinical evidence.",
            "supporting_evidence": [PMID],
            "requires_clinician_review": True,
        }],
        treatment_pathways=[],
        supporting_evidence=[],
        uncertainties=["Synthetic test uncertainty."],
        doctor_review_items=[{"item": "Clinician review", "reason": "Required for test output."}],
        status="success", error=None,
    )
    return state


# Replace model behavior with tool calls that read each citation before recording a verdict.
def approve_semantic_items(pipeline, verdict="supported"):
    """Script the verifier by reading each citation before recording its verdict."""
    def run_verification(_task, **_kwargs):
        tools = pipeline._tool_functions
        for item in pipeline.semantic_session.citable_items():
            read = tools["get_cited_evidence"].forward(
                item_type=item["item_type"], number=item["number"]
            )
            assert read["success"]
            recorded = tools["record_verdict"].forward(
                item_type=item["item_type"], number=item["number"],
                verdict=verdict, reason="Deterministic software-test verdict.",
            )
            assert recorded["success"]
    pipeline.agent.run = run_verification


class SingleAgentPipelineTests(unittest.TestCase):
    # Give each unittest method a fresh pipeline with the no-call model.
    def setUp(self):
        self.pipeline = make_pipeline()

    # Inspect the initial registry and confirm the shared patient tool objects are installed.
    def test_all_pipeline_tools_belong_to_one_agent(self):
        self.assertEqual(set(self.pipeline._tool_functions), {"retrieve_patient", "search_patient_records"})
        self.assertIs(self.pipeline.agent.tools["retrieve_patient"], single_agent.retrieve_patient)
        self.assertIs(self.pipeline.agent.tools["search_patient_records"], single_agent.search_patient_records)
        self.assertIn("final_answer", self.pipeline.agent.tools)

    # Swap the phase registry and confirm the existing agent instance remains active.
    def test_phase_tool_swap_keeps_the_same_agent(self):
        agent = self.pipeline.agent
        self.pipeline._set_phase_tools("patient", [
            single_agent.retrieve_patient,
            single_agent.search_patient_records,
        ])
        self.assertIs(self.pipeline.agent, agent)
        self.assertIs(self.pipeline.agent.tools["retrieve_patient"], single_agent.retrieve_patient)

    # Replace patient search with a two-record result to exercise ambiguous lookup handling.
    def test_ambiguous_patient_search_does_not_choose_a_record(self):
        self.pipeline.state = single_agent.create_initial_state("Find a patient")
        self.pipeline.agent.run = lambda _task: '{"age_min": 79, "age_max": 79, "sex": "Male"}'
        matches = [{"Patient_ID": "PatientID_0003"}, {"Patient_ID": "PatientID_0004"}]
        with patch.object(single_agent.search_patient_records, "forward", return_value={
            "success": True,
            "count": 2,
            "patients": matches,
        }):
            success = self.pipeline._run_patient_phase("Find a male patient aged 79")
        self.assertFalse(success)
        self.assertIsNone(self.pipeline.patient_result)
        self.assertIn("2 matches", self.pipeline.state["patient_information"]["error"])

    # Run an unknown explicit ID and inspect which downstream stages remain untouched.
    def test_unknown_patient_stops_before_evidence_and_report(self):
        result = self.pipeline.run("Generate a report for PatientID_9999")
        self.assertEqual(result["patient_information"]["status"], "failed")
        self.assertEqual(result["medical_evidence"]["status"], "pending")
        self.assertEqual(result["report"]["status"], "pending")

    # Script each active phase through its real tools to exercise a complete pipeline run.
    def test_mocked_run_reaches_verified_report(self):
        self.pipeline.pubmed_client = FakePubMedClient()

        def run_current_phase(_task, **_kwargs):
            tools = self.pipeline._tool_functions
            if self.pipeline.phase == "evidence":
                # Retrieve one synthetic record and attach an exact-quote assessment.
                found = tools["search_medical_evidence"].forward(query="glioblastoma treatment")
                self.assertTrue(found["success"])
                assessed = tools["assess_evidence"].forward(
                    pmid="12345678",
                    relevance="high",
                    rationale="Mock assessment for testing.",
                    supporting_quote="The study reports a mock finding for software testing.",
                    limitations="Mock data do not provide clinical evidence.",
                )
                self.assertTrue(assessed["success"])
            elif self.pipeline.phase == "cds":
                # Record one consideration, one pathway, and one uncertainty.
                self.assertTrue(tools["record_clinical_consideration"].forward(
                    consideration="Mock consideration",
                    reasoning="Recorded only to exercise the report workflow.",
                    context_info="Mock patient context.",
                    supporting_evidence=["12345678"],
                    limitations="This mock output is not medical advice.",
                )["success"])
                self.assertTrue(tools["record_treatment_pathway"].forward(
                    option="Mock pathway",
                    when_considered="Testing only.",
                    supporting_evidence=["12345678"],
                    unknown_patient_factors="All clinical factors are unknown in this test.",
                    risks_and_limitations="Mock pathway; clinician decision required.",
                )["success"])
                self.assertTrue(tools["record_uncertainty"].forward(
                    description="This is a software test with mock evidence."
                )["success"])
            elif self.pipeline.phase == "verification":
                # Run structural checks, then read and approve every citable item.
                self.assertTrue(tools["run_verification_checks"].forward()["passed"])
                for item in self.pipeline.semantic_session.citable_items():
                    read = tools["get_cited_evidence"].forward(
                        item_type=item["item_type"], number=item["number"]
                    )
                    self.assertTrue(read["success"])
                    self.assertTrue(tools["record_verdict"].forward(
                        item_type=item["item_type"],
                        number=item["number"],
                        verdict="supported",
                        reason="Mock test flow; no clinical conclusion is implied.",
                    )["success"])
            elif self.pipeline.phase == "report":
                # Assemble the previously validated report sections in canonical order.
                self.assertTrue(tools["assemble_report"].forward(
                    section_order=single_agent.REPORT_SECTION_ORDER
                )["success"])

        self.pipeline.agent.run = run_current_phase
        result = self.pipeline.run("Generate a report for PatientID_0003")
        self.assertEqual(result["verification"]["verification_status"], "approved", result["verification"])
        self.assertEqual(result["report"]["status"], "success")
        self.assertIn("PMID 12345678", result["report"]["content"])
        content = result["report"]["content"]
        self.assertIn("**DRAFT — FOR CLINICIAN REVIEW**", content)
        self.assertIn("**Consideration:** Mock consideration", content)
        self.assertIn("**Possible pathway:** Mock pathway", content)
        self.assertIn("**Clinician review:** Required.", content)
        headings = ["Patient Context", "Clinical Considerations", "Treatment Pathways",
                "Uncertainties", "Doctor Review Items", "References"]
        positions = [content.index("## " + heading) for heading in headings]
        self.assertEqual(positions, sorted(positions))
        # Round-trip the result to confirm it can be serialized for API or file output.
        output = json.loads(json.dumps(result, ensure_ascii=False, default=str))
        self.assertEqual(output["patient_information"]["patient_data"][0]["Patient_ID"], "PatientID_0003")
        self.assertEqual(output["report"]["status"], "success")
        self.assertIn("GBM Decision-Support Report", output["report"]["content"])


# Start patient lookup from pending state and compare its stored record with the dataset.
def test_patient_phase_retrieves_exact_record():
    pipeline = make_pipeline()
    pipeline.state = single_agent.create_initial_state("Generate a test report")

    assert pipeline._run_patient_phase("Generate a report for patient 3")
    expected = single_agent.retrieve_patient.forward(patient_id="PatientID_0003")["patient"]
    assert pipeline.state["patient_information"]["patient_data"] == [expected]
    assert pipeline.state["patient_information"]["status"] == "success"


# Script filter extraction and intercept search to inspect the exact filters and result.
def test_patient_phase_accepts_one_filter_match(monkeypatch):
    pipeline = make_pipeline()
    pipeline.state = single_agent.create_initial_state("Generate a test report")
    pipeline.agent.run = lambda _task: '{"age_min": 79, "age_max": 79, "sex": "Male"}'
    calls = []

    # Capture the search arguments and return one matching synthetic patient.
    def search(**filters):
        calls.append(filters)
        return {"success": True, "count": 1, "patients": [PATIENT]}

    monkeypatch.setattr(single_agent.search_patient_records, "forward", search)

    assert pipeline._run_patient_phase("Find a male patient aged 79")
    assert calls == [{
        "age_min": 79, "age_max": 79, "sex": "Male", "progression": None,
        "death_recorded": None,
    }]
    assert pipeline.state["patient_information"]["patient_data"] == [PATIENT]


# Exercise malformed JSON, a JSON array, and an empty object as filter-extraction responses.
@pytest.mark.parametrize("response", ["not-json", "[]", "{}"])
def test_patient_phase_rejects_missing_or_malformed_filters(response):
    pipeline = make_pipeline()
    pipeline.state = single_agent.create_initial_state("Generate a test report")
    pipeline.agent.run = lambda _task: response

    assert not pipeline._run_patient_phase("Find a suitable patient")
    assert pipeline.state["patient_information"]["status"] == "failed"
    assert pipeline.state["patient_information"]["patient_data"] == []


# Drive evidence search and assessment tools against the fixed fake PubMed record.
def test_evidence_phase_records_search_and_assessment():
    pipeline = make_pipeline(pubmed_client=FakePubMedClient())
    set_patient_state(pipeline)

    def run_evidence(_task, **_kwargs):
        # Call both evidence tools with arguments tied to the fake record.
        tools = pipeline._tool_functions
        found = tools["search_medical_evidence"].forward(query="glioblastoma treatment")
        assert found["success"]
        assessed = tools["assess_evidence"].forward(
            pmid=PMID, relevance="high", rationale="Synthetic assessment.",
            supporting_quote=ABSTRACT, limitations="Synthetic test evidence.",
        )
        assert assessed["success"]

    pipeline.agent.run = run_evidence

    assert pipeline._run_evidence_phase()
    evidence = pipeline.state["medical_evidence"]
    assert evidence["status"] == "success"
    assert evidence["search_attempts"] == 1
    assert [item["pmid"] for item in evidence["evidence_relevance"]] == [PMID]


# Omit assessment on the first pass, then handle the pipeline's recovery prompt.
def test_evidence_phase_recovers_unassessed_retrieved_record():
    pipeline = make_pipeline(pubmed_client=FakePubMedClient())
    set_patient_state(pipeline)
    calls = 0

    def skip_then_assess(_task, **_kwargs):
        nonlocal calls
        calls += 1
        if calls == 1:
            # First pass retrieves evidence but leaves it unassessed.
            found = pipeline._tool_functions["search_medical_evidence"].forward(query="glioblastoma")
            assert found["success"]
            return
        # Recovery pass assesses the outstanding PMID.
        assessed = pipeline._tool_functions["assess_evidence"].forward(
            pmid=PMID, relevance="high", rationale="Recovered assessment.",
            supporting_quote=ABSTRACT, limitations="Synthetic test evidence.",
        )
        assert assessed["success"]

    pipeline.agent.run = skip_then_assess

    assert pipeline._run_evidence_phase()
    assert calls == 2
    assert pipeline.state["medical_evidence"]["status"] == "success"


# Use a client that raises to check how the evidence phase records a search failure.
def test_evidence_phase_fails_closed_when_search_fails():
    pipeline = make_pipeline(pubmed_client=FailingPubMedClient())
    set_patient_state(pipeline)
    pipeline.agent.run = lambda _task, **_kwargs: pipeline._tool_functions[
        "search_medical_evidence"
    ].forward(query="glioblastoma")

    assert not pipeline._run_evidence_phase()
    assert pipeline.state["medical_evidence"]["status"] == "failed"
    assert pipeline.state["medical_evidence"]["retrieved_evidence"] == []


# Exercise all three CDS recording tools and inspect the completed session output.
def test_cds_phase_records_consideration_pathway_and_uncertainty():
    pipeline = make_pipeline()
    pipeline.state = ready_state()

    def record_cds(_task, **_kwargs):
        # Build a cited consideration, a review-required pathway, and an uncertainty.
        tools = pipeline._tool_functions
        assert tools["record_clinical_consideration"].forward(
            consideration="Synthetic consideration",
            reasoning="Recorded for a software test.", context_info="Synthetic context.",
            supporting_evidence=[PMID], limitations="Not clinical evidence.",
        )["success"]
        assert tools["record_treatment_pathway"].forward(
            option="Synthetic pathway", when_considered="Testing only.",
            supporting_evidence=[PMID], unknown_patient_factors="All factors are unknown.",
            risks_and_limitations="Clinician review required.",
        )["success"]
        assert tools["record_uncertainty"].forward(
            description="Synthetic uncertainty."
        )["success"]

    pipeline.agent.run = record_cds

    assert pipeline._run_cds_phase(None, None, None)
    cds = pipeline.state["clinical_decision_support"]
    assert cds["status"] == "success"
    assert len(cds["clinical_considerations"]) == 1
    assert len(cds["treatment_pathways"]) == 1
    assert "Synthetic uncertainty." in cds["uncertainties"]
    assert all(item["requires_clinician_review"] for item in cds["treatment_pathways"])


# Attempt to record a citation that is absent from the synthetic retrieved-evidence set.
def test_cds_phase_rejects_unretrieved_citation():
    pipeline = make_pipeline()
    pipeline.state = ready_state()

    def add_invalid_citation(_task, **_kwargs):
        result = pipeline._tool_functions["record_clinical_consideration"].forward(
            consideration="Invalid citation test", reasoning="Testing citation validation.",
            context_info="Synthetic context.", supporting_evidence=["99999999"],
            limitations="Synthetic test.",
        )
        assert not result["success"]
        assert "not found" in result["error"]

    pipeline.agent.run = add_invalid_citation

    assert not pipeline._run_cds_phase(None, None, None)
    assert pipeline.state["clinical_decision_support"]["status"] == "failed"


# Leave the CDS session empty and inspect the resulting phase status.
def test_cds_phase_fails_when_agent_records_no_items():
    pipeline = make_pipeline()
    pipeline.state = ready_state()
    pipeline.agent.run = lambda _task, **_kwargs: None

    assert not pipeline._run_cds_phase(None, None, None)
    assert pipeline.state["clinical_decision_support"]["status"] == "failed"


# Read cited evidence and record a supported semantic verdict through verification tools.
def test_verification_phase_approves_supported_cited_item():
    pipeline = make_pipeline()
    pipeline.state = ready_state()
    approve_semantic_items(pipeline)

    assert pipeline._run_verification_phase()
    result = pipeline.state["verification"]
    assert result["verification_status"] == "approved"
    assert result["semantic_checks"][0]["verdict"] == "supported"


# Reuse the verification helper with an unsupported verdict and inspect the generated issue.
def test_verification_phase_requires_revision_for_unsupported_item():
    pipeline = make_pipeline()
    pipeline.state = ready_state()
    approve_semantic_items(pipeline, verdict="unsupported")

    assert not pipeline._run_verification_phase()
    result = pipeline.state["verification"]
    assert result["revision_required"] is True
    assert any("does not support" in issue for issue in result["issues"])


# Leave a cited claim unchecked so the phase must report incomplete semantic verification.
def test_verification_phase_fails_if_semantic_item_is_unchecked():
    pipeline = make_pipeline()
    pipeline.state = ready_state()
    pipeline.agent.run = lambda _task, **_kwargs: None

    with pytest.raises(ValueError, match="Semantic verification incomplete"):
        pipeline._run_verification_phase()


# Prepare approved upstream state and assemble its validated report sections.
def test_report_phase_assembles_validated_sections():
    pipeline = make_pipeline()
    pipeline.state = ready_state()
    pipeline.state["verification"].update(
        verification_status="approved", issues=[], revision_required=False,
        semantic_checks=[{
            "item_type": "consideration", "number": 1, "verdict": "supported",
            "reason": "Synthetic test verdict.",
        }],
        status="success", error=None,
    )

    def assemble(_task, **_kwargs):
        result = pipeline._tool_functions["assemble_report"].forward(
            section_order=single_agent.REPORT_SECTION_ORDER
        )
        assert result["success"]

    pipeline.agent.run = assemble
    pipeline._run_report_phase()

    report = pipeline.state["report"]
    assert report["status"] == "success"
    assert "Synthetic consideration" in report["content"]
    assert "PMID 12345678" in report["content"]


# Check both an invalid section order and no assembly call using the same report setup.
@pytest.mark.parametrize("mode", ["invalid-order", "skip-assembly"])
def test_report_phase_does_not_succeed_without_valid_assembly(mode):
    pipeline = make_pipeline()
    pipeline.state = ready_state()
    pipeline.state["verification"].update(
        verification_status="approved", issues=[], revision_required=False,
        semantic_checks=[{
            "item_type": "consideration", "number": 1, "verdict": "supported",
            "reason": "Synthetic test verdict.",
        }],
        status="success", error=None,
    )

    if mode == "invalid-order":
        # Ask the report tool to assemble sections in reverse order.
        def invalid_order(_task, **_kwargs):
            result = pipeline._tool_functions["assemble_report"].forward(
                section_order=list(reversed(single_agent.REPORT_SECTION_ORDER))
            )
            assert not result["success"]
        pipeline.agent.run = invalid_order
    else:
        # Simulate an agent that finishes without calling the assembly tool.
        pipeline.agent.run = lambda _task, **_kwargs: None

    with pytest.raises(ValueError, match="did not successfully assemble"):
        pipeline._run_report_phase()


# Run two patient requests through one instance while tracking fresh evidence sessions.
def test_pipeline_reuse_resets_sessions_and_request_state():
    pipeline = make_pipeline(pubmed_client=FakePubMedClient())
    evidence_searches = 0

    def run_phase(_task, **_kwargs):
        nonlocal evidence_searches
        tools = pipeline._tool_functions
        if pipeline.phase == "evidence":
            # Each request performs its own retrieval and evidence assessment.
            evidence_searches += 1
            assert tools["search_medical_evidence"].forward(query="glioblastoma")["success"]
            assert tools["assess_evidence"].forward(
                pmid=PMID, relevance="high", rationale="Synthetic.",
                supporting_quote=ABSTRACT, limitations="Synthetic.",
            )["success"]
        elif pipeline.phase == "cds":
            # Include the run number in each consideration to expose state leakage.
            assert tools["record_clinical_consideration"].forward(
                consideration=f"Consideration {evidence_searches}", reasoning="Synthetic.",
                context_info="Test context.", supporting_evidence=[PMID], limitations="Synthetic.",
            )["success"]
        elif pipeline.phase == "verification":
            # Verify each newly created citable item before the report phase.
            for item in pipeline.semantic_session.citable_items():
                assert tools["get_cited_evidence"].forward(
                    item_type=item["item_type"], number=item["number"]
                )["success"]
                assert tools["record_verdict"].forward(
                    item_type=item["item_type"], number=item["number"], verdict="supported",
                    reason="Synthetic.",
                )["success"]
        elif pipeline.phase == "report":
                # Assemble each run's report from that run's validated state.
            assert tools["assemble_report"].forward(
                section_order=single_agent.REPORT_SECTION_ORDER
            )["success"]

    pipeline.agent.run = run_phase
    first = pipeline.run("Generate a report for PatientID_0003")
    first_report = first["report"]["content"]
    second = pipeline.run("Generate a report for PatientID_0004")

    assert first["report"]["status"] == second["report"]["status"] == "success"
    assert first["patient_information"]["patient_data"][0]["Patient_ID"] == "PatientID_0003"
    assert second["patient_information"]["patient_data"][0]["Patient_ID"] == "PatientID_0004"
    assert "Consideration 1" in first_report
    assert "Consideration 2" in second["report"]["content"]
    assert evidence_searches == 2


# Keep the file directly runnable as well as discoverable by pytest.
if __name__ == "__main__":
    report_path = os.path.join(currentdir, "single_agent_test_report.xml")
    exit_code = pytest.main([
        __file__, "-v", "-s", f"--junitxml={report_path}"
    ])
    if os.path.exists(report_path):
        # Add readable whitespace while preserving the JUnit XML elements and values.
        report_tree = ET.parse(report_path)
        ET.indent(report_tree, space="  ")
        report_tree.write(report_path, encoding="utf-8", xml_declaration=True)
    raise SystemExit(exit_code)