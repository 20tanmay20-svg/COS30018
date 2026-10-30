import logging
import queue
import threading
from typing import Any

# Importing the multi-agent service sets up sys.path and .env loading for agent_system
from app.services.multi_agent_service import _populate_final_report_summary

logger = logging.getLogger(__name__)

_import_error: str | None = None

try:
    from single_agent import SingleAgentPipeline
    # Same model (and cloud-to-local fallback) the multi-agent pipeline builds from the root .env
    from agent_system.multi_agent.clinical_decision_support_agent import _build_model
except Exception as e:
    logger.warning("Could not import single_agent.SingleAgentPipeline: %s", e)
    _import_error = str(e)
    SingleAgentPipeline = None


# Progress events emitted around each single-agent phase, mirroring the multi-agent stage indices
_PHASE_EVENTS = {
    "patient": (
        "patient_information", 1, 15, 25,
        "Single Agent: Locating and indexing patient record...",
        "Single Agent: Record retrieved successfully.",
    ),
    "evidence": (
        "medical_evidence", 2, 35, 50,
        "Single Agent: Searching PubMed & assessing literature...",
        "Single Agent: Literature retrieved and assessed.",
    ),
    "cds": (
        "clinical_decision_support", 3, 55, 75,
        "Single Agent: Formulating considerations & treatment pathways...",
        "Single Agent: Decision pathways synthesized.",
    ),
    "verification": (
        "verification", 4, 80, 90,
        "Single Agent: Cross-referencing claims against cited abstracts...",
        "Single Agent: Verification checks complete.",
    ),
    "report": (
        "report_generation", 5, 95, 98,
        "Single Agent: Compiling verified structured dossier...",
        "Single Agent: Report assembled.",
    ),
}


def _progress(phase: str, done: bool, suffix: str = "") -> dict[str, Any]:
    stage, index, start_pct, done_pct, start_msg, done_msg = _PHASE_EVENTS[phase]
    return {
        "type": "progress",
        "stage": stage,
        "stage_index": index,
        "percent": done_pct if done else start_pct,
        "message": (done_msg if done else start_msg) + suffix,
    }


def _make_streaming_pipeline(emit):
    """Subclass the pipeline so each phase reports progress without modifying the agent itself."""

    class StreamingSingleAgentPipeline(SingleAgentPipeline):
        _cds_runs = 0

        def _run_patient_phase(self, *args, **kwargs):
            print("\n--- Running single-agent patient phase ---", flush=True)
            emit(_progress("patient", False))
            ok = super()._run_patient_phase(*args, **kwargs)
            if ok:
                emit(_progress("patient", True))
            return ok

        def _run_evidence_phase(self, *args, **kwargs):
            print("\n--- Running single-agent evidence phase ---", flush=True)
            emit(_progress("evidence", False))
            ok = super()._run_evidence_phase(*args, **kwargs)
            if ok:
                emit(_progress("evidence", True))
            return ok

        def _run_cds_phase(self, *args, **kwargs):
            self._cds_runs += 1
            suffix = f" (revision {self._cds_runs - 1})" if self._cds_runs > 1 else ""
            print(f"\n--- Running single-agent CDS phase{suffix} ---", flush=True)
            emit(_progress("cds", False, suffix))
            ok = super()._run_cds_phase(*args, **kwargs)
            if ok:
                emit(_progress("cds", True, suffix))
            return ok

        def _run_verification_phase(self, *args, **kwargs):
            print("\n--- Running single-agent verification phase ---", flush=True)
            emit(_progress("verification", False))
            approved = super()._run_verification_phase(*args, **kwargs)
            if approved:
                emit(_progress("verification", True))
            else:
                emit(_progress("verification", True, " Revision required; regenerating decision support..."))
            return approved

        def _run_report_phase(self, *args, **kwargs):
            print("\n--- Running single-agent report phase ---", flush=True)
            emit(_progress("report", False))
            result = super()._run_report_phase(*args, **kwargs)
            emit(_progress("report", True))
            return result

    return StreamingSingleAgentPipeline


def _failure_message(state: dict[str, Any]) -> str:
    """Picks the most specific failure detail recorded in the single-agent state."""
    errors = state.get("errors") or []
    if errors:
        return str(errors[-1])
    for key in ("patient_information", "medical_evidence", "clinical_decision_support", "verification", "report"):
        section = state.get(key) or {}
        if section.get("status") == "failed" and section.get("error"):
            return str(section["error"])
    return "Single-agent pipeline stopped before producing a report."


def execute_single_agent_pipeline_stream(user_request: str):
    """
    Streams single-agent pipeline progress phase by phase, using the same event format as the
    multi-agent stream so the frontend can consume either. The pipeline runs in a worker thread
    and phase hooks push events onto a queue that this generator drains.
    """
    if SingleAgentPipeline is None:
        err_msg = _import_error or "Single-agent module not available. Verify that smolagents[litellm] is installed and GEMINI_API_KEY is configured in .env."
        logger.error("Cannot run single-agent pipeline: %s", err_msg)
        yield {
            "type": "error",
            "message": f"Single-agent pipeline initialization failed: {err_msg}",
        }
        return

    events: queue.Queue = queue.Queue()
    done = object()
    result: dict[str, Any] = {}

    def worker():
        try:
            pipeline_cls = _make_streaming_pipeline(events.put)
            result["state"] = pipeline_cls(model=_build_model()).run(user_request)
        except Exception as exc:
            logger.exception("Error in single-agent pipeline: %s", exc)
            result["error"] = str(exc)
        finally:
            events.put(done)

    threading.Thread(target=worker, daemon=True).start()

    while True:
        event = events.get()
        if event is done:
            break
        yield event

    if "error" in result:
        yield {
            "type": "error",
            "message": f"Single-agent pipeline execution failed: {result['error']}",
        }
        return

    state = result.get("state") or {}
    if (state.get("report") or {}).get("status") != "success":
        err_detail = _failure_message(state)
        logger.error("Single-agent pipeline failed: %s", err_detail)
        yield {
            "type": "error",
            "message": f"Single-agent pipeline failed: {err_detail}",
        }
        return

    print(f"--- Finished single-agent pipeline: {state['report']['status']} ---", flush=True)
    state = _populate_final_report_summary(state)

    yield {
        "type": "complete",
        "percent": 100,
        "stage_index": 5,
        "message": "Single-Agent Pipeline Complete: Dossier Assembled & Verified",
        "state": state,
    }
