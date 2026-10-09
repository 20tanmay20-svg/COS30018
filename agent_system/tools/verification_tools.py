"""Verification tools for the GBM decision-support pipeline.

Two kinds of tool live here, both independent of any model:

1. verify_cds_output      - deterministic structural / evidence-linking checks.
2. SemanticCheckSession   - validated storage for the model's judgement of whether
                            each cited abstract actually supports the claim citing it.

Neither makes clinical decisions. Item numbers are 1-based throughout.
"""

from copy import deepcopy
import threading
from typing import Any

USEFUL_RELEVANCE = {"high", "medium"}
VERDICTS = {"supported", "partial", "unsupported"}
ITEM_TYPES = {"consideration", "pathway"}


def _is_retracted(record: dict[str, Any]) -> bool:
    return bool(record.get("retraction_flags")) or any(
        "retract" in str(t).lower() for t in record.get("publication_types", []) or []
    )


# ---------------------------------------------------------
# 1. Deterministic checks

def verify_cds_output(
    patient_information: dict[str, Any],
    medical_evidence: dict[str, Any],
    clinical_decision_support: dict[str, Any],
) -> dict[str, Any]:
    """
    Verify the structural and evidence-linking integrity of CDS output.

    This tool performs deterministic checks. It does not make clinical
    decisions or assess whether a treatment is medically appropriate.

    Args:
        patient_information: Successful Patient Information Agent output.
        medical_evidence: Successful Medical Evidence Agent output.
        clinical_decision_support: CDS Agent output to verify.

    Returns:
        Dictionary containing verification issues and whether revision is required.
    """

    issues = []

    # ---------------------------------------------------------
    # Validate upstream state

    if patient_information.get("status") != "success":
        issues.append("Patient Information Agent did not complete successfully.")

    if medical_evidence.get("status") != "success":
        issues.append("Medical Evidence Agent did not complete successfully.")

    if clinical_decision_support.get("status") != "success":
        issues.append("Clinical Decision Support Agent did not complete successfully.")

    # ---------------------------------------------------------
    # Retrieved evidence, with each paper's relevance rating

    records = {
        str(r.get("pmid")): r
        for r in medical_evidence.get("retrieved_evidence", []) or []
        if isinstance(r, dict) and r.get("pmid")
    }
    relevance = {
        str(a.get("pmid")): a.get("relevance")
        for a in medical_evidence.get("evidence_relevance", []) or []
        if isinstance(a, dict) and a.get("pmid")
    }

    considerations = clinical_decision_support.get("clinical_considerations", []) or []
    pathways = clinical_decision_support.get("treatment_pathways", []) or []

    if not considerations and not pathways:
        issues.append("The CDS output contains no considerations or treatment pathways.")

    def check_citations(label: str, pmids: list) -> None:
        for pmid in pmids:
            pmid = str(pmid)
            record = records.get(pmid)
            if record is None:
                issues.append(
                    f"{label} cites PMID {pmid}, which was not retrieved "
                    "by the Medical Evidence Agent."
                )
                continue
            if relevance.get(pmid) not in USEFUL_RELEVANCE:
                issues.append(
                    f"{label} cites PMID {pmid}, which was not assessed as "
                    "high or medium relevance."
                )
            if _is_retracted(record):
                issues.append(
                    f"{label} cites PMID {pmid}, which carries a retraction "
                    "or expression-of-concern flag."
                )

    # ---------------------------------------------------------
    # Check CDS considerations

    for index, consideration in enumerate(considerations, start=1):
        label = f"Clinical consideration {index}"
        if not isinstance(consideration, dict):
            issues.append(f"{label} has an invalid format.")
            continue

        pmids = consideration.get("supporting_evidence", [])
        if not isinstance(pmids, list):
            issues.append(f"{label} has invalid supporting evidence.")
            continue

        check_citations(label, pmids)

        if not pmids and consideration.get("requires_clinician_review") is not True:
            issues.append(
                f"{label} has no supporting evidence but is not marked "
                "for clinician review."
            )

    # ---------------------------------------------------------
    # Check treatment pathways

    for index, pathway in enumerate(pathways, start=1):
        label = f"Treatment pathway {index}"
        if not isinstance(pathway, dict):
            issues.append(f"{label} has an invalid format.")
            continue

        pmids = pathway.get("supporting_evidence", [])
        if not isinstance(pmids, list):
            issues.append(f"{label} has invalid supporting evidence.")
            continue

        check_citations(label, pmids)

        if pathway.get("requires_clinician_review") is not True:
            issues.append(f"{label} is not marked for clinician review.")

    # ---------------------------------------------------------
    # Check that doctor review items exist

    review_items = clinical_decision_support.get("doctor_review_items", [])
    if not isinstance(review_items, list) or not review_items:
        issues.append("No doctor-review items were provided by the CDS Agent.")

    return {
        "passed": not issues,
        "issues": issues,
        "revision_required": bool(issues),
    }


# ---------------------------------------------------------
# 2. Semantic check session

class SemanticCheckSession:
    """Per-run store for the model's verdicts. The model can only judge items that
    exist and cite retrieved evidence, and only after reading that evidence."""

    def __init__(self, state: dict[str, Any]):
        cds = state.get("clinical_decision_support", {}) or {}
        evidence = state.get("medical_evidence", {}) or {}
        self.records = {
            str(r.get("pmid")): r
            for r in evidence.get("retrieved_evidence", []) or []
            if isinstance(r, dict) and r.get("pmid")
        }
        self.assessments = {
            str(a.get("pmid")): a
            for a in evidence.get("evidence_relevance", []) or []
            if isinstance(a, dict) and a.get("pmid")
        }
        self.items: dict[tuple[str, int], dict] = {}
        for n, entry in enumerate(cds.get("clinical_considerations", []) or [], start=1):
            if isinstance(entry, dict):
                self.items[("consideration", n)] = entry
        for n, entry in enumerate(cds.get("treatment_pathways", []) or [], start=1):
            if isinstance(entry, dict):
                self.items[("pathway", n)] = entry
        self.viewed: set[tuple[str, int]] = set()
        self.checks: dict[tuple[str, int], dict] = {}
        self.lock = threading.RLock()

    def _cited(self, entry: dict) -> list[str]:
        pmids = entry.get("supporting_evidence", [])
        if not isinstance(pmids, list):
            return []
        return [str(p) for p in pmids if str(p) in self.records]

    @staticmethod
    def _text(item_type: str, entry: dict) -> str:
        return str(entry.get("consideration" if item_type == "consideration" else "option") or "")

    def citable_items(self) -> list[dict]:
        """Items with at least one cited PMID that exists in the retrieved evidence."""
        return [
            {"item_type": t, "number": n, "text": self._text(t, e)}
            for (t, n), e in self.items.items() if self._cited(e)
        ]

    def _lookup(self, item_type: str, number: Any):
        if item_type not in ITEM_TYPES:
            return None, "item_type must be 'consideration' or 'pathway'."
        if not isinstance(number, int) or isinstance(number, bool):
            return None, "number must be an integer."
        entry = self.items.get((item_type, number))
        if entry is None:
            return None, f"No {item_type} number {number} exists."
        if not self._cited(entry):
            return None, f"{item_type} {number} cites no retrieved evidence; the rule checks cover it."
        return entry, None

    def get_evidence(self, item_type: str, number: int) -> dict[str, Any]:
        with self.lock:
            entry, error = self._lookup(item_type, number)
            if error:
                return {"success": False, "error": error}
            self.viewed.add((item_type, number))
            if item_type == "consideration":
                claim = {"consideration": entry.get("consideration"),
                         "reasoning": entry.get("reasoning"), "context": entry.get("context")}
            else:
                claim = {"option": entry.get("option"), "when_considered": entry.get("when_considered")}
            cited = []
            for pmid in self._cited(entry):
                assessment = self.assessments.get(pmid, {})
                cited.append({
                    "pmid": pmid, "title": self.records[pmid].get("title"),
                    "abstract": self.records[pmid].get("abstract"),
                    "recorded_supporting_quote": assessment.get("supporting_quote"),
                    "recorded_limitations": assessment.get("limitations"),
                })
            return {"success": True, "claim": claim, "cited_evidence": cited}

    def record_verdict(self, item_type: str, number: int, verdict: str, reason: str) -> dict[str, Any]:
        with self.lock:
            entry, error = self._lookup(item_type, number)
            if error:
                return {"success": False, "error": error}
            if (item_type, number) not in self.viewed:
                return {"success": False, "error": "Read the cited evidence with get_cited_evidence first."}
            if verdict not in VERDICTS:
                return {"success": False, "error": "verdict must be supported, partial, or unsupported."}
            if not isinstance(reason, str) or not reason.strip():
                return {"success": False, "error": "Provide a nonempty reason."}
            self.checks[(item_type, number)] = {
                "item_type": item_type, "number": number, "verdict": verdict,
                "reason": reason.strip(), "assessed_by": "language_model",
            }
            return {"success": True, "checked_count": len(self.checks)}

    def missing(self) -> list[str]:
        """Citable items that have no verdict yet."""
        return [f"{i['item_type']} {i['number']}" for i in self.citable_items()
                if (i["item_type"], i["number"]) not in self.checks]

    def issues(self) -> list[str]:
        """Issue strings for unsupported claims (these require revision)."""
        return [
            f"{c['item_type'].capitalize()} {c['number']}: cited evidence does not support "
            f"this claim. {c['reason']}"
            for c in self.checks.values() if c["verdict"] == "unsupported"
        ]

    def results(self) -> list[dict]:
        return deepcopy(list(self.checks.values()))