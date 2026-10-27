import unittest
import json
from unittest.mock import patch
import sys
import os
import inspect

from smolagents import LiteLLMModel

# Aleksa: Only solution which worked for me so far
currentdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
parentdir = os.path.dirname(currentdir)
sys.path.insert(0, parentdir)

from agent_system import single_agent


class FakePubMedClient:
    # Provide deterministic evidence records so integration-style tests never call PubMed.
    def search(self, query):
        return ([{
            "pmid": "12345678",
            "title": "Mock GBM evidence",
            "abstract": "The study reports a mock finding for software testing.",
            "journal": "Test Journal",
            "publication_date": "2025",
            "publication_types": ["Review"],
            "doi": "10.0000/mock",
            "url": "https://pubmed.ncbi.nlm.nih.gov/12345678/",
            "source": "PubMed",
            "evidence_level": "abstract_only",
            "retraction_flags": [],
        }], {})


class SingleAgentPipelineTests(unittest.TestCase):
    # Use a placeholder model; test methods replace agent.run before any model call.
    def setUp(self):
        model = LiteLLMModel(model_id="gemini/gemini-3.6-flash", api_key="test-key")
        self.pipeline = single_agent.SingleAgentPipeline(model=model)

    def test_all_pipeline_tools_belong_to_one_agent(self):
        # Patient phase uses the exact decorated tool objects already shared by the agents.
        self.assertEqual(set(self.pipeline._tool_functions), {"retrieve_patient", "search_patient_records"})
        self.assertIs(self.pipeline.agent.tools["retrieve_patient"], single_agent.retrieve_patient)
        self.assertIs(self.pipeline.agent.tools["search_patient_records"], single_agent.search_patient_records)
        self.assertIn("final_answer", self.pipeline.agent.tools)

    def test_phase_tool_swap_keeps_the_same_agent(self):
        # Changing the registry must not create a second model-backed agent.
        agent = self.pipeline.agent
        self.pipeline._set_phase_tools("patient", [
            single_agent.retrieve_patient,
            single_agent.search_patient_records,
        ])
        self.assertIs(self.pipeline.agent, agent)
        self.assertIs(self.pipeline.agent.tools["retrieve_patient"], single_agent.retrieve_patient)

    def test_ambiguous_patient_search_does_not_choose_a_record(self):
        # A multi-match response should fail closed rather than select a patient.
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

    def test_unknown_patient_stops_before_evidence_and_report(self):
        # An unknown explicit ID must not advance into external or report stages.
        result = self.pipeline.run("Generate a report for PatientID_9999")
        self.assertEqual(result["patient_information"]["status"], "failed")
        self.assertEqual(result["medical_evidence"]["status"], "pending")
        self.assertEqual(result["report"]["status"], "pending")

    def test_mocked_run_reaches_verified_report(self):
        # Drive the original phase tools directly to check state transitions end to end.
        self.pipeline.pubmed_client = FakePubMedClient()

        def run_current_phase(_task, **_kwargs):
            tools = self.pipeline._tool_functions
            if self.pipeline.phase == "evidence":
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
        # Confirm the final object remains JSON-serializable and includes assembled report text.
        output = json.loads(json.dumps(result, ensure_ascii=False, default=str))
        self.assertEqual(output["patient_information"]["patient_data"][0]["Patient_ID"], "PatientID_0003")
        self.assertEqual(output["report"]["status"], "success")
        self.assertIn("GBM Decision-Support Report", output["report"]["content"])


if __name__ == "__main__":
    unittest.main()