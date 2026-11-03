"""Pytest setup: make the agents importable and provide the `record` fixture."""

import sys
from pathlib import Path

import pytest
from dotenv import load_dotenv

HERE = Path(__file__).resolve().parent
MULTI_AGENT = HERE.parent
AGENT_SYSTEM = MULTI_AGENT.parent
REPO = AGENT_SYSTEM.parent
for path in (AGENT_SYSTEM, MULTI_AGENT):
    sys.path.insert(0, str(path))
load_dotenv(REPO / ".env")
load_dotenv(REPO / "backend" / ".env")

from measure import ROWS, write_report  # noqa: E402  (needs the paths above)


def check_case(case, result):
    """Run the case's check on the result. Returns (passed, reason)."""
    try:
        case["check"](result)
        return True, ""
    except Exception as error:  # a failed assert, or a missing key because a stage failed
        return False, str(error) or repr(error)


@pytest.fixture
def record(request):
    """Call record(case, passed, reason, metrics) once per test to save a report row."""
    saved = []

    def add(case, passed, reason, metrics):
        saved.append(True)
        ROWS.append({"id": case["id"], "name": case["name"], "passed": passed, "reason": reason, **metrics})

    yield add
    if not saved:  # the test crashed before recording, so count it as a failure
        ROWS.append({"id": request.node.callspec.id, "name": "", "passed": False, "reason": "crashed",
                     "seconds": 0, "tokens": 0, "cost": 0})


def pytest_sessionfinish(session, exitstatus):
    write_report()

