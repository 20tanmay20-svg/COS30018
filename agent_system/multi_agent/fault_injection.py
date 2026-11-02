"""Faults that cannot be triggered by typing a request, applied for one main.py run only.

Typing `CMP-05: Prepare a report for PatientID_0003` makes main.py call fault_for("CMP-05", ...),
which temporarily changes one part of the real pipeline and restores it afterwards.

  CMP-05  CDS adds a claim that cites no evidence
  CMP-06  CDS adds a claim that cites retrieved evidence which does not support it
  CMP-07  the patient record gets a second, conflicting age at diagnosis
  CMP-08  the PubMed search raises an error
"""

from contextlib import ExitStack, contextmanager
from unittest import mock

import medical_evidence_agent
import patient_info_agent
from evaluate_runs import BAD_CLAIMS


class BrokenPubMed:
    def search(self, *args, **kwargs):
        raise RuntimeError("Injected PubMed outage")


def _cds_with_bad_claim(real_cds, claim):
    """Wrap the CDS agent so its first draft also contains the bad claim (later drafts are untouched)."""
    added = []

    def wrapped(state, **kwargs):
        state = real_cds(state, **kwargs)
        if not added and state["clinical_decision_support"]["status"] == "success":
            added.append(True)
            evidence = state["medical_evidence"]["retrieved_evidence"]
            cited = [str(evidence[0]["pmid"])] if claim["cites_evidence"] and evidence else []
            state["clinical_decision_support"]["clinical_considerations"].append({
                "consideration": claim["text"], "reasoning": claim["text"], "context": "Injected for evaluation",
                "limitations": "None stated", "supporting_evidence": cited, "requires_clinician_review": False})
        return state

    return wrapped


def _with_conflicting_age(real_lookup):
    def wrapped(patient_id):
        result = real_lookup(patient_id)
        if result.get("success"):
            patient = dict(result["patient"])
            patient["Age at diagnosis (history)"] = "42" if str(patient.get("Age at diagnosis")) != "42" else "57"
            return {**result, "patient": patient}
        return result

    return wrapped


@contextmanager
def fault_for(case_id, pipeline):
    """Apply the fault for case_id (if it has one) to the `pipeline` module (main.py) for the duration."""
    with ExitStack() as stack:
        if case_id in BAD_CLAIMS:
            patched = _cds_with_bad_claim(pipeline.run_clinical_decision_support_agent, BAD_CLAIMS[case_id])
            stack.enter_context(mock.patch.object(pipeline, "run_clinical_decision_support_agent", patched))
        elif case_id == "CMP-07":
            stack.enter_context(mock.patch.object(
                patient_info_agent, "get_patient_by_id", _with_conflicting_age(patient_info_agent.get_patient_by_id)))
        elif case_id == "CMP-08":
            stack.enter_context(mock.patch.object(medical_evidence_agent, "PubMedClient", BrokenPubMed))
        yield
