import unittest
import os
import sys
import inspect

# Aleksa: Does not work for some reason
# sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Aleksa: Only solution which worked for me so far
currentdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
parentdir = os.path.dirname(currentdir)
sys.path.insert(0, parentdir)

from agent_system.tools.assemble_report import create_assemble_report_tool
from agent_system.tools.assess_evidence import create_assess_evidence_tool
from agent_system.tools.record_clinical_consideration import create_record_clinical_consideration_tool
from agent_system.tools.record_treatment_pathway import create_record_treatment_pathway_tool
from agent_system.tools.record_uncertainty import create_record_uncertainty_tool
from agent_system.tools.retrieve_patient import retrieve_patient
from agent_system.tools.search_medical_evidence import create_search_medical_evidence_tool
from agent_system.tools.search_patient_records import search_patient_records
from agent_system.tools.tool_schemas import ReportSection
from agent_system.tools.verification_tools import create_verification_tools


class ToolSchemaTests(unittest.TestCase):
    def setUp(self):
        session = object()
        verification_tools = create_verification_tools({}, session, {})
        self.tools = {
            "retrieve_patient": retrieve_patient,
            "search_patient_records": search_patient_records,
            "search_medical_evidence": create_search_medical_evidence_tool(session),
            "assess_evidence": create_assess_evidence_tool(session),
            "record_clinical_consideration": create_record_clinical_consideration_tool(session),
            "record_treatment_pathway": create_record_treatment_pathway_tool(session),
            "record_uncertainty": create_record_uncertainty_tool(session),
            "assemble_report": create_assemble_report_tool(session),
            **{tool.name: tool for tool in verification_tools},
        }

    def test_every_tool_has_object_result_and_result_contract(self):
        self.assertEqual(len(self.tools), 11)
        for name, tool in self.tools.items():
            with self.subTest(tool=name):
                self.assertEqual(tool.output_type, "object")
                self.assertIn("Result:", tool.description)

    def test_optional_patient_filters_have_nullable_types(self):
        inputs = self.tools["search_patient_records"].inputs
        for name in ("age_min", "age_max", "sex", "progression", "death_recorded"):
            with self.subTest(argument=name):
                self.assertTrue(inputs[name]["nullable"])
        self.assertEqual(inputs["sex"]["enum"], ["Female", "Male"])
        self.assertEqual(inputs["progression"]["enum"], [0, 1])
        self.assertEqual(inputs["death_recorded"]["enum"], [0, 1])

    def test_evidence_and_verification_choices_are_enumerated(self):
        self.assertEqual(
            self.tools["assess_evidence"].inputs["relevance"]["enum"],
            ["high", "medium", "low", "not_relevant"],
        )
        self.assertEqual(
            self.tools["get_cited_evidence"].inputs["item_type"]["enum"],
            ["consideration", "pathway"],
        )
        self.assertEqual(
            self.tools["record_verdict"].inputs["verdict"]["enum"],
            ["supported", "partial", "unsupported"],
        )

    def test_report_section_array_has_allowed_values(self):
        section_schema = self.tools["assemble_report"].inputs["section_order"]
        self.assertEqual(section_schema["type"], "array")
        self.assertEqual(section_schema["items"]["enum"], list(ReportSection.__args__))

    def test_requires_review_can_be_omitted_without_changing_its_default(self):
        schema = self.tools["record_clinical_consideration"].inputs["requires_review"]
        self.assertTrue(schema["nullable"])
        self.assertEqual(schema["type"], "boolean")


if __name__ == "__main__":
    unittest.main()