"""Synthetic software tests for CDS validation; no model or network is required."""
import copy
import importlib.util
import json
from pathlib import Path
import unittest
from unittest.mock import patch


MODULE_PATH = Path(__file__).resolve().parents[1] / "agent_system/multi_agent/clinical_decision_support_agent.py"
SPEC = importlib.util.spec_from_file_location("clinical_decision_support_agent", MODULE_PATH)
cds = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(cds)


def valid_state():
    return {
        "user_request": "Review this synthetic case",
        "patient_information": {"status": "success", "patient_data": [{
            "Patient ID": "SYNTHETIC-PRIVATE", "Primary Diagnosis": "Synthetic diagnosis",
            "Age at diagnosis": 50, "Sex at Birth": "Unknown", "survival": 12,
        }]},
        "medical_evidence": {"status": "success", "retrieved_evidence": [
            {"pmid": "123456", "title": "Synthetic reference"},
            {"pmid": "654321", "title": "Unrelated synthetic reference"},
        ], "evidence_relevance": [
            {"pmid": "123456", "relevance": "high", "supporting_quote": "Synthetic quote",
             "limitations": "Synthetic evidence only"},
            {"pmid": "654321", "relevance": "low"},
        ]},
        "errors": [],
    }


def record_consideration(session, evidence=None, **changes):
    arguments = dict(
        consideration=" Synthetic consideration ", reasoning=" Synthetic reasoning ",
        context_info=" Synthetic context ", supporting_evidence=["123456"] if evidence is None else evidence,
        limitations=" Synthetic limitation ", requires_review=True,
    )
    arguments.update(changes)
    return session.add_consideration(**arguments)


class ClinicalDecisionSupportAgentTests(unittest.TestCase):
    def make_session(self, **kwargs):
        return cds.CDSSession(valid_state()["medical_evidence"]["retrieved_evidence"][:1], **kwargs)

    def test_context_filters_private_outcome_and_irrelevant_data(self):
        state = valid_state()
        state["patient_information"]["patient_data"].append(
            dict(state["patient_information"]["patient_data"][0], **{"Patient ID": "OTHER"}))
        original = copy.deepcopy(state)
        prompt, evidence = cds._context(
            state, clinical_notes="Synthetic notes", verification_feedback=" Correct citation ",
            previous_reports=[{"summary": "Historical context", "Survival": 12, "outcome": "past"}])
        context = json.loads(prompt)
        self.assertEqual(len(context["patient_profiles"]), 1)
        self.assertNotIn("SYNTHETIC-PRIVATE", prompt)
        self.assertNotIn("survival", context["patient_profiles"][0])
        self.assertEqual(context["previous_reports_summary"], [{"summary": "Historical context"}])
        self.assertEqual(context["verification_feedback"], "Correct citation")
        self.assertEqual(context["clinical_notes"], "Synthetic notes")
        self.assertEqual([r["pmid"] for r in evidence], ["123456"])
        self.assertEqual(context["available_evidence"][0]["supporting_quote"], "Synthetic quote")
        self.assertEqual(state, original)

    def test_upstream_validation_clears_stale_success_without_creating_model(self):
        cases = [
            ("patient_information", {"status": "pending"}),
            ("patient_information", {"status": "success", "patient_data": []}),
            ("patient_information", {"status": "success", "patient_data": [None]}),
            ("medical_evidence", {"status": "failed"}),
            ("medical_evidence", {"status": "success", "retrieved_evidence": []}),
        ]
        missing_assessments = copy.deepcopy(valid_state()["medical_evidence"])
        missing_assessments["evidence_relevance"] = None
        cases.append(("medical_evidence", missing_assessments))
        no_useful_evidence = copy.deepcopy(valid_state()["medical_evidence"])
        no_useful_evidence["evidence_relevance"] = []
        cases.append(("medical_evidence", no_useful_evidence))
        for key, value in cases:
            with self.subTest(key=key, value=value):
                state = valid_state()
                state[key] = value
                state["clinical_decision_support"] = {"status": "success"}
                with patch.object(cds, "create_clinical_decision_support_agent") as factory:
                    returned = cds.run_clinical_decision_support_agent(state, model=object())
                factory.assert_not_called()
                self.assertIs(returned, state)
                self.assertEqual(state["clinical_decision_support"]["status"], "failed")
                self.assertTrue(state["clinical_decision_support"]["error"])
                self.assertEqual(len(state["errors"]), 1)

    def test_consideration_deduplicates_citations_and_normalizes_text(self):
        session = self.make_session()
        self.assertTrue(record_consideration(session, ["123456", "123456"])["success"])
        result = session.finish()
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["clinical_considerations"][0]["consideration"], "Synthetic consideration")
        self.assertEqual(result["clinical_considerations"][0]["supporting_evidence"], ["123456"])
        self.assertEqual(result["supporting_evidence"], valid_state()["medical_evidence"]["retrieved_evidence"][:1])

    def test_invalid_considerations_are_not_recorded(self):
        for changes in ({"consideration": " "}, {"reasoning": None}, {"limitations": ""},
                        {"supporting_evidence": "123456"}, {"supporting_evidence": [123456]},
                        {"supporting_evidence": ["654321"]}):
            with self.subTest(changes=changes):
                session = self.make_session()
                self.assertFalse(record_consideration(session, **changes)["success"])
                self.assertEqual(session.considerations, [])

    def test_unsupported_consideration_forces_review_and_defaults_context(self):
        session = self.make_session()
        record_consideration(session, [], requires_review=False, context_info="")
        entry = session.finish()["clinical_considerations"][0]
        self.assertTrue(entry["requires_clinician_review"])
        self.assertEqual(entry["context"], "Not specified.")
        self.assertEqual(len(session.review_items), 2)

    def test_treatment_pathway_requires_review_and_rejects_invalid_input(self):
        session = self.make_session()
        arguments = dict(option="Synthetic option", when_considered="Synthetic condition",
                         supporting_evidence=["123456", "123456"],
                         unknown_patient_factors="Unknown factors", risks_and_limitations="Synthetic risks")
        self.assertTrue(session.add_treatment_pathway(**arguments)["success"])
        result = session.finish()
        self.assertEqual(result["status"], "success")
        self.assertTrue(result["treatment_pathways"][0]["requires_clinician_review"])
        self.assertEqual(result["treatment_pathways"][0]["supporting_evidence"], ["123456"])
        for changes in ({"option": ""}, {"when_considered": None}, {"unknown_patient_factors": " "},
                        {"risks_and_limitations": ""}, {"supporting_evidence": "123456"},
                        {"supporting_evidence": [123456]}, {"supporting_evidence": ["999999"]}):
            with self.subTest(changes=changes):
                self.assertFalse(session.add_treatment_pathway(**(arguments | changes))["success"])
        self.assertEqual(len(session.pathways), 1)

    def test_mri_review_handles_missing_invalid_low_and_boundary_confidence(self):
        cases = [
            (None, "No MRI classification"), ("invalid", "unexpected format"),
            ({}, "label was not provided"),
            ({"label": "Synthetic", "confidence": "high"}, "score was invalid"),
            ({"label": "Synthetic", "confidence": 1.1}, "score was invalid"),
            ({"label": "Synthetic", "confidence": 0.5}, "low-confidence"),
        ]
        for findings, expected in cases:
            with self.subTest(findings=findings):
                session = self.make_session(mri_findings=findings)
                self.assertIn(expected, " ".join(session.uncertainties))
                self.assertTrue(session.review_items)
        session = self.make_session(mri_findings={"classification": "Synthetic", "confidence": 0.7})
        self.assertEqual(session.uncertainties, [])
        self.assertEqual(len(session.review_items), 1)
        for threshold in (0, -0.1, 1.1):
            with self.subTest(threshold=threshold), self.assertRaises(ValueError):
                self.make_session(low_confidence_threshold=threshold)

    def test_finish_requires_output_and_returns_independent_snapshot(self):
        session = self.make_session()
        self.assertEqual(session.finish()["status"], "failed")
        self.assertFalse(session.add_uncertainty(" ")["success"])
        self.assertTrue(session.add_uncertainty(" Synthetic unknown ")["success"])
        self.assertEqual(session.finish()["status"], "failed")
        record_consideration(session)
        result = session.finish()
        result["clinical_considerations"][0]["supporting_evidence"].clear()
        result["supporting_evidence"][0]["title"] = "Changed"
        self.assertEqual(session.finish()["clinical_considerations"][0]["supporting_evidence"], ["123456"])
        self.assertEqual(session.finish()["supporting_evidence"][0]["title"], "Synthetic reference")
        self.assertIn("Synthetic unknown", session.finish()["uncertainties"])

    def test_run_stores_tool_output_preserves_upstream_and_passes_model(self):
        state = valid_state()
        original = copy.deepcopy(state)
        model = object()

        def make_agent(session, model=None):
            class FakeAgent:
                def run(self, prompt):
                    self_context = json.loads(prompt.split("\n", 1)[1])
                    self_test.assertEqual(self_context["verification_feedback"], "Fix draft")
                    record_consideration(session)
                    return "Ignored model text"
            return FakeAgent()

        self_test = self
        with patch.object(cds, "create_clinical_decision_support_agent", side_effect=make_agent) as factory:
            returned = cds.run_clinical_decision_support_agent(state, model=model, verification_feedback="Fix draft")
        self.assertIs(returned, state)
        self.assertIs(factory.call_args.kwargs["model"], model)
        self.assertEqual(state["clinical_decision_support"]["status"], "success")
        self.assertEqual(state["current_agent"], "clinical_decision_support_agent")
        self.assertEqual(state["errors"], [])
        for key in ("patient_information", "medical_evidence"):
            self.assertEqual(state[key], original[key])

    def test_run_preserves_partial_output_and_sanitizes_unexpected_failure(self):
        def make_agent(session, model=None):
            class FailingAgent:
                def run(self, prompt):
                    record_consideration(session)
                    raise RuntimeError("private provider response")
            return FailingAgent()

        state = valid_state()
        with patch.object(cds, "create_clinical_decision_support_agent", side_effect=make_agent):
            cds.run_clinical_decision_support_agent(state, model=object())
        result = state["clinical_decision_support"]
        self.assertEqual(result["status"], "failed")
        self.assertEqual(len(result["clinical_considerations"]), 1)
        self.assertIn("RuntimeError", result["error"])
        self.assertNotIn("private provider response", result["error"])
        self.assertEqual(len(state["errors"]), 1)


if __name__ == "__main__":
    unittest.main()
