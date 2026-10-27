"""Shared type aliases used by the model-facing patient and GBM tools."""

from typing import Any, Literal, TypeAlias


ToolResult: TypeAlias = dict[str, Any]
PatientRecord: TypeAlias = dict[str, Any]
PatientId: TypeAlias = str
PubMedId: TypeAlias = str
PatientSex: TypeAlias = Literal["Female", "Male"]
BinaryPatientStatus: TypeAlias = Literal[0, 1]
EvidenceRelevance: TypeAlias = Literal["high", "medium", "low", "not_relevant"]
VerificationItemType: TypeAlias = Literal["consideration", "pathway"]
VerificationVerdict: TypeAlias = Literal["supported", "partial", "unsupported"]
ReportSection: TypeAlias = Literal[
    "patient_context",
    "clinical_considerations",
    "treatment_pathways",
    "uncertainties",
    "doctor_review_items",
    "references",
]