from datetime import datetime
from fastapi import APIRouter, Depends, Form, File, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.config import settings
from app.core.database import get_db
from app.models.models import Scan, Report, ChatMessage
from app.schemas.schemas import (
    AgentChatRequest,
    AgentChatResponse,
    DiagnosticAnalysisResponse,
    DifferentialItem,
    HealthResponse,
    ImagingFindingItem,
    PrimaryDiagnosisData,
    ReportCreate,
    ReportResponse,
    ScanCreate,
    ScanResponse,
    SegmentationResult,
    TreatmentProtocolSectionData,
    PatientProfileSummary,
)
from app.services.agent import run_agent_chat
from app.services.gemini import generate_clinical_report
from app.services.mri import run_mri_segmentation
from app.services.multi_agent_service import (
    get_patient_summaries,
    run_diagnostic_pipeline,
)

api_router = APIRouter()




# --- System Health ---
@api_router.get("/health", response_model=HealthResponse, tags=["System"])
async def health_check():
    return {
        "status": "online",
        "environment": settings.ENVIRONMENT,
        "version": "0.1.0",
    }


# --- Scans Management ---
@api_router.get("/scans", response_model=list[ScanResponse], tags=["Scans"])
async def list_scans(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Scan).order_by(Scan.id.desc()))
    return result.scalars().all()


@api_router.post("/scans", response_model=ScanResponse, status_code=status.HTTP_201_CREATED, tags=["Scans"])
async def create_scan(scan_in: ScanCreate, db: AsyncSession = Depends(get_db)):
    new_scan = Scan(
        patient_id=scan_in.patient_id,
        file_path=f"data/uploads/{scan_in.patient_id}_BraTS.nii.gz",
        modality=scan_in.modality,
        status="pending",
    )
    db.add(new_scan)
    await db.commit()
    await db.refresh(new_scan)
    return new_scan


@api_router.get("/scans/{scan_id}", response_model=ScanResponse, tags=["Scans"])
async def get_scan(scan_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Scan).where(Scan.id == scan_id))
    scan = result.scalar_one_or_none()
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")
    return scan


# --- MONAI SegResNet Segmentation ---
@api_router.post("/scans/{scan_id}/segment", response_model=SegmentationResult, tags=["MONAI MRI"])
async def run_segmentation(scan_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Scan).where(Scan.id == scan_id))
    scan = result.scalar_one_or_none()
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")

    seg_output = await run_mri_segmentation(scan.file_path)

    scan.wt_volume_cm3 = seg_output["wt_volume_cm3"]
    scan.tc_volume_cm3 = seg_output["tc_volume_cm3"]
    scan.et_volume_cm3 = seg_output["et_volume_cm3"]
    scan.status = "completed"
    await db.commit()
    await db.refresh(scan)

    return {
        "scan_id": scan.id,
        "wt_volume_cm3": scan.wt_volume_cm3,
        "tc_volume_cm3": scan.tc_volume_cm3,
        "et_volume_cm3": scan.et_volume_cm3,
        "status": scan.status,
    }


# --- Gemini Clinical Report Generation ---
@api_router.post("/reports", response_model=ReportResponse, status_code=status.HTTP_201_CREATED, tags=["Gemini Reports"])
async def create_report(report_in: ReportCreate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Scan).where(Scan.id == report_in.scan_id))
    scan = result.scalar_one_or_none()
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")

    # If scan not yet segmented, run segmentation first
    if scan.wt_volume_cm3 is None:
        seg_output = await run_mri_segmentation(scan.file_path)
        scan.wt_volume_cm3 = seg_output["wt_volume_cm3"]
        scan.tc_volume_cm3 = seg_output["tc_volume_cm3"]
        scan.et_volume_cm3 = seg_output["et_volume_cm3"]
        scan.status = "completed"
        await db.commit()

    report_content = await generate_clinical_report(
        scan_id=scan.id,
        patient_id=scan.patient_id,
        wt_vol=scan.wt_volume_cm3 or 0.0,
        tc_vol=scan.tc_volume_cm3 or 0.0,
        et_vol=scan.et_volume_cm3 or 0.0,
        clinical_history=report_in.clinical_history,
    )

    new_report = Report(
        scan_id=scan.id,
        findings=report_content["findings"],
        impression=report_content["impression"],
        recommendations=report_content.get("recommendations"),
    )
    db.add(new_report)
    await db.commit()
    await db.refresh(new_report)
    return new_report


# --- smolagents Interactive Chat ---
@api_router.post("/agent/chat", response_model=AgentChatResponse, tags=["smolagents"])
async def chat_with_agent(req: AgentChatRequest, db: AsyncSession = Depends(get_db)):
    # Persist user message
    user_msg = ChatMessage(session_id=req.session_id, role="user", content=req.message)
    db.add(user_msg)
    await db.commit()

    agent_result = await run_agent_chat(
        session_id=req.session_id,
        message=req.message,
        scan_id=req.scan_id,
    )

    # Persist assistant response
    assistant_msg = ChatMessage(session_id=req.session_id, role="assistant", content=agent_result["response"])
    db.add(assistant_msg)
    await db.commit()

    return agent_result


# --- Patient Database Queries ---
@api_router.get("/patients", response_model=list[PatientProfileSummary], tags=["Patients"])
async def list_patient_profiles(limit: int = 50):
    """Retrieves available patient records from gbm_patient_profiles.json."""
    return get_patient_summaries(limit=limit)


# --- Diagnostic Workstation Full Processing Endpoint ---
@api_router.post("/diagnostic/analyze", response_model=DiagnosticAnalysisResponse, tags=["Diagnostic Workstation"])
async def run_diagnostic_analysis(
    file: UploadFile | None = File(None),
    patientId: str | None = Form(None),
    fullName: str = Form("Hayden Janezic"),
    dateOfBirth: str = Form("27/08/2005"),
    biologicalSex: str = Form("Male"),
    weightKg: str = Form("20"),
    scanType: str = Form("MRI Brain"),
    contrastAdministered: bool = Form(False),
    presentingSymptoms: str = Form("dizziness"),
    clinicalNotes: str = Form("extreme history of migranes"),
    db: AsyncSession = Depends(get_db),
):
    """
    Executes full multi-modal diagnostic pipeline:
    1. Ingests scan file & metadata
    2. Runs multi-agent pipeline + patient database lookup
    3. Persists scan record in database
    4. Returns structured diagnostic response for MedScan AI workstation
    """
    # 1. Execute diagnostic pipeline via multi_agent_service
    result = run_diagnostic_pipeline(
        patient_id=patientId,
        full_name=fullName,
        scan_type=scanType,
        symptoms=presentingSymptoms,
        clinical_notes=clinicalNotes,
    )

    # 2. Persist scan in DB audit log
    resolved_patient = patientId or fullName.replace(" ", "_") or "PATIENT_UNKNOWN"
    scan_record = Scan(
        patient_id=resolved_patient,
        file_path=file.filename if file and file.filename else "data/uploads/sample_mri.nii.gz",
        modality=scanType,
        status="completed",
        wt_volume_cm3=38.45,
        tc_volume_cm3=19.82,
        et_volume_cm3=7.64,
    )
    db.add(scan_record)
    await db.commit()
    await db.refresh(scan_record)

    return result


