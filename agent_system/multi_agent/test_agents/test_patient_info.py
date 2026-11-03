"""Patient Information Agent: 6 cases (PI-01 to PI-06)."""

import pytest

import patient_info_agent as agent
from shared_state import create_initial_state
from tools.patient_search import get_patient_by_id, load_patients
from conftest import check_case
from measure import run

# A patient with the most filled-in fields, for PI-02.
FULLEST = max(load_patients(), key=lambda p: sum(v not in (None, "") for v in p.values()))

CONFLICTING_RECORD = {"Patient_ID": "PatientID_9998", "Primary Diagnosis": "GBM",
                      "Age at diagnosis": "57", "Age at diagnosis (history)": "42"}


def returns_record(patient_id):
    def check(result):
        assert result["status"] == "success", f"Lookup failed: {result['error']}"
        assert result["patient_data"] == [get_patient_by_id(patient_id)["patient"]], "Record does not match the dataset"
    return check


def check_missing_fields(result):
    returns_record("PatientID_0004")(result)
    assert any(v in (None, "") for v in result["patient_data"][0].values()), "Fixture has no missing field"


def check_not_found(result):
    assert result["status"] == "failed", "Unknown patient was not rejected"
    assert result["patient_data"] == [], "A record was returned for an unknown patient"
    assert "not found" in result["error"].lower(), f"Unclear error: {result['error']}"


def check_conflict(result):
    assert result["status"] == "failed", "Conflicting history was silently accepted"
    assert "conflict" in str(result["error"]).lower(), f"Error does not mention the conflict: {result['error']}"


def check_irrelevant(result):
    assert result["status"] == "failed", "Irrelevant request was not rejected"
    assert result["patient_data"] == [] and result["error"], "Expected no data and an error message"


def use_conflicting_record(monkeypatch):
    monkeypatch.setattr(agent, "get_patient_by_id", lambda _id: {"success": True, "patient": CONFLICTING_RECORD})


CASES = [
    {"id": "PI-01", "name": "Retrieve a valid patient ID", "request": "Retrieve history for patient 3",
     "expect": "Returns the correct patient record and history.", "check": returns_record("PatientID_0003")},
    {"id": "PI-02", "name": "Patient with complete information", "request": f"Retrieve {FULLEST['Patient_ID']}",
     "expect": "Extracts the available patient details accurately.", "check": returns_record(FULLEST["Patient_ID"])},
    {"id": "PI-03", "name": "Patient with missing fields", "request": "Retrieve patient 4",
     "expect": "Reports available details and identifies missing information without guessing.",
     "check": check_missing_fields},
    {"id": "PI-04", "name": "Patient that does not exist", "request": "Retrieve patient 99999999",
     "expect": "Reports that no matching patient record was found.", "check": check_not_found},
    {"id": "PI-05", "name": "Conflicting patient history", "request": "Retrieve patient 9998",
     "expect": "Identifies the inconsistency instead of silently choosing a value.",
     "setup": use_conflicting_record, "check": check_conflict},
    {"id": "PI-06", "name": "Irrelevant request", "request": "What is the weather today?",
     "expect": "Handles invalid input safely and returns an error message.", "check": check_irrelevant},
]


@pytest.mark.parametrize("case", CASES, ids=[c["id"] for c in CASES])
def test_patient_info(case, monkeypatch, record):
    if "setup" in case:
        case["setup"](monkeypatch)
    state, metrics = run(lambda: agent.run_patient_info_agent(create_initial_state(case["request"])))
    result = state["patient_information"]
    passed, reason = check_case(case, result)
    record(case, passed, reason, metrics)
    assert passed, reason
