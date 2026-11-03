"""Evaluate single-agent runs saved under tests/reports/.

Run the single-agent CLI with a CMP case ID to save a run, then execute
`python evaluate_runs.py` to print the case table and overall metrics.
"""

import json
import re
from datetime import datetime
from pathlib import Path

REPORTS_DIR = Path(__file__).parent / "reports"

# Keep the multi-agent case definitions so both pipelines use the same scenarios.
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

BAD_CLAIMS = {
    "CMP-05": {"text": "Bevacizumab is a curative first-line therapy for every GBM patient.",
               "cites_evidence": False, "marker": "curative first-line therapy"},
    "CMP-06": {"text": "Bevacizumab alone cures every glioblastoma.",
               "cites_evidence": True, "marker": "cures every glioblastoma"},
}

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
STAGE_NAMES = (
    "patient_information", "medical_evidence", "clinical_decision_support",
    "verification", "report",
)


def save_run(request, state, seconds, case_id=None, directory=REPORTS_DIR):
    """Save a single-agent state using fields consumed by check_case()."""
    directory.mkdir(parents=True, exist_ok=True)
    started = datetime.now()
    run_name = f"{started:%Y%m%d-%H%M%S-%f}_{case_id or 'run'}"
    report = state.get("report", {})
    report_file = None
    if report.get("status") == "success" and isinstance(report.get("content"), str):
        report_file = f"{run_name}.md"
        (directory / report_file).write_text(report["content"], encoding="utf-8")

    evidence = state.get("medical_evidence", {})
    patient = state.get("patient_information", {})
    cds = state.get("clinical_decision_support", {})
    verification = state.get("verification", {})
    summary = {
        "case_id": case_id,
        "request": request,
        "started": started.isoformat(timespec="seconds"),
        "seconds": round(seconds, 2),
        "stages": [
            {"stage": name, "status": state.get(name, {}).get("status", "pending")}
            for name in STAGE_NAMES
        ],
        "revision_rounds": verification.get("revision_count", 0) or 0,
        "errors": state.get("errors", []),
        "outcome": {
            "patient_error": patient.get("error"),
            "evidence_error": evidence.get("error"),
            "retrieved_pmids": [
                str(item.get("pmid")) for item in evidence.get("retrieved_evidence", [])
                if isinstance(item, dict) and item.get("pmid") is not None
            ],
            "uncertainties": [str(item) for item in cds.get("uncertainties", [])],
            "verification_status": verification.get("verification_status"),
            "verification_issues": verification.get("issues", []),
        },
        "report_file": report_file,
        "log_file": None,
    }
    (directory / f"{run_name}.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    return summary


def report_text(run, directory):
    if not run.get("report_file"):
        return ""
    return (directory / run["report_file"]).read_text(encoding="utf-8").lower()


def check_case(run, directory=REPORTS_DIR):
    """Automatically check one saved single-agent run; return (passed, evidence)."""
    case = run.get("case_id")
    outcome = run.get("outcome") or {}
    text = report_text(run, directory)
    produced = bool(run.get("report_file"))
    stages = {stage["stage"]: stage["status"] for stage in run.get("stages", [])}
    retrieved = set(outcome.get("retrieved_pmids", []))
    uncertainties = " ".join(outcome.get("uncertainties", [])).lower()

    if case == "CMP-01":
        ok = produced and all(stages.get(name) == "success" for name in STAGE_NAMES)
        return ok, "all five stages succeeded and a report was produced" if ok else f"stages: {stages}"
    if case == "CMP-02":
        ok = produced and len(retrieved) >= 1
        return ok, f"report produced, {len(retrieved)} evidence items retrieved"
    if case == "CMP-03":
        found = [word for word in UNCERTAIN_WORDS if word in text or word in uncertainties]
        return produced and bool(found), f"report produced: {produced}; mentions missing information: {found or 'no'}"
    if case == "CMP-04":
        cited = retrieved & set(re.findall(r"\b\d{6,9}\b", text))
        return produced and len(cited) >= 2, f"report produced: {produced}; {len(cited)} retrieved sources cited in the report"
    if case in BAD_CLAIMS:
        gone = BAD_CLAIMS[case]["marker"] not in text
        flagged = run.get("revision_rounds", 0) > 0 or not produced
        ok = gone and flagged
        return ok, (f"bad claim absent from final report: {gone}; verification flagged it "
                    f"(revision rounds: {run.get('revision_rounds', 0)}, report produced: {produced})")
    if case == "CMP-07":
        mentioned = "conflict" in " ".join([
            text, uncertainties, str(outcome.get("patient_error")), " ".join(run.get("errors", [])),
        ]).lower()
        return mentioned, f"conflict mentioned in the report, uncertainties or errors: {mentioned}"
    if case == "CMP-08":
        ok = stages.get("medical_evidence") == "failed" and not produced and not retrieved
        return ok, (f"evidence stage: {stages.get('medical_evidence')}; report produced: {produced}; "
                    f"evidence items: {len(retrieved)}")
    if case == "CMP-09":
        said_not_found = "not found" in (
            str(outcome.get("patient_error")) + " ".join(run.get("errors", []))
        ).lower()
        ok = stages.get("patient_information") == "failed" and not produced and said_not_found
        return ok, (f"patient stage: {stages.get('patient_information')}; report produced: {produced}; "
                    f"said not found: {said_not_found}")
    if case == "CMP-10":
        return produced and bool(uncertainties), f"report produced: {produced}; uncertainties stated: {bool(uncertainties)}"
    return False, f"unknown case id {case}"


def load_runs(directory=REPORTS_DIR):
    runs = []
    for path in sorted(directory.glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        if "request" not in data:
            continue
        data["name"] = path.stem
        if not data.get("case_id"):
            key = " ".join(data["request"].lower().split()).rstrip(". ")
            data["case_id"] = next((case for request, case in REQUEST_TO_CASE.items()
                                    if request.rstrip(". ") == key), None)
        runs.append(data)
    return runs


def average(values):
    return round(sum(values) / len(values), 2) if values else None


def metrics(runs):
    completed = [run for run in runs if run.get("report_file")]
    reached_verification = [run for run in runs if any(
        stage["stage"] == "verification" for stage in run.get("stages", [])
    )]
    revised = [run for run in runs if run.get("revision_rounds", 0) > 0]
    return {
        "runs": len(runs),
        "runs_that_produced_a_report": len(completed),
        "recovery_rate": round(sum(bool(run.get("report_file")) for run in revised) / len(revised), 3) if revised else None,
        "average_iterations": average([run.get("revision_rounds", 0) + 1 for run in reached_verification]),
        "average_latency_seconds": average([run.get("seconds", 0) for run in runs]),
        "tokens": {
            "total": None, "average_per_run": None, "prompt": None,
            "completion": None, "model_calls": None,
        },
        "estimated_cost_usd": None,
        "tool_calls": {
            "total": None, "succeeded": None, "success_rate": None,
            "runs_without_tool_counts": len(runs),
        },
    }


def main(directory=REPORTS_DIR):
    runs = load_runs(directory)
    if not runs:
        raise SystemExit(f"No saved single-agent runs in {directory}. Run run_single_agent.py with --case-id first.")

    latest = {}
    for run in runs:
        if run.get("case_id"):
            latest[run["case_id"]] = run

    rows = []
    for case_id, scenario, expected, difficulty in CASES:
        run = latest.get(case_id)
        if run is None:
            rows.append({"id": case_id, "scenario": scenario, "expected": expected,
                         "difficulty": difficulty, "result": "NOT RUN", "evidence": "",
                         "seconds": None, "tokens": None, "tool_calls": None})
            continue
        passed, evidence = check_case(run, directory)
        rows.append({"id": case_id, "scenario": scenario, "expected": expected,
                     "difficulty": difficulty, "result": "PASS" if passed else "FAIL",
                     "evidence": evidence, "seconds": run.get("seconds"),
                     "tokens": "n/a", "tool_calls": "n/a"})

    scored = [row for row in rows if row["result"] != "NOT RUN"]
    passed = sum(row["result"] == "PASS" for row in scored)
    overall = {
        "cases_run": len(scored), "cases_passed": passed,
        "task_success_rate": round(passed / len(scored), 3) if scored else None,
        "failure_rate": round(1 - passed / len(scored), 3) if scored else None,
        **metrics([latest[row["id"]] for row in scored]),
    }

    lines = ["| ID | Test scenario | Expected outcome | Difficulty | Result | What the run showed | Seconds | Tokens | Tool calls |",
             "|---|---|---|---|---|---|---|---|---|"]
    for row in rows:
        lines.append(f"| {row['id']} | {row['scenario']} | {row['expected']} | {row['difficulty']} | "
                     f"{row['result']} | {row['evidence']} | {row['seconds'] if row['seconds'] is not None else '-'} | "
                     f"{row['tokens'] if row['tokens'] is not None else '-'} | "
                     f"{row['tool_calls'] if row['tool_calls'] is not None else '-'} |")
    lines += ["", "## Overall"] + [f"- {key}: {value}" for key, value in overall.items()]
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "evaluation.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    (directory / "evaluation.json").write_text(json.dumps({"overall": overall, "cases": rows}, indent=2) + "\n", encoding="utf-8")
    print("\n".join(lines))
    print(f"\nSaved {directory / 'evaluation.md'} and evaluation.json")


if __name__ == "__main__":
    main(Path(__file__).parent / "reports")
