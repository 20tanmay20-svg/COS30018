"""Saves every main.py run to reports/: the report, a log of the run, and token usage."""

import json
import logging
import re
import time
from datetime import datetime
from pathlib import Path

import litellm

REPORTS_DIR = Path(__file__).parent.parent / "reports"

USAGE = {"calls": 0, "prompt_tokens": 0, "completion_tokens": 0, "tokens": 0, "cost": 0.0}  # all model calls so far
STAGES = []  # one entry per stage run, filled in by main.py
TOOL_CALLS = []  # one {"tool", "ok"} per agent tool call


def _count_usage(kwargs, response, start, end):
    usage = getattr(response, "usage", None)
    USAGE["calls"] += 1
    USAGE["prompt_tokens"] += getattr(usage, "prompt_tokens", 0) or 0
    USAGE["completion_tokens"] += getattr(usage, "completion_tokens", 0) or 0
    USAGE["tokens"] += getattr(usage, "total_tokens", 0) or 0
    USAGE["cost"] += kwargs.get("response_cost") or 0


if _count_usage not in litellm.success_callback:
    litellm.success_callback.append(_count_usage)


def _count_tool_calls():
    """Wrap smolagents' Tool.__call__ so every agent tool call is recorded. A call fails if it
    raises, or returns a dict with success=False (the convention the project's tools use)."""
    from smolagents.tools import Tool

    if getattr(Tool.__call__, "counted", False):
        return
    original = Tool.__call__

    def counted(self, *args, **kwargs):
        try:
            result = original(self, *args, **kwargs)
        except Exception:
            if self.name != "final_answer":
                TOOL_CALLS.append({"tool": self.name, "ok": False})
            raise
        if self.name != "final_answer":
            ok = not (isinstance(result, dict) and result.get("success") is False)
            TOOL_CALLS.append({"tool": self.name, "ok": ok})
        return result

    counted.counted = True
    Tool.__call__ = counted


_count_tool_calls()


def begin_stage():
    return time.perf_counter(), USAGE["tokens"]


def end_stage(section, began, status):
    STAGES.append({"stage": section, "status": status, "seconds": round(time.perf_counter() - began[0], 2),
                   "tokens": USAGE["tokens"] - began[1]})


def _outcome(state):
    """Facts about the run that the case checks need (no patient data)."""
    evidence = state["medical_evidence"]
    return {
        "patient_error": state["patient_information"].get("error"),
        "evidence_error": evidence.get("error"),
        "retrieved_pmids": [str(e.get("pmid")) for e in evidence.get("retrieved_evidence", []) if isinstance(e, dict)],
        "uncertainties": [str(u) for u in state["clinical_decision_support"].get("uncertainties", [])],
        "verification_status": state["verification"].get("verification_status"),
        "verification_issues": state["verification"].get("issues", []),
    }


class RunRecorder:
    """Create one before run_pipeline() and call finish() after it."""

    def __init__(self, request, case_id=None):
        REPORTS_DIR.mkdir(exist_ok=True)
        self.request = request
        self.case_id = case_id
        self.started = datetime.now()
        self.began = time.perf_counter()
        self.usage_before = dict(USAGE)
        patient = re.search(r"patient(?:id)?[\s_-]*(\d+)", request, re.IGNORECASE)  # "PatientID_0003" or "patient 3"
        label = f"PatientID_{patient.group(1)}" if patient else "no-patient"
        self.name = f"{self.started:%Y%m%d-%H%M%S}_{case_id + '_' if case_id else ''}{label}"
        STAGES.clear()
        TOOL_CALLS.clear()

        root = logging.getLogger()
        if root.level == logging.NOTSET or root.level > logging.INFO:
            root.setLevel(logging.INFO)
        self.log_handler = logging.FileHandler(REPORTS_DIR / f"{self.name}.log", encoding="utf-8")
        self.log_handler.setFormatter(logging.Formatter("%(asctime)s | %(levelname)s | %(name)s | %(message)s"))
        root.addHandler(self.log_handler)
        logging.getLogger("pipeline").info("Run started: %s", request)

    def finish(self, state, session=None):
        """Save the report (if one was made), a run summary and the log. Returns the summary dict."""
        used = {key: USAGE[key] - self.usage_before[key] for key in USAGE}
        report = state["report"]
        report_file = None
        if report["status"] == "success":
            report_file = f"{self.name}.md"
            (REPORTS_DIR / report_file).write_text(report["content"], encoding="utf-8")

        summary = {
            "case_id": self.case_id,
            "request": self.request,
            "started": self.started.isoformat(timespec="seconds"),
            "seconds": round(time.perf_counter() - self.began, 1),
            "stages": list(STAGES),
            "revision_rounds": (state["verification"].get("revision_count") or 0),
            "errors": state["errors"],
            "tokens": {"model_calls": used["calls"], "prompt": used["prompt_tokens"],
                       "completion": used["completion_tokens"], "total": used["tokens"],
                       "estimated_cost_usd": round(used["cost"], 4)},
            "tool_calls": {
                "total": len(TOOL_CALLS), "succeeded": sum(c["ok"] for c in TOOL_CALLS),
                "by_tool": {name: sum(c["tool"] == name for c in TOOL_CALLS)
                            for name in sorted({c["tool"] for c in TOOL_CALLS})},
            },
            "outcome": _outcome(state),
            "report_file": report_file,
            "log_file": f"{self.name}.log",
        }
        (REPORTS_DIR / f"{self.name}.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")

        logging.getLogger("pipeline").info("Run finished in %.1fs, %s tokens", summary["seconds"], used["tokens"])
        logging.getLogger().removeHandler(self.log_handler)
        self.log_handler.close()

        print(f"\nSaved to {REPORTS_DIR}/{self.name}.*")
        print(f"  report: {report_file or 'none (the run did not produce one)'}")
        print(f"  time: {summary['seconds']}s | model calls: {used['calls']} | tokens: {used['tokens']} "
              f"({used['prompt_tokens']} prompt + {used['completion_tokens']} completion) "
              f"| est. cost: ${used['cost']:.4f}")
        calls = summary["tool_calls"]
        print(f"  tool calls: {calls['succeeded']}/{calls['total']} succeeded")
        return summary
