"""Temporary faults for single-agent pipeline evaluation runs.

CMP-05/06 add a faulty CDS claim, CMP-07 adds conflicting patient history,
and CMP-08 forces the PubMed client to fail. Patches are restored on exit.
"""

from contextlib import ExitStack, contextmanager
import importlib
from unittest import mock

from .evaluate_runs import BAD_CLAIMS


class BrokenPubMed:
    def search(self, *args, **kwargs):
        raise RuntimeError("Injected PubMed outage")


def _with_conflicting_age(real_lookup):
    def wrapped(patient_id):
        result = real_lookup(patient_id)
        if result.get("success"):
            patient = dict(result["patient"])
            current_age = patient.get("Age at diagnosis")
            patient["Age at diagnosis (history)"] = "42" if str(current_age) != "42" else "57"
            return {**result, "patient": patient}
        return result

    return wrapped


def _with_bad_claim(pipeline, claim):
    real_cds_phase = pipeline._run_cds_phase
    injected = False

    def wrapped(*args, **kwargs):
        nonlocal injected
        succeeded = real_cds_phase(*args, **kwargs)
        cds = pipeline.state["clinical_decision_support"]
        if succeeded and not injected:
            evidence = pipeline.state["medical_evidence"].get("retrieved_evidence", [])
            cited = [str(evidence[0]["pmid"])] if claim["cites_evidence"] and evidence else []
            cds["clinical_considerations"].append({
                "consideration": claim["text"],
                "reasoning": claim["text"],
                "context": "Injected for evaluation",
                "limitations": "None stated",
                "supporting_evidence": cited,
                "requires_clinician_review": False,
            })
            injected = True
        return succeeded

    return wrapped


@contextmanager
def fault_for(case_id, pipeline):
    """Apply one case fault to a SingleAgentPipeline for the duration of the context."""
    with ExitStack() as stack:
        if case_id in BAD_CLAIMS:
            stack.enter_context(mock.patch.object(
                pipeline, "_run_cds_phase", _with_bad_claim(pipeline, BAD_CLAIMS[case_id])
            ))
        elif case_id == "CMP-07":
            patient_tool = importlib.import_module("tools.retrieve_patient")
            stack.enter_context(mock.patch.object(
                patient_tool, "get_patient_by_id",
                _with_conflicting_age(patient_tool.get_patient_by_id),
            ))
        elif case_id == "CMP-08":
            previous_client = pipeline.pubmed_client
            pipeline.pubmed_client = BrokenPubMed()
            stack.callback(setattr, pipeline, "pubmed_client", previous_client)
        yield
