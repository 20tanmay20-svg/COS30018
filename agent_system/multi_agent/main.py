"""Starts the GBM multi-agent pipeline.

Each agent is built independently and exposes run_*(state) -> state, which
updates its own section of the shared state. This file creates the state, runs
the agents in order, and runs the Verification -> CDS revision loop (capped).
"""
import json

from shared_state import create_initial_state
from patient_info_agent import run_patient_info_agent
from medical_evidence_agent import run_medical_evidence_agent
from clinical_decision_support_agent import run_clinical_decision_support_agent
from verification_agent import run_verification_agent, format_feedback
# Add Report Generation here once it is written.

MAX_REVISIONS = 2

BEFORE_CDS = [
    ("patient_information", run_patient_info_agent),
    ("medical_evidence", run_medical_evidence_agent),
]


def _run_stage(state, section, run_agent, **kwargs):
    print(f"\n--- Running {section} ---")
    state = run_agent(state, **kwargs)
    print(f"--- Finished {section}: {state[section]['status']} ---")
    return state


def _stop(state):
    state["current_agent"] = None
    return state


def run_pipeline(user_request, max_revisions=MAX_REVISIONS):
    state = create_initial_state(user_request)

    for section, run_agent in BEFORE_CDS:
        state = _run_stage(state, section, run_agent)
        if state[section]["status"] != "success":
            return _stop(state)  # the agent has already recorded its error

    # CDS <-> Verification loop
    feedback = None
    for revision in range(max_revisions + 1):
        state = _run_stage(state, "clinical_decision_support",
                           run_clinical_decision_support_agent,
                           verification_feedback=feedback)
        if state["clinical_decision_support"]["status"] != "success":
            return _stop(state)

        state = _run_stage(state, "verification", run_verification_agent)
        state["verification"]["revision_count"] = revision
        if state["verification"]["status"] != "success":
            return _stop(state)
        if not state["verification"]["revision_required"]:
            break
        print(f"--- Verification requested revision {revision + 1}/{max_revisions} ---")
        feedback = format_feedback(state)
    else:
        state["errors"].append(
            f"Verification still requires revision after {max_revisions} attempts; pipeline stopped."
        )
        return _stop(state)

    # Report generation goes here once it is written.
    return _stop(state)


if __name__ == "__main__":
    while True:
        user_input = input("User Request: ").strip()
        if user_input.lower() == "exit":
            break
        if user_input:
            print(json.dumps(run_pipeline(user_input), indent=2, default=str))