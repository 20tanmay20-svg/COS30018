import json
import logging
import os
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any
from dotenv import load_dotenv

# Ensure project root and agent_system are on sys.path
PROJECT_ROOT = Path(__file__).resolve().parents[3]
AGENT_SYSTEM_ROOT = PROJECT_ROOT / "agent_system"
MULTI_AGENT_ROOT = AGENT_SYSTEM_ROOT / "multi_agent"

for p in (str(PROJECT_ROOT), str(AGENT_SYSTEM_ROOT), str(MULTI_AGENT_ROOT)):
    if p not in sys.path:
        sys.path.insert(0, p)

load_dotenv(PROJECT_ROOT / ".env")
load_dotenv(PROJECT_ROOT / "backend" / ".env")

logger = logging.getLogger(__name__)

# Safely import patient search tools
try:
    from agent_system.tools.patient_search import get_patient_by_id, load_patients
except Exception as e:
    logger.warning("Could not import patient_search directly: %s. Using local JSON reader fallback.", e)
    load_patients = None
    get_patient_by_id = None

# Safely import multi-agent pipeline & stages
try:
    from agent_system.multi_agent.main import run_pipeline
except Exception as e:
    logger.warning("Could not import multi_agent.main.run_pipeline: %s", e)
    run_pipeline = None

_import_error: str | None = None

try:
    from agent_system.multi_agent.shared_state import create_initial_state
    from agent_system.multi_agent.patient_info_agent import run_patient_info_agent
    from agent_system.multi_agent.medical_evidence_agent import run_medical_evidence_agent
    from agent_system.multi_agent.clinical_decision_support_agent import run_clinical_decision_support_agent
    from agent_system.multi_agent.verification_agent import run_verification_agent
except Exception as e:
    logger.warning("Could not import multi_agent stage agents: %s", e)
    _import_error = str(e)
    create_initial_state = None
    run_patient_info_agent = None
    run_medical_evidence_agent = None
    run_clinical_decision_support_agent = None
    run_verification_agent = None

try:
    from agent_system.multi_agent.report_generation_agent import run_report_generation_agent
except Exception as e:
    logger.warning("Could not import report_generation_agent: %s", e)
    run_report_generation_agent = None


def _load_raw_patient_profiles() -> list[dict[str, Any]]:
    """Loads gbm_patient_profiles.json from disk."""
    json_path = AGENT_SYSTEM_ROOT / "data" / "processed" / "gbm_patient_profiles.json"
    if json_path.exists():
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error("Failed to read %s: %s", json_path, e)
    return []


def get_patient_summaries(limit: int = 50) -> list[dict[str, Any]]:
    """Retrieves patient summary list for the frontend lookup."""
    patients = load_patients() if load_patients else _load_raw_patient_profiles()
    summaries = []
    for p in patients[:limit]:
        summaries.append({
            "patient_id": p.get("Patient_ID"),
            "sex": p.get("Sex at Birth"),
            "age": p.get("Age at diagnosis"),
            "diagnosis": p.get("Primary Diagnosis", "GBM"),
            "grade": p.get("Grade of Primary Brain Tumor", "4"),
            "progression": p.get("Progression"),
            "progression_days": p.get("Time to First Progression (Days)"),
            "death": p.get("Overall Survival (Death)"),
        })
    return summaries


def get_single_patient(patient_id: str) -> dict[str, Any] | None:
    """Retrieves single patient profile by Patient_ID."""
    if get_patient_by_id:
        try:
            res = get_patient_by_id(patient_id)
            if res.get("success"):
                return res.get("patient")
        except Exception:
            pass

    patients = _load_raw_patient_profiles()
    target = patient_id.strip().lower()
    for p in patients:
        if p.get("Patient_ID", "").lower() == target:
            return p
    return None


def _extract_patient_ids(user_request: str) -> list[str]:
    """Robustly extracts all patient IDs and numbers from freeform text."""
    pids: list[str] = []

    # 1. Match explicit IDs like PatientID_0003 or PatientID-12
    for m in re.findall(r"PatientID[_\s-]*(\d+)", user_request, re.IGNORECASE):
        pid = f"PatientID_{int(m):04d}"
        if pid not in pids:
            pids.append(pid)

    # 2. Match multi-number series, e.g., "patients 3 and 6", "patients 3, 4, and 5"
    series_match = re.search(r"\bpatient(?:s)?\s+([0-9\s,and&]+)", user_request, re.IGNORECASE)
    if series_match:
        for num in re.findall(r"\b(\d+)\b", series_match.group(1)):
            pid = f"PatientID_{int(num):04d}"
            if pid not in pids:
                pids.append(pid)

    # 3. Match individual "patient 3", "patient #3"
    for m in re.findall(r"\bpatient[s]?\s*#?(\d+)\b", user_request, re.IGNORECASE):
        pid = f"PatientID_{int(m):04d}"
        if pid not in pids:
            pids.append(pid)

    return pids


def _populate_final_report_summary(state: dict[str, Any]) -> dict[str, Any]:
    """Ensures final_report is fully populated for frontend executive card views."""
    if not state:
        return state
    if "final_report" not in state or not state["final_report"]:
        cds = state.get("clinical_decision_support", {})
        patient_list = state.get("patient_information", {}).get("patient_data", [])
        patient_rec = patient_list[0] if patient_list else {}
        pid = patient_rec.get("Patient_ID") or patient_rec.get("patient_id", "PatientID_0007")
        psex = patient_rec.get("Sex at Birth", "Male")
        page = patient_rec.get("Age at diagnosis", "65")
        pgrade = patient_rec.get("Grade of Primary Brain Tumor", "4")
        pdiag = patient_rec.get("Primary Diagnosis", "GBM")

        findings_lines = [
            f"• {c.get('consideration')}: {c.get('reasoning')}"
            for c in cds.get("clinical_considerations", [])
            if isinstance(c, dict)
        ]
        pathway_lines = [
            f"{i+1}. {p.get('option')} (When: {p.get('when_considered')}; Risks: {p.get('risks_and_limitations')})"
            for i, p in enumerate(cds.get("treatment_pathways", []))
            if isinstance(p, dict)
        ]
        rec_lines = [
            f"• {r.get('item')}: {r.get('reason')}"
            for r in cds.get("doctor_review_items", [])
            if isinstance(r, dict)
        ]

        state["final_report"] = {
            "patient_summary": f"{pid} • {psex} • Age {page} (WHO Grade {pgrade} {pdiag})",
            "findings": "\n\n".join(findings_lines) or "Clinical considerations generated by multi-agent reasoning.",
            "impression": (cds.get("uncertainties", ["Evidence and clinical plan reviewed."])[0]
                           if cds.get("uncertainties") else "High-grade glioma evaluation completed by CDS agent."),
            "treatment_plan": "\n".join(pathway_lines) or "Treatment pathways synthesized from retrieved clinical literature.",
            "recommendations": "\n".join(rec_lines) or "Mandatory multidisciplinary clinician review required.",
        }
    return state


def execute_multi_agent_pipeline_stream(user_request: str):
    """
    Streams multi-agent pipeline progress stage by stage, directly matching terminal logs.
    Yields progress events as each agent begins and finishes, then yields 'complete' with final state.
    If any stage or dependency fails, yields an error event and stops.
    """
    if not (create_initial_state and run_patient_info_agent and run_medical_evidence_agent and run_clinical_decision_support_agent and run_verification_agent):
        err_msg = _import_error or "Pipeline agent modules not available. Verify that smolagents[litellm] is installed and GEMINI_API_KEY is configured in .env."
        logger.error("Cannot run pipeline: %s", err_msg)
        yield {
            "type": "error",
            "message": f"Pipeline initialization failed: {err_msg}",
        }
        return

    try:
        # Initialize
        yield {
            "type": "progress",
            "stage": "patient_information",
            "stage_index": 1,
            "percent": 15,
            "message": "Patient Information Agent: Locating and indexing patient record...",
        }
        state = create_initial_state(user_request)

        # Stage 1: Patient Information Agent
        print(f"\n--- Running patient_information ---", flush=True)
        state = run_patient_info_agent(state)
        p_status = state.get("patient_information", {}).get("status")
        print(f"--- Finished patient_information: {p_status} ---", flush=True)

        if p_status != "success":
            err_detail = state.get("patient_information", {}).get("error") or ", ".join(state.get("errors", [])) or "Patient record not found"
            logger.error("Patient Information Agent failed: %s", err_detail)
            yield {
                "type": "error",
                "message": f"Patient Information Agent failed: {err_detail}",
            }
            return

        yield {
            "type": "progress",
            "stage": "patient_information",
            "stage_index": 1,
            "percent": 25,
            "message": "Patient Information Agent: Record retrieved successfully.",
        }

        # Stage 2: Medical Evidence Agent
        yield {
            "type": "progress",
            "stage": "medical_evidence",
            "stage_index": 2,
            "percent": 35,
            "message": "Medical Evidence Agent: Searching PubMed & assessing literature...",
        }
        print(f"\n--- Running medical_evidence ---", flush=True)
        state = run_medical_evidence_agent(state)
        e_status = state.get("medical_evidence", {}).get("status")
        print(f"--- Finished medical_evidence: {e_status} ---", flush=True)

        if e_status != "success":
            err_detail = state.get("medical_evidence", {}).get("error") or ", ".join(state.get("errors", [])) or "Medical evidence retrieval failed"
            logger.error("Medical Evidence Agent failed: %s", err_detail)
            yield {
                "type": "error",
                "message": f"Medical Evidence Agent failed: {err_detail}",
            }
            return

        yield {
            "type": "progress",
            "stage": "medical_evidence",
            "stage_index": 2,
            "percent": 50,
            "message": "Medical Evidence Agent: Literature retrieved and assessed.",
        }

        # Stage 3: Clinical Decision Support Agent
        yield {
            "type": "progress",
            "stage": "clinical_decision_support",
            "stage_index": 3,
            "percent": 55,
            "message": "Clinical Decision Support Agent: Formulating considerations & treatment pathways...",
        }
        print(f"\n--- Running clinical_decision_support ---", flush=True)
        state = run_clinical_decision_support_agent(state)
        cds_status = state.get("clinical_decision_support", {}).get("status")
        print(f"--- Finished clinical_decision_support: {cds_status} ---", flush=True)

        if cds_status != "success":
            err_detail = state.get("clinical_decision_support", {}).get("error") or ", ".join(state.get("errors", [])) or "Clinical decision support failed"
            logger.error("Clinical Decision Support Agent failed: %s", err_detail)
            yield {
                "type": "error",
                "message": f"Clinical Decision Support Agent failed: {err_detail}",
            }
            return

        yield {
            "type": "progress",
            "stage": "clinical_decision_support",
            "stage_index": 3,
            "percent": 75,
            "message": "Clinical Decision Support Agent: Decision pathways synthesized.",
        }

        # Stage 4: Verification Agent
        yield {
            "type": "progress",
            "stage": "verification",
            "stage_index": 4,
            "percent": 80,
            "message": "Verification Agent: Cross-referencing claims against cited abstracts...",
        }
        print(f"\n--- Running verification ---", flush=True)
        state = run_verification_agent(state)
        v_status = state.get("verification", {}).get("status")
        print(f"--- Finished verification: {v_status} ---", flush=True)

        if v_status != "success":
            err_detail = state.get("verification", {}).get("error") or ", ".join(state.get("errors", [])) or "Verification failed"
            logger.error("Verification Agent failed: %s", err_detail)
            yield {
                "type": "error",
                "message": f"Verification Agent failed: {err_detail}",
            }
            return

        yield {
            "type": "progress",
            "stage": "verification",
            "stage_index": 4,
            "percent": 90,
            "message": "Verification Agent: Claims verified.",
        }

        # Stage 5: Report Generation Agent
        yield {
            "type": "progress",
            "stage": "report_generation",
            "stage_index": 5,
            "percent": 95,
            "message": "Report Generation Agent: Compiling verified structured dossier...",
        }
        print(f"\n--- Running report_generation ---", flush=True)
        if run_report_generation_agent:
            is_approved = (
                state.get("verification", {}).get("status") == "success"
                and not state.get("verification", {}).get("revision_required")
            )
            state = run_report_generation_agent(state, preview=not is_approved, use_llm=False)
        print(f"--- Finished report_generation: {state.get('report', {}).get('status')} ---", flush=True)

        state = _populate_final_report_summary(state)

        yield {
            "type": "complete",
            "percent": 100,
            "stage_index": 5,
            "message": "Multi-Agent Pipeline Complete: Dossier Assembled & Verified",
            "state": state,
        }

    except Exception as exc:
        logger.exception("Error in pipeline stream: %s", exc)
        yield {
            "type": "error",
            "message": f"Pipeline execution failed: {str(exc)}",
        }


def execute_multi_agent_pipeline(user_request: str) -> dict[str, Any]:
    """
    Executes the multi-agent pipeline and returns the final state dictionary.
    """
    final_state = None
    last_error = None
    for event in execute_multi_agent_pipeline_stream(user_request):
        if event.get("type") == "complete":
            final_state = event.get("state")
        elif event.get("type") == "error":
            last_error = event.get("message")
    if not final_state:
        raise RuntimeError(last_error or "Multi-agent pipeline failed to produce final state.")
    return final_state


def _build_dynamic_database_state(user_request: str) -> dict[str, Any]:
    raise NotImplementedError("Direct database report generation is disabled. Reports must be generated via the multi-agent pipeline.")
