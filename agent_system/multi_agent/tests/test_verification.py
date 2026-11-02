"""Verification Agent: 8 cases (VA-01 to VA-08) using hand-written claims and evidence."""

import pytest

import verification_agent as agent
from shared_state import create_initial_state
from conftest import check_case
from fake_models import judge_model
from measure import run

PMID = "90000001"
EVIDENCE = {"pmid": PMID, "title": "Controlled study", "publication_types": [], "retraction_flags": [],
            "abstract": "In the study cohort, temozolomide with radiotherapy was associated with improved survival."}


def make_state(claims, evidence_ok=True):
    """Build a state holding the given claims. Each claim is (text, cited_pmids[, needs_review])."""
    state = create_initial_state("Controlled verification request")
    state["patient_information"].update(status="success", patient_data=[])
    state["medical_evidence"].update(
        status="success" if evidence_ok else "failed",
        retrieved_evidence=[EVIDENCE] if evidence_ok else [],
        evidence_relevance=[{"pmid": PMID, "relevance": "high"}])
    state["clinical_decision_support"].update(
        status="success", treatment_pathways=[],
        doctor_review_items=[{"item": "Clinician review", "reason": "Required."}],
        clinical_considerations=[{
            "consideration": text, "reasoning": text, "context": "Controlled test",
            "limitations": "Not patient-specific advice.", "supporting_evidence": pmids,
            "requires_clinician_review": review[0] if review else True}
            for text, pmids, *review in claims])
    return state


def verdicts(result):
    return [c["verdict"] for c in result["semantic_checks"]]


def has_issue(result, *words):
    return any(all(w.lower() in issue.lower() for w in words) for issue in result["issues"])


def check_supported(result):
    assert result["verification_status"] == "approved", "Supported claim was not approved"
    assert verdicts(result) == ["supported"], f"Verdicts: {verdicts(result)}"


def check_cited_support(result):
    assert verdicts(result) == ["supported"], f"Verdicts: {verdicts(result)}"
    assert result["revision_required"] is False


def check_citation_does_not_support(result):
    assert result["revision_required"] is True, "Unsupported claim was accepted"
    assert has_issue(result, "does not support"), f"Issues: {result['issues']}"


def check_no_citation(result):
    assert result["revision_required"] is True
    assert has_issue(result, "no supporting evidence"), f"Issues: {result['issues']}"


def check_bad_pmid(result):
    assert result["revision_required"] is True
    assert has_issue(result, "99999999", "not retrieved"), f"Issues: {result['issues']}"


def check_contradiction(result):
    assert has_issue(result, "contradict"), f"Issues: {result['issues']}"


def check_evidence_failure(result):
    assert result["verification_status"] != "approved", "Claims were confirmed without evidence"
    assert result["revision_required"] is True
    assert has_issue(result, "Medical Evidence Agent did not complete"), f"Issues: {result['issues']}"


def check_mixed(result):
    assert len(verdicts(result)) == 3, f"Expected 3 verdicts, got {verdicts(result)}"
    assert "supported" in verdicts(result), "No claim was marked supported"
    assert set(verdicts(result)) & {"partial", "unsupported"}, "No claim was marked unsupported"
    assert result["revision_required"] is True


CASES = [
    {"id": "VA-01", "name": "All CDS claims supported",
     "state": make_state([("Temozolomide with radiotherapy was associated with improved survival.", [PMID])]),
     "expect": "Accepts the supported claims and validates the citations.", "check": check_supported},
    {"id": "VA-02", "name": "Valid citation supports the claim",
     "state": make_state([("The study reports an association between temozolomide and survival.", [PMID])]),
     "expect": "Confirms that the cited evidence supports the specific claim.", "check": check_cited_support},
    {"id": "VA-03", "name": "Citation does not support the claim",
     "state": make_state([("Temozolomide cures every patient.", [PMID])]),
     "expect": "Flags the unsupported claim rather than accepting it.", "check": check_citation_does_not_support},
    {"id": "VA-04", "name": "Claim without a citation",
     "state": make_state([("Uncited clinical claim.", [], False)]),
     "expect": "Identifies the claim as lacking evidence.", "check": check_no_citation},
    {"id": "VA-05", "name": "Non-existent PMID",
     "state": make_state([("Claim with invalid citation.", ["99999999"])]),
     "expect": "Flags the citation as invalid or unverifiable.", "check": check_bad_pmid},
    {"id": "VA-06", "name": "Contradictory claims",
     "state": make_state([("Temozolomide improves survival.", [PMID]),
                          ("Temozolomide does not improve survival.", [PMID])]),
     "expect": "Identifies the contradiction and requests correction or review.", "check": check_contradiction},
    {"id": "VA-07", "name": "Evidence retrieval failed",
     "state": make_state([("Claim not checked.", [])], evidence_ok=False),
     "expect": "Reports that verification could not be completed rather than confirming the claims.",
     "check": check_evidence_failure},
    {"id": "VA-08", "name": "Unseen mix of supported and unsupported claims",
     "state": make_state([("Temozolomide with radiotherapy improves survival.", [PMID]),
                          ("Temozolomide always cures glioblastoma.", [PMID]),
                          ("Temozolomide improves survival in every population.", [PMID])]),
     "expect": "Distinguishes supported claims from unsupported ones and explains its decisions.",
     "check": check_mixed},
]


@pytest.mark.parametrize("case", CASES, ids=[c["id"] for c in CASES])
def test_verification(case, record):
    state, metrics = run(lambda: agent.run_verification_agent(case["state"], model=judge_model()))
    result = state["verification"]
    passed, reason = check_case(case, result)
    record(case, passed, reason, metrics)
    assert passed, reason
