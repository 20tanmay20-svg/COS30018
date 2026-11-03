import json
import logging
import re
import sys
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
from test_pipeline.run_recorder import REPORTS_DIR, RunRecorder, begin_stage, end_stage

log = logging.getLogger("pipeline")


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
    log.info("Running %s", section)
    began = begin_stage()
    try:
        state = run_agent(state, **kwargs)
    except Exception as exc:  # agents should catch their own errors; this is the safety net
        log.exception("%s crashed", section)  # includes the traceback
        message = f"{section} crashed ({type(exc).__name__})."
        state.setdefault(section, {})
        state[section]["status"] = "failed"
        state[section]["error"] = message
        state["errors"].append(message)
    end_stage(section, began, state[section]["status"])
    if state[section]["status"] == "success":
        log.info("Finished %s: success", section)
    else:
        log.error("Finished %s: %s (%s)", section, state[section]["status"], state[section].get("error"))
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
        log.info("Draft %s of %s (CDS then verification)", attempt + 1, max_revisions + 1)
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
            log.info("Verification approved the draft")
            return state, True

        issues = state["verification"]["issues"]
        log.warning("Verification found %s issue(s): %s", len(issues), "; ".join(issues))
        if attempt < max_revisions:
            log.info("Verification requested correction %s/%s", attempt + 1, max_revisions)
            feedback = format_feedback(state)

    message = f"Verification still requires revision after {max_revisions} correction rounds; pipeline stopped."
    log.error(message)
    state["errors"].append(message)
    return state, False


def run_pipeline(user_request, session=None, max_revisions=MAX_REVISIONS):
    """Run a new report, or revise the session's current report.

    Pass the same Session object on each call. On a revision the patient
    information and evidence are reused; CDS, verification and the report re-run.
    """
    session = session if session is not None else Session()
    is_revision = session.has_report and not PATIENT_REF.search(user_request)
    log.info("Pipeline started: %s request (%s)", "revision" if is_revision else "new report", user_request)

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
                log.error("Pipeline stopped at %s; no report produced", section)
                return _stop(state)

    state, ok = _cds_verification_loop(state, revision_request, max_revisions)
    if not ok:
        log.error("Pipeline stopped before the report; no report produced")
        return _stop(state)

    state = _run_stage(state, "report", run_report_generation_agent)

    # Only a successful run replaces the saved session; a failed revision leaves the last good report.
    if state["report"]["status"] == "success":
        for name in SAVED_SECTIONS:
            session.sections[name] = deepcopy(state[name])
        if is_revision:
            session.revision_requests.append(user_request)
        session.report_versions.append(deepcopy(state["report"]))
        log.info("Pipeline finished: report version %s saved to the session", len(session.report_versions))
    else:
        log.error("Pipeline finished without a report; the session keeps its last good report")

    return _stop(state)


if __name__ == "__main__":
    session = Session()
    while True:
        user_input = input("User Request: ").strip()
        if user_input.lower() == "exit":
            break
        if user_input:
            # "CMP-05: Prepare a report for ..." runs the request as evaluation case CMP-05
            tagged = re.match(r"\s*(CMP-\d{2})\s*[:\-]\s*(.*)", user_input, re.DOTALL)
            case_id, request = (tagged.group(1).upper(), tagged.group(2)) if tagged else (None, user_input)
            from test_pipeline.evaluate_runs import CASES, check_case  # imported here so tests of main.py stay light
            from test_pipeline.fault_injection import fault_for

            run = RunRecorder(request, case_id)
            with fault_for(case_id, sys.modules[__name__]):
                result = run_pipeline(request, session)
            print(json.dumps(result, indent=2, default=str))
            summary = run.finish(result, session)
            if case_id:
                expected = next((c[2] for c in CASES if c[0] == case_id), "unknown case")
                passed, evidence = check_case(summary, REPORTS_DIR)
                print(f"\n{case_id}: {'PASS' if passed else 'FAIL'}\n  expected: {expected}\n  result: {evidence}")
            print(f"\n[report versions saved: {len(session.report_versions)}]")