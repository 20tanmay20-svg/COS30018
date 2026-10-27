import argparse
import json
import sys
from pathlib import Path

from dotenv import load_dotenv

# Make single_agent importable whether run from the project root or agent_system.
AGENT_DIR = Path(__file__).resolve().parent
if str(AGENT_DIR) not in sys.path:
    sys.path.insert(0, str(AGENT_DIR))

from single_agent import SingleAgentPipeline


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
    args = parser.parse_args()
    load_dotenv(AGENT_DIR / ".env")
    # Apply the default before running; an empty request is rejected by the pipeline.
    user_request = input("Describe the GBM report request: ").strip()
    if not user_request:
        user_request = "make me a report for patient 7"
    state = run_gbm_report(user_request)
    report = state.get("report", {})
    if args.report_output and report.get("status") == "success":
        args.report_output.write_text(report["content"], encoding="utf-8")
    print_pipeline_state(state)
