"""Synthetic software fixtures; these are not medical evidence or clinical tests."""
import copy
import sys
from pathlib import Path
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1] / "agent_system"),)
from multi_agent import report_generation_agent as report


def valid_state():
    return {
        "patient_information": {"status": "success", "patient_data": [{
            "Patient_ID": "SYNTHETIC-001", "Primary Diagnosis": "GBM",
            "Age at diagnosis": 50, "Sex at Birth": "Unknown",
            "Grade of Primary Brain Tumor": "Not supplied"}]},
        "medical_evidence": {"status": "success", "retrieved_evidence": [{
            "pmid": "123456", "title": "SYNTHETIC test reference",
            "abstract": "Synthetic abstract for software testing only.",
            "publication_types": [], "retraction_flags": [],
            "evidence_level": "abstract_only"}],
            "evidence_relevance": [{"pmid": "123456", "relevance": "high"}]},
        "clinical_decision_support": {"status": "success", "clinical_considerations": [{
            "consideration": "Synthetic consideration", "reasoning": "Synthetic reasoning",
            "context": "Synthetic context", "limitations": "Synthetic limitations",
            "supporting_evidence": ["123456"], "requires_clinician_review": True}],
            "treatment_pathways": [{"option": "Synthetic pathway",
                "when_considered": "Synthetic condition", "unknown_patient_factors": "Unknown",
                "risks_and_limitations": "Synthetic limitation",
                "supporting_evidence": ["123456"], "requires_clinician_review": True}],
            "uncertainties": ["Synthetic uncertainty"],
            "doctor_review_items": [{"item": "Synthetic review", "reason": "Synthetic reason"}]},
        "verification": {"status": "success", "verification_status": "approved",
            "revision_required": False, "issues": [], "error": None,
            "semantic_checks": [{"item_type": kind, "number": 1,
                "verdict": "supported", "reason": "Synthetic supported verdict"}
                for kind in ("consideration", "pathway")]},
        "errors": []}


class ReportTests(unittest.TestCase):
    def run_state(self, state=None, **kwargs):
        return report.run_report_generation_agent(
            valid_state() if state is None else state, use_llm=False, **kwargs)["report"]

    def blocked(self, state):
        result = self.run_state(state)
        self.assertEqual(result["status"], "failed")
        self.assertIsNone(result["content"])
        self.assertTrue(result["error"])

    def test_success_and_citations(self):
        result = self.run_state()
        self.assertEqual(result["status"], "success")
        self.assertIn("Synthetic consideration", result["content"])
        self.assertIn("[PMID 123456](https://pubmed.ncbi.nlm.nih.gov/123456/)", result["content"])
        self.assertEqual(result["content"].count("## References"), 1)

    def test_upstream_unchanged(self):
        state = valid_state()
        original = copy.deepcopy(state)
        self.run_state(state)
        for key in ("patient_information", "medical_evidence", "clinical_decision_support", "verification"):
            self.assertEqual(state[key], original[key])

    def test_verification_gate(self):
        for change in ({"status": "failed"}, {"verification_status": "pending"},
                       {"revision_required": True}, {"issues": ["issue"]}, {"error": "failure"}):
            with self.subTest(change=change):
                state = valid_state(); state["verification"].update(change)
                self.blocked(state)

    def test_preview_is_not_success(self):
        state = valid_state(); state.pop("verification")
        result = self.run_state(state, preview=True)
        self.assertEqual(result["status"], "preview")
        self.assertIn("UNVERIFIED PREVIEW", result["content"])

    def test_failed_upstream(self):
        for key in ("patient_information", "medical_evidence", "clinical_decision_support"):
            with self.subTest(stage=key):
                state = valid_state(); state[key]["status"] = "failed"
                self.blocked(state)

    def test_missing_semantic_verdict(self):
        state = valid_state(); state["verification"]["semantic_checks"].pop()
        self.blocked(state)

    def test_unsupported_verdict(self):
        state = valid_state(); state["verification"]["semantic_checks"][0]["verdict"] = "unsupported"
        self.blocked(state)

    def test_partial_is_explicit_review_item(self):
        state = valid_state(); state["verification"]["semantic_checks"][0]["verdict"] = "partial"
        result = self.run_state(state)
        self.assertEqual(result["status"], "success")
        self.assertIn("Partial evidence support", result["content"])

    def test_duplicate_semantic_verdict(self):
        state = valid_state(); state["verification"]["semantic_checks"].append(
            state["verification"]["semantic_checks"][0])
        self.blocked(state)

    def test_missing_or_low_relevance_citations(self):
        for pmid in ("999999", "123456"):
            state = valid_state()
            state["clinical_decision_support"]["clinical_considerations"][0]["supporting_evidence"] = [pmid]
            state["medical_evidence"]["evidence_relevance"][0]["relevance"] = "low"
            self.blocked(state)

    def test_retracted_evidence(self):
        state = valid_state(); state["medical_evidence"]["retrieved_evidence"][0]["retraction_flags"] = ["RetractionIn"]
        self.blocked(state)

    def test_review_flag(self):
        state = valid_state(); state["clinical_decision_support"]["treatment_pathways"][0]["requires_clinician_review"] = False
        self.blocked(state)

    def test_uncited_consideration(self):
        state = valid_state()
        state["clinical_decision_support"]["clinical_considerations"][0]["supporting_evidence"] = []
        state["verification"]["semantic_checks"].pop(0)
        self.assertEqual(self.run_state(state)["status"], "success")
        state["clinical_decision_support"]["clinical_considerations"][0]["requires_clinician_review"] = False
        self.blocked(state)

    def test_malformed_lists_and_items(self):
        for value in (None, {}, [None], [{"consideration": "Incomplete"}]):
            with self.subTest(value=value):
                state = valid_state(); state["clinical_decision_support"]["clinical_considerations"] = value
                self.blocked(state)

    def test_patient_count(self):
        state = valid_state(); state["patient_information"]["patient_data"] *= 2
        self.blocked(state)

    def test_stale_report_cleared(self):
        state = valid_state(); state["report"] = {"content": "OLD", "status": "success"}
        state["verification"]["status"] = "failed"
        self.blocked(state)

    def test_escaping(self):
        state = valid_state(); state["patient_information"]["patient_data"][0]["Patient_ID"] = "<script>\n# fake heading"
        content = self.run_state(state)["content"]
        self.assertNotIn("<script>", content)
        self.assertIn("&lt;script&gt;", content)
        self.assertNotIn("\n# fake heading", content)

    def test_invalid_section_orders(self):
        session = report.ReportSession(report.prepare_sections(valid_state()))
        for order in ([], report.SECTIONS[:-1], list(reversed(report.SECTIONS)), ["x"] * 6):
            self.assertFalse(session.assemble(order)["success"])
            self.assertIsNone(session.content)

    def test_model_prose_cannot_become_report(self):
        class FakeAgent:
            def run(self, task):
                return "Fabricated report"
        with patch.object(report, "create_report_generation_agent", return_value=FakeAgent()):
            result = report.run_report_generation_agent(valid_state())["report"]
        self.assertEqual(result["status"], "failed")
        self.assertIsNone(result["content"])

    def test_mock_agent_assembly(self):
        def factory(session, model=None):
            class FakeAgent:
                def run(self, task):
                    session.assemble(report.SECTIONS)
                    return "Ignored final prose"
            return FakeAgent()
        with patch.object(report, "create_report_generation_agent", side_effect=factory):
            result = report.run_report_generation_agent(valid_state())["report"]
        self.assertEqual(result["status"], "success")
        self.assertNotIn("Ignored final prose", result["content"])

    def test_model_failure(self):
        with patch.object(report, "create_report_generation_agent", side_effect=RuntimeError("provider failed")):
            result = report.run_report_generation_agent(valid_state())["report"]
        self.assertEqual(result["status"], "failed")
        self.assertIsNone(result["content"])


if __name__ == "__main__":
    unittest.main()
