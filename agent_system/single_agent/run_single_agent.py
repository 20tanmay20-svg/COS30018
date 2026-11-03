import argparse
import json
import re
import sys
import time
from pathlib import Path

from dotenv import load_dotenv

# Add the repository root so this entry point works when run by file path.
AGENT_SYSTEM_DIR = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = AGENT_SYSTEM_DIR.parent
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from agent_system.single_agent.single_agent import SingleAgentPipeline
from agent_system.single_agent.tests.evaluate_runs import CASES, check_case, save_run
from agent_system.single_agent.tests.fault_injection import fault_for


def run_gbm_report(user_request, **options):
    """Run one patient request through the complete single-agent pipeline."""
    return SingleAgentPipeline().run(user_request, **options)


def print_pipeline_state(state):
    print(json.dumps(state, indent=2, ensure_ascii=False, default=str))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run the single-agent GBM decision-support pipeline.")
    parser.add_argument(
        "--report-output",
        type=Path,
        help="Optional path for the generated Markdown report.",
    )
    parser.add_argument(
        "--case-id",
        choices=[case[0] for case in CASES],
        help="Evaluation case ID; applies its fault injection and saves a scored run.",
    )
    args = parser.parse_args()
    load_dotenv(AGENT_SYSTEM_DIR / ".env")
    # Apply the default before running; an empty request is rejected by the pipeline.
    user_request = input("Describe the GBM report request: ").strip()
    tagged = re.match(r"\s*(CMP-\d{2})\s*[:\-]\s*(.*)", user_request, re.DOTALL)
    if tagged:
        if args.case_id and args.case_id != tagged.group(1).upper():
            parser.error("The typed case ID does not match --case-id.")
        case_id, user_request = tagged.group(1).upper(), tagged.group(2).strip()
    else:
        case_id = args.case_id
    if not user_request:
        user_request = "make me a report for patient 7"
    pipeline = SingleAgentPipeline()
    began = time.perf_counter()
    with fault_for(case_id, pipeline):
        state = pipeline.run(user_request)
    elapsed = time.perf_counter() - began
    report = state.get("report", {})
    if args.report_output and report.get("status") == "success":
        args.report_output.write_text(report["content"], encoding="utf-8")
    print_pipeline_state(state)
    if case_id:
        saved = save_run(user_request, state, elapsed, case_id)
        expected = next(case[2] for case in CASES if case[0] == case_id)
        passed, evidence = check_case(saved)
        print(f"\n{case_id}: {'PASS' if passed else 'FAIL'}\n  expected: {expected}\n  result: {evidence}")
