from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field


class HealthResponse(BaseModel):
    status: str
    environment: str
    version: str


# --- Scan Schemas ---
class ScanCreate(BaseModel):
    patient_id: str
    modality: str = "BraTS-Multimodal"


class ScanResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    patient_id: str
    file_path: str
    modality: str
    status: str
    wt_volume_cm3: float | None = None
    tc_volume_cm3: float | None = None
    et_volume_cm3: float | None = None
    created_at: datetime


# --- Segmentation Schemas ---
class SegmentationResult(BaseModel):
    scan_id: int
    wt_volume_cm3: float = Field(..., description="Whole Tumor volume in cm³")
    tc_volume_cm3: float = Field(..., description="Tumor Core volume in cm³")
    et_volume_cm3: float = Field(..., description="Enhancing Tumor volume in cm³")
    status: str = "completed"


# --- Report Schemas ---
class ReportCreate(BaseModel):
    scan_id: int
    clinical_history: str | None = None


class ReportResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    scan_id: int
    findings: str
    impression: str
    recommendations: str | None = None
    created_at: datetime


# --- Agent Schemas ---
class AgentChatRequest(BaseModel):
    session_id: str
    message: str
    scan_id: int | None = None


class AgentChatResponse(BaseModel):
    session_id: str
    response: str
    tools_used: list[str] = []
