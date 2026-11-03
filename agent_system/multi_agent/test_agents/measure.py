"""Helpers: time and cost a run, and write the per-area result files."""

import json
import time
from pathlib import Path

from fake_models import MODE
from test_pipeline.run_recorder import USAGE  # running total of every model call

RESULTS_DIR = Path(__file__).parent / "results"
ROWS = []  # one dict per test case, filled in by the `record` fixture in conftest.py


def run(fn):
    """Call fn() and return (result, metrics) with seconds, tokens and cost for that call."""
    tokens, cost, start = USAGE["tokens"], USAGE["cost"], time.perf_counter()
    result = fn()
    return result, {
        "seconds": time.perf_counter() - start,
        "tokens": USAGE["tokens"] - tokens,
        "cost": USAGE["cost"] - cost,
    }


def _average(values):
    values = [v for v in values if v is not None]
    return round(sum(values) / len(values), 3) if values else None


AREAS = {
    "PI": "patient_info",
    "CDS": "clinical_decision_support",
    "VA": "verification",
    "ME": "medical_evidence",
    "RG": "report_generation",
}


def write_report():
    """Write results/<area>.json: a summary per area, plus the result of every case.

    Patient Info makes no model calls, so it only reports outcomes.
    """
    RESULTS_DIR.mkdir(exist_ok=True)
    for prefix, area in AREAS.items():
        rows = [r for r in ROWS if r["id"].startswith(prefix + "-")]
        if not rows:
            continue
        passed = sum(r["passed"] for r in rows)
        summary = {
            "mode": MODE,
            "cases_run": len(rows),
            "task_success_rate": round(passed / len(rows), 3),
            "failure_rate": round(1 - passed / len(rows), 3),
            "average_latency_seconds": _average(r["seconds"] for r in rows),
        }
        cases = [{"id": r["id"], "scenario": r["name"], "passed": r["passed"],
                  "reason": " ".join(str(r["reason"]).split())[:200]} for r in rows]
        if prefix != "PI":
            summary["total_tokens"] = sum(r["tokens"] for r in rows)
            summary["estimated_cost_usd"] = round(sum(r["cost"] for r in rows), 4)
            for case, r in zip(cases, rows):
                case.update(seconds=round(r["seconds"], 3),
                            tokens=r["tokens"], cost_usd=round(r["cost"], 4))
        summary["cases"] = cases
        (RESULTS_DIR / f"{area}.json").write_text(json.dumps(summary, indent=2) + "\n")
