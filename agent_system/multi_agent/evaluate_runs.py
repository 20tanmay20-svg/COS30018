"""Evaluate the runs saved in reports/ by main.py.

main.py prints PASS/FAIL for a case right after the run (type `CMP-03: Prepare a report for ...`).
Run `python3 evaluate_runs.py` for the full table of all ten cases plus overall metrics.
Writes reports/evaluation.json and reports/evaluation.md.
"""

import json
import re
import sys
from pathlib import Path

REPORTS_DIR = Path(__file__).parent / "reports"

# (id, scenario, expected outcome, difficulty)
CASES = [
    ("CMP-01", "Valid patient record with complete clinical history and clear MRI findings",
     "Generates a complete report consistent with the supplied information", "Simple"),
    ("CMP-02", "Patient record with relevant medical history and straightforward evidence retrieval",
     "Incorporates relevant history and retrieves appropriate supporting evidence", "Simple"),
    ("CMP-03", "Patient record contains missing clinical information",
     "Identifies missing details without inventing information", "Moderate"),
    ("CMP-04", "MRI findings require multiple relevant medical evidence sources",
     "Produces a report supported by relevant evidence and valid citations", "Moderate"),
    ("CMP-05", "CDS output contains an unsupported clinical claim",
     "Identifies, removes or flags the unsupported claim before finalising the report", "Moderate"),
    ("CMP-06", "Retrieved evidence contains a citation that does not support its associated claim",
     "Detects the citation mismatch and avoids presenting the claim as verified", "Difficult"),
    ("CMP-07", "Clinical history and supplied findings contain conflicting information",
     "Identifies the inconsistency and communicates uncertainty appropriately", "Difficult"),
    ("CMP-08", "Evidence retrieval tool returns no results or encounters an error",
     "Handles the failure gracefully and does not fabricate supporting evidence", "Edge case"),
    ("CMP-09", "Invalid or nonexistent patient ID is supplied",
     "Reports the patient record cannot be found and avoids a misleading patient-specific report", "Edge case"),
    ("CMP-10", "Previously unseen patient case with a combination of findings not used during development",
     "Processes the case accurately, generates an appropriate report and handles evidence limitations", "Unseen"),
]

# Faulty claims that fault_injection.py adds to the CDS output for CMP-05 and CMP-06.
BAD_CLAIMS = {
    "CMP-05": {"text": "Bevacizumab is a curative first-line therapy for every GBM patient.",
               "cites_evidence": False, "marker": "curative first-line therapy"},
    "CMP-06": {"text": "Bevacizumab alone cures every glioblastoma.",
               "cites_evidence": True, "marker": "cures every glioblastoma"},
}

# Runs saved without a case ID (typed without the "CMP-xx:" prefix) are matched by their request text.
REQUEST_TO_CASE = {
    "prepare a report for patientid_0003. the mri findings are clear and consistent with the recorded history.": "CMP-01",
    "prepare a report for patientid_0003. use the medical history and retrieve relevant literature.": "CMP-02",
    "prepare a report for patientid_0004. some history fields are missing; identify unknowns without guessing.": "CMP-03",
    "prepare a report for patientid_0003. use multiple independent evidence sources.": "CMP-04",
    "prepare a report for patientid_0005. assess this new combination of atypical findings; state evidence limits.": "CMP-10",
    "prepare a report for patientid_99999999.": "CMP-09",
}

UNCERTAIN_WORDS = ("unknown", "missing", "not documented", "not recorded", "not available",
                   "not provided", "unavailable")


# ---------------------------------------------------------
# Per-case checks

def report_text(run, directory):
    if not run["report_file"]:
        return ""
    return (directory / run["report_file"]).read_text(encoding="utf-8").lower()


def log_text(run, directory):
    path = directory / run.get("log_file", "")
    return path.read_text(encoding="utf-8").lower() if run.get("log_file") and path.exists() else ""


def check_case(run, directory=REPORTS_DIR):
    """Automatic check of one saved run against its case. Returns (passed, evidence)."""
    case = run["case_id"]
    out = run.get("outcome")
    text = report_text(run, directory)
    produced = bool(run["report_file"])
    stages = {s["stage"]: s["status"] for s in run["stages"]}
    if out is None:  # run saved before the extra details were recorded: judge from the report text instead
        out = {}
        retrieved = set(re.findall(r"\b\d{6,9}\b", text))
        uncertainties = text
    else:
        retrieved = set(out.get("retrieved_pmids", []))
        uncertainties = " ".join(out.get("uncertainties", [])).lower()

    if case == "CMP-01":
        ok = produced and all(stages.get(s) == "success" for s in
                              ("patient_information", "medical_evidence", "clinical_decision_support", "verification", "report"))
        return ok, "all five stages succeeded and a report was produced" if ok else f"stages: {stages}"
    if case == "CMP-02":
        ok = produced and len(retrieved) >= 1
        return ok, f"report produced, {len(retrieved)} evidence items retrieved"
    if case == "CMP-03":
        found = [w for w in UNCERTAIN_WORDS if w in text or w in uncertainties]
        return produced and bool(found), f"report produced: {produced}; mentions missing information: {found or 'no'}"
    if case == "CMP-04":
        cited = retrieved & set(re.findall(r"\b\d{6,9}\b", text))
        return produced and len(cited) >= 2, f"report produced: {produced}; {len(cited)} retrieved sources cited in the report"
    if case in BAD_CLAIMS:
        gone = BAD_CLAIMS[case]["marker"] not in text
        flagged = run["revision_rounds"] > 0 or not produced
        ok = gone and flagged
        return ok, (f"bad claim absent from final report: {gone}; verification flagged it "
                    f"(revision rounds: {run['revision_rounds']}, report produced: {produced})")
    if case == "CMP-07":
        mentioned = "conflict" in " ".join([text, uncertainties, str(out.get("patient_error")), " ".join(run["errors"])]).lower()
        return mentioned, f"conflict mentioned in the report, uncertainties or errors: {mentioned}"
    if case == "CMP-08":
        ok = stages.get("medical_evidence") == "failed" and not produced and not retrieved
        return ok, (f"evidence stage: {stages.get('medical_evidence')}; report produced: {produced}; "
                    f"evidence items: {len(retrieved)}")
    if case == "CMP-09":
        said_not_found = "not found" in (str(out.get("patient_error")) + " ".join(run["errors"]) + log_text(run, directory)).lower()
        ok = stages.get("patient_information") == "failed" and not produced and said_not_found
        return ok, f"patient stage: {stages.get('patient_information')}; report produced: {produced}; said not found: {said_not_found}"
    if case == "CMP-10":
        return produced and bool(uncertainties), f"report produced: {produced}; uncertainties stated: {bool(uncertainties)}"
    return False, f"unknown case id {case}"


# ---------------------------------------------------------
# Overall metrics

def load_runs(directory):
    runs = []
    for path in sorted(directory.glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        if "request" in data:  # skips evaluation.json
            data["name"] = path.stem
            tagged = re.match(r"\s*(CMP-(?:01|02|03|04|09|10))\s*[:\-]", data["request"])  # cases that need no fault
            if not data.get("case_id") and tagged:  # typed with the prefix in an old main.py session
                data["case_id"] = tagged.group(1)
            if not data.get("case_id"):
                key = " ".join(data["request"].lower().split()).rstrip(". ")  # ignore a missing final period
                data["case_id"] = next((c for text, c in REQUEST_TO_CASE.items() if text.rstrip(". ") == key), None)
            runs.append(data)
    return runs


def average(values):
    return round(sum(values) / len(values), 2) if values else None


def metrics(runs):
    done = [r for r in runs if r["report_file"]]
    reached_verification = [r for r in runs if any(s["stage"] == "verification" for s in r["stages"])]
    revised = [r for r in runs if r["revision_rounds"] > 0]
    with_tools = [r for r in runs if "tool_calls" in r]  # older run files have no tool counts
    tool_total = sum(r["tool_calls"]["total"] for r in with_tools)
    tool_ok = sum(r["tool_calls"]["succeeded"] for r in with_tools)
    return {
        "runs": len(runs),
        "runs_that_produced_a_report": len(done),
        "recovery_rate": round(sum(bool(r["report_file"]) for r in revised) / len(revised), 3) if revised else None,
        "average_iterations": average([r["revision_rounds"] + 1 for r in reached_verification]),
        "average_latency_seconds": average([r["seconds"] for r in runs]),
        "tokens": {"total": sum(r["tokens"]["total"] for r in runs),
                   "average_per_run": average([r["tokens"]["total"] for r in runs]),
                   "prompt": sum(r["tokens"]["prompt"] for r in runs),
                   "completion": sum(r["tokens"]["completion"] for r in runs),
                   "model_calls": sum(r["tokens"]["model_calls"] for r in runs)},
        "estimated_cost_usd": round(sum(r["tokens"]["estimated_cost_usd"] for r in runs), 4),
        "tool_calls": {"total": tool_total, "succeeded": tool_ok,
                       "success_rate": round(tool_ok / tool_total, 3) if tool_total else None,
                       "runs_without_tool_counts": len(runs) - len(with_tools)},
    }


# ---------------------------------------------------------
# Full evaluation

def main(directory=REPORTS_DIR):
    runs = load_runs(directory)
    if not runs:
        raise SystemExit(f"No saved runs in {directory}. Run main.py first.")

    latest = {}  # the most recent run of each case
    for run in runs:
        if run.get("case_id"):
            latest[run["case_id"]] = run

    rows = []
    for case_id, scenario, expected, difficulty in CASES:
        run = latest.get(case_id)
        if run is None:
            rows.append({"id": case_id, "scenario": scenario, "expected": expected, "difficulty": difficulty,
                         "result": "NOT RUN", "evidence": "", "seconds": None, "tokens": None, "tool_calls": None})
            continue
        passed, evidence = check_case(run, directory)
        calls = run.get("tool_calls")
        rows.append({"id": case_id, "scenario": scenario, "expected": expected, "difficulty": difficulty,
                     "result": "PASS" if passed else "FAIL", "evidence": evidence, "seconds": run["seconds"],
                     "tokens": run["tokens"]["total"],
                     "tool_calls": f"{calls['succeeded']}/{calls['total']}" if calls else "n/a"})

    scored = [r for r in rows if r["result"] != "NOT RUN"]
    passed = sum(r["result"] == "PASS" for r in scored)
    overall = {"cases_run": len(scored), "cases_passed": passed,
               "task_success_rate": round(passed / len(scored), 3) if scored else None,
               "failure_rate": round(1 - passed / len(scored), 3) if scored else None,
               **metrics([latest[r["id"]] for r in scored])}

    lines = ["| ID | Test scenario | Expected outcome | Difficulty | Result | What the run showed | Seconds | Tokens | Tool calls |",
             "|---|---|---|---|---|---|---|---|---|"]
    for r in rows:
        lines.append(f"| {r['id']} | {r['scenario']} | {r['expected']} | {r['difficulty']} | {r['result']} | "
                     f"{r['evidence']} | {r['seconds'] or '-'} | {r['tokens'] or '-'} | {r['tool_calls'] or '-'} |")
    lines += ["", "## Overall"] + [f"- {key}: {value}" for key, value in overall.items()]
    (directory / "evaluation.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    (directory / "evaluation.json").write_text(json.dumps({"overall": overall, "cases": rows}, indent=2) + "\n", encoding="utf-8")

    print("\n".join(lines))
    print(f"\nSaved {directory / 'evaluation.md'} and evaluation.json")


if __name__ == "__main__":
    main(Path(sys.argv[1]) if len(sys.argv) > 1 else REPORTS_DIR)
