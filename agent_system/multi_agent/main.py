import json
import re
from copy import deepcopy

import litellm, logging
litellm.suppress_debug_info = True
logging.getLogger("LiteLLM").setLevel(logging.WARNING)

from shared_state import create_initial_state
from session import Session
from patient_info_agent import run_patient_info_agent
from medical_evidence_agent import run_medical_evidence_agent
from clinical_decision_support_agent import run_clinical_decision_support_agent
from verification_agent import run_verification_agent, format_feedback
from report_generation_agent import run_report_generation_agent


MAX_REVISIONS = 2  # automatic verification -> CDS correction rounds

BEFORE_CDS = [
    ("patient_information", run_patient_info_agent),
    ("medical_evidence", run_medical_evidence_agent),
]

# A request that names a patient starts a new report; anything else is a revision.
PATIENT_REF = re.compile(r"\b(patientid[_\s-]*\d+|patient\s+\d+)\b", re.IGNORECASE)

SAVED_SECTIONS = ["patient_information", "medical_evidence",
                  "clinical_decision_support", "verification", "report"]


def _run_stage(state, section, run_agent, **kwargs):
    print(f"\n--- Running {section} ---")
    try:
        state = run_agent(state, **kwargs)
    except Exception as exc:  # agents should catch their own errors; this is the safety net
        message = f"{section} crashed ({type(exc).__name__})."
        state.setdefault(section, {})
        state[section]["status"] = "failed"
        state[section]["error"] = message
        state["errors"].append(message)
    print(f"--- Finished {section}: {state[section]['status']} ---")
    return state


def _stop(state):
    state["current_agent"] = None
    return state


def _cds_verification_loop(state, revision_request, max_revisions):
    """Run CDS then Verification, retrying on verification feedback.

    revision_request is passed on EVERY iteration so a correction round
    never loses the clinician's instruction. Returns (state, ok).
    """
    feedback = None
    for attempt in range(max_revisions + 1):
        state = _run_stage(state, "clinical_decision_support",
                           run_clinical_decision_support_agent,
                           verification_feedback=feedback,
                           revision_request=revision_request)
        if state["clinical_decision_support"]["status"] != "success":
            return state, False

        state = _run_stage(state, "verification", run_verification_agent)
        state["verification"]["revision_count"] = attempt
        if state["verification"]["status"] != "success":
            return state, False
        if not state["verification"]["revision_required"]:
            return state, True

        if attempt < max_revisions:
            print(f"--- Verification requested correction {attempt + 1}/{max_revisions} ---")
            feedback = format_feedback(state)

    state["errors"].append(
        f"Verification still requires revision after {max_revisions} correction rounds; pipeline stopped."
    )
    return state, False


def run_pipeline(user_request, session=None, max_revisions=MAX_REVISIONS):
    """Run a new report, or revise the session's current report.

    Pass the same Session object on each call. On a revision the patient
    information and evidence are reused; CDS, verification and the report re-run.
    """
    session = session if session is not None else Session()
    is_revision = session.has_report and not PATIENT_REF.search(user_request)

    if is_revision:
        # Keep the ORIGINAL request: evidence/CDS agents read state["user_request"] as the question.
        state = create_initial_state(session.original_request)
        state["patient_information"] = deepcopy(session.sections["patient_information"])
        state["medical_evidence"] = deepcopy(session.sections["medical_evidence"])
        # CDS regenerates from scratch, so replay earlier revisions too.
        all_requests = session.revision_requests + [user_request]
        revision_request = "\n".join(f"- {r}" for r in all_requests)
    else:
        session.reset(user_request)
        state = create_initial_state(user_request)
        revision_request = None
        for section, run_agent in BEFORE_CDS:
            state = _run_stage(state, section, run_agent)
            if state[section]["status"] != "success":
                return _stop(state)

    state, ok = _cds_verification_loop(state, revision_request, max_revisions)
    if not ok:
        return _stop(state)

    state = _run_stage(state, "report", run_report_generation_agent)

    # Only a successful run replaces the saved session; a failed revision leaves the last good report.
    if state["report"]["status"] == "success":
        for name in SAVED_SECTIONS:
            session.sections[name] = deepcopy(state[name])
        if is_revision:
            session.revision_requests.append(user_request)
        session.report_versions.append(deepcopy(state["report"]))

    return _stop(state)


if __name__ == "__main__":
    session = Session()
    while True:
        user_input = input("User Request: ").strip()
        if user_input.lower() == "exit":
            break
        if user_input:
            result = run_pipeline(user_input, session)
            print(json.dumps(result, indent=2, default=str))
            print(f"\n[report versions saved: {len(session.report_versions)}]")