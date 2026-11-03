"""Clinical Decision Support Agent: 10 cases (CDS-01 to CDS-10) using synthetic patients and evidence.

CDS-01, CDS-02 and CDS-10 run the real agent loop and tools. OFFLINE they get a scripted model that
makes fixed tool calls; with LIVE=1 they use the configured cloud model. The other cases check the
agent's validation code directly, so they behave the same in both modes.
"""

import copy
import json
from unittest.mock import patch

import pytest
from smolagents import Model
from smolagents.models import ChatMessage, ChatMessageToolCall, ChatMessageToolCallFunction

import clinical_decision_support_agent as cds
from shared_state import create_initial_state
from conftest import check_case
from fake_models import LIVE
from measure import run

HIGH, LOW, MEDIUM = "90000011", "90000012", "90000013"
EVIDENCE = {
    HIGH: ("Temozolomide with radiotherapy in glioblastoma", "high",
           "Temozolomide with radiotherapy was associated with improved survival."),
    LOW: ("Unrelated imaging study", "low", None),
    MEDIUM: ("Small case series of atypical glioblastoma", "medium",
             "Atypical presentations were described in a small case series."),
}


def make_state(pmids=(HIGH, LOW), records=None):
    """A state with successful patient and evidence stages, ready for the CDS Agent."""
    state = create_initial_state("Synthetic request: consider management options for this patient.")
    state["patient_information"].update(status="success", patient_data=records or [{
        "Patient_ID": "SYNTHETIC-PRIVATE", "Primary Diagnosis": "GBM", "Age at diagnosis": 60,
        "Sex at Birth": "Female", "Grade of Primary Brain Tumor": 4, "Overall Survival (Death)": 1}])
    state["medical_evidence"].update(
        status="success",
        retrieved_evidence=[{"pmid": p, "title": EVIDENCE[p][0], "url": f"https://pubmed.ncbi.nlm.nih.gov/{p}/"}
                            for p in pmids],
        evidence_relevance=[{"pmid": p, "relevance": EVIDENCE[p][1], "supporting_quote": EVIDENCE[p][2],
                             "limitations": "Synthetic evidence only."} for p in pmids])
    return state


def make_session(pmids=(HIGH,), **kwargs):
    return cds.CDSSession([{"pmid": p, "title": EVIDENCE[p][0]} for p in pmids], **kwargs)


def consideration(evidence=(HIGH,), **changes):
    arguments = dict(consideration="Synthetic consideration", reasoning="Synthetic reasoning",
                     context_info="Synthetic context", supporting_evidence=list(evidence),
                     limitations="Synthetic limitation", requires_review=True)
    return arguments | changes


def pathway(evidence=(HIGH,), **changes):
    arguments = dict(option="Synthetic option", when_considered="Synthetic condition",
                     supporting_evidence=list(evidence), unknown_patient_factors="Performance status unknown.",
                     risks_and_limitations="Synthetic risks.")
    return arguments | changes


# ---------------------------------------------------------
# Scripted stand-in for the CDS Agent's language model

class ScriptedCDSModel(Model):
    """Make the given recording tool calls in the first step, then call final_answer alone."""

    def __init__(self, calls, fail_after_first_step=False):
        super().__init__(model_id="fake-cds")
        self.calls, self.fail = calls, fail_after_first_step

    def generate(self, messages, stop_sequences=None, response_format=None, tools_to_call_from=None, **kwargs):
        steps_done = sum(1 for m in messages if str(getattr(m, "role", "")).lower().endswith("assistant"))
        if steps_done and self.fail:
            raise RuntimeError("private provider response")
        calls = self.calls if steps_done == 0 else [("final_answer", {"answer": "Recorded."})]
        return ChatMessage(role="assistant", content="", tool_calls=[
            ChatMessageToolCall(id=f"call_{steps_done}_{n}", type="function",
                                function=ChatMessageToolCallFunction(name=name, arguments=args))
            for n, (name, args) in enumerate(calls)])


def cds_model(calls):
    """The model to pass to run_clinical_decision_support_agent: None means the real configured model."""
    return None if LIVE else ScriptedCDSModel(calls)


def run_agent(state, model, **kwargs):
    original = copy.deepcopy(state)
    cds.run_clinical_decision_support_agent(state, model=model, **kwargs)
    return {"cds": state["clinical_decision_support"], "state": state, "original": original}


def cited(result):
    items = result["cds"]["clinical_considerations"] + result["cds"]["treatment_pathways"]
    return {pmid for item in items for pmid in item["supporting_evidence"]}


# ---------------------------------------------------------
# Case runners and checks

def run_cds01():
    return run_agent(make_state(), cds_model([("record_clinical_consideration", consideration())]))


def check_cds01(result):
    assert result["cds"]["status"] == "success", f"CDS failed: {result['cds']['error']}"
    assert result["cds"]["clinical_considerations"], "No clinical consideration was stored"
    assert cited(result) <= {HIGH}, f"Cited evidence outside the relevant set: {cited(result)}"
    for key in ("patient_information", "medical_evidence"):
        assert result["state"][key] == result["original"][key], f"{key} was modified"


def run_cds02():
    return run_agent(make_state(), cds_model([("record_treatment_pathway", pathway((HIGH, HIGH)))]))


def check_cds02(result):
    pathways = result["cds"]["treatment_pathways"]
    assert result["cds"]["status"] == "success", f"CDS failed: {result['cds']['error']}"
    assert pathways, "No treatment pathway was recorded"
    for p in pathways:
        assert all(p[k] for k in ("option", "when_considered", "unknown_patient_factors", "risks_and_limitations"))
        assert p["requires_clinician_review"] is True, "Pathway does not require clinician review"
        assert len(p["supporting_evidence"]) == len(set(p["supporting_evidence"])), "Duplicate citations kept"


def run_cds03():
    prompt, useful = cds._context(make_state((HIGH, LOW, MEDIUM)))
    session = cds.CDSSession(useful)
    return {"available": [e["pmid"] for e in json.loads(prompt)["available_evidence"]],
            "low_citation": session.add_consideration(**consideration((LOW,))), "session": session}


def check_cds03(result):
    assert sorted(result["available"]) == sorted([HIGH, MEDIUM]), f"Available evidence: {result['available']}"
    assert result["low_citation"]["success"] is False, "A low-relevance citation was accepted"
    assert not result["session"].considerations


def run_cds04():
    invalid = [consideration(("99999999",)), consideration(consideration=" "), consideration(reasoning=None),
               consideration(limitations=""), consideration(supporting_evidence=HIGH),
               consideration(supporting_evidence=[90000011])]
    session = make_session()
    return {"results": [session.add_consideration(**c) for c in invalid], "session": session}


def check_cds04(result):
    accepted = [r for r in result["results"] if r["success"]]
    assert not accepted, f"{len(accepted)} invalid entries were accepted"
    assert not result["session"].considerations, "An invalid entry was added to the output"


def run_cds05():
    session = make_session()
    session.add_consideration(**consideration((), requires_review=False, context_info=""))
    return {"entry": session.finish()["clinical_considerations"][0], "reviews": session.review_items}


def check_cds05(result):
    assert result["entry"]["supporting_evidence"] == []
    assert result["entry"]["requires_clinician_review"] is True, "Uncited consideration skipped review"
    assert result["entry"]["context"] == "Not specified."
    assert any("Synthetic consideration" in r["item"] for r in result["reviews"]), "No doctor review item added"


MRI_CASES = [(None, "No MRI classification"), ("invalid", "unexpected format"), ({}, "label was not provided"),
             ({"label": "GBM", "confidence": "high"}, "score was invalid"),
             ({"label": "GBM", "confidence": 1.1}, "score was invalid"),
             ({"label": "GBM", "confidence": 0.5}, "low-confidence")]


def run_cds06():
    sessions = [(make_session(mri_findings=f), expected) for f, expected in MRI_CASES]
    return {"sessions": sessions, "boundary": make_session(mri_findings={"label": "GBM", "confidence": 0.7})}


def check_cds06(result):
    for session, expected in result["sessions"]:
        assert expected in " ".join(session.uncertainties), f"Missing uncertainty: {expected}"
        assert session.review_items, "Clinician review requirement was lost"
    low = result["sessions"][-1][0]
    assert len(low.review_items) == 2, "Low confidence did not add a second review item"
    assert result["boundary"].uncertainties == [], "Confidence at the 0.7 threshold was flagged"


def run_cds07():
    record = make_state()["patient_information"]["patient_data"][0]
    state = make_state(records=[record, dict(record, Patient_ID="SYNTHETIC-OTHER")])
    prompt, _ = cds._context(state, previous_reports=[{"summary": "Historical context", "Survival": 12,
                                                      "outcome": "past"}])
    return {"prompt": prompt, "context": json.loads(prompt)}


def check_cds07(result):
    assert "SYNTHETIC-PRIVATE" not in result["prompt"], "Patient identifier reached the prompt"
    assert len(result["context"]["patient_profiles"]) == 1, "Duplicate profiles were not merged"
    assert "Overall Survival (Death)" not in result["context"]["patient_profiles"][0], "Outcome field kept"
    assert result["context"]["previous_reports_summary"] == [{"summary": "Historical context"}]


def run_cds08():
    no_assessments = make_state()["medical_evidence"] | {"evidence_relevance": None}
    no_useful = make_state((LOW,))["medical_evidence"]
    broken = [("patient_information", {"status": "pending"}),
              ("patient_information", {"status": "success", "patient_data": []}),
              ("patient_information", {"status": "success", "patient_data": [None]}),
              ("medical_evidence", {"status": "failed"}),
              ("medical_evidence", {"status": "success", "retrieved_evidence": []}),
              ("medical_evidence", no_assessments), ("medical_evidence", no_useful)]
    outcomes = []
    for key, value in broken:
        state = make_state()
        state[key] = value
        state["clinical_decision_support"]["status"] = "success"  # stale result from an earlier run
        with patch.object(cds, "create_clinical_decision_support_agent") as factory:
            cds.run_clinical_decision_support_agent(state, model=object())
        outcomes.append((state["clinical_decision_support"], factory.called))
    return outcomes


def check_cds08(result):
    for cds_result, model_started in result:
        assert cds_result["status"] == "failed", "Invalid upstream data was accepted"
        assert cds_result["error"], "No error message was given"
        assert not model_started, "The model was started despite invalid upstream data"


def run_cds09():
    model = ScriptedCDSModel([("record_clinical_consideration", consideration())], fail_after_first_step=True)
    return run_agent(make_state(), model)


def check_cds09(result):
    assert result["cds"]["status"] == "failed", "A model failure was reported as success"
    assert len(result["cds"]["clinical_considerations"]) == 1, "Partial output was lost"
    assert "private provider response" not in result["cds"]["error"], "Provider text leaked into the error"


def run_cds10():
    record = {"Patient_ID": "SYNTHETIC-UNSEEN", "Primary Diagnosis": "GBM", "Age at diagnosis": None,
              "Sex at Birth": "Male", "Grade of Primary Brain Tumor": None}
    model = cds_model([
        ("record_clinical_consideration", consideration((MEDIUM,), consideration="Atypical presentation",
                                                        limitations="Evidence is limited to a small case series.")),
        ("record_treatment_pathway", pathway((MEDIUM,), option="Repeat imaging or biopsy")),
        ("record_uncertainty", {"description": "Age at diagnosis and tumour grade are unknown."})])
    return run_agent(make_state((MEDIUM, LOW), records=[record]), model,
                     mri_findings={"classification": "GBM", "confidence": 0.55})


def check_cds10(result):
    out = result["cds"]
    assert out["status"] == "success", f"CDS failed: {out['error']}"
    assert cited(result) <= {MEDIUM}, f"Cited evidence outside the available set: {cited(result)}"
    assert any("low-confidence" in u for u in out["uncertainties"]), "Provisional MRI result not flagged"
    assert len(out["uncertainties"]) >= 2, "Unknown patient details were not recorded"
    assert all(p["requires_clinician_review"] for p in out["treatment_pathways"])
    assert out["doctor_review_items"], "No clinician review was required"


CASES = [
    {"id": "CDS-01", "name": "Valid patient information and relevant evidence", "run": run_cds01,
     "expect": "Stores evidence-linked considerations without modifying upstream data.", "check": check_cds01},
    {"id": "CDS-02", "name": "Treatment pathway with valid evidence", "run": run_cds02,
     "expect": "Records the full pathway and marks it as requiring clinician review.", "check": check_cds02},
    {"id": "CDS-03", "name": "Relevant and irrelevant evidence", "run": run_cds03,
     "expect": "Only high or medium relevance evidence can be cited.", "check": check_cds03},
    {"id": "CDS-04", "name": "Unknown PMID or missing required fields", "run": run_cds04,
     "expect": "Rejects the invalid entry without adding it to the output.", "check": check_cds04},
    {"id": "CDS-05", "name": "Uncited consideration that requests no review", "run": run_cds05,
     "expect": "Records it with no evidence and requires clinician review.", "check": check_cds05},
    {"id": "CDS-06", "name": "Missing, malformed or low-confidence MRI findings", "run": run_cds06,
     "expect": "Records the uncertainty; low confidence adds a review item.", "check": check_cds06},
    {"id": "CDS-07", "name": "Identifiers, duplicate profiles and outcomes", "run": run_cds07,
     "expect": "Removes identifiers and outcomes and merges duplicate profiles.", "check": check_cds07},
    {"id": "CDS-08", "name": "Unsuccessful or malformed upstream information", "run": run_cds08,
     "expect": "Fails with a clear error, clears stale success and never starts the model.", "check": check_cds08},
    {"id": "CDS-09", "name": "Model fails after recording a consideration", "run": run_cds09,
     "expect": "Keeps partial output, fails the run and reports a sanitised error.", "check": check_cds09},
    {"id": "CDS-10", "name": "Unseen mix of missing details, provisional MRI and limited evidence",
     "run": run_cds10, "expect": "Keeps unknowns, cites only available evidence and requires review.",
     "check": check_cds10},
]


@pytest.mark.parametrize("case", CASES, ids=[c["id"] for c in CASES])
def test_clinical_decision_support(case, record):
    result, metrics = run(case["run"])
    passed, reason = check_case(case, result)
    record(case, passed, reason, metrics)
    assert passed, reason
