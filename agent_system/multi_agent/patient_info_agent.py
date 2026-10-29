import os
import sys
import json
import logging
import re

from dotenv import load_dotenv
from smolagents import LiteLLMModel, ToolCallingAgent


# ---------------------------------------------------------
# Find root configuration

PROJECT_ROOT = os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))
)

sys.path.append(PROJECT_ROOT)


# ---------------------------------------------------------
# Import existing patient search functions

from tools.patient_search import get_patient_by_id
from tools.retrieve_patient import retrieve_patient
from tools.search_patient_records import search_patient_records

from shared_state import create_initial_state


load_dotenv()


# ---------------------------------------------------------
# Configure logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------
# Patient request parser

def parse_patient_request(user_request: str) -> dict | None:
    """
    Identify a specific patient from a natural-language request.

    Examples:
        "make a report for patient 3"
        "PatientID_0003"
        "show information for patient 12"

    Returns None if a specific patient cannot be identified.
    """

    # Match PatientID_0003
    match = re.search(
        r"\bPatientID[_\s-]*(\d+)\b",
        user_request,
        re.IGNORECASE
    )

    # Match "patient 3"
    if not match:
        match = re.search(
            r"\bpatient\s+(\d+)\b",
            user_request,
            re.IGNORECASE
        )

    if not match:
        return None

    patient_number = int(match.group(1))
    patient_id = f"PatientID_{patient_number:04d}"

    # Determine the requested task
    request_lower = user_request.lower()

    if "report" in request_lower:
        requested_task = "generate_report"
    elif any(
        word in request_lower
        for word in ["compare", "comparison"]
    ):
        requested_task = "compare_patients"
    else:
        requested_task = "retrieve_information"

    return {
        "request_type": "individual_patient",
        "requested_task": requested_task,
        "patient_id": patient_id
    }



# ---------------------------------------------------------
# Local model configuration (Ollama)

local_model = os.getenv("LOCAL_MODEL")
gemini_key = os.getenv("GEMINI_API_KEY")
gemini_model = os.getenv("GEMINI_MODEL", "gemini/gemini-flash-latest")

if local_model:
    model = LiteLLMModel(
        model_id=local_model,
        api_base=os.getenv("LOCAL_API_BASE", "http://localhost:11434"),
    )
elif gemini_key:
    model = LiteLLMModel(
        model_id=gemini_model,
        api_key=gemini_key,
    )
else:
    raise ValueError(
        "Neither LOCAL_MODEL nor GEMINI_API_KEY is set. Add GEMINI_API_KEY to your .env file."
    )


# ---------------------------------------------------------
# Patient Information Agent

agent = ToolCallingAgent(
    tools=[
        search_patient_records,
        retrieve_patient
    ],

    model=model,

    max_steps=5,

    instructions="""
You are the Patient Information Agent in a multi-agent
medical decision-support system.

Your responsibility is to retrieve relevant patient information
from the GBM patient dataset.

You do NOT make medical decisions, recommendations, or final reports.

Use retrieve_patient when the user asks about a specific patient.

Use search_patient_records when the user asks about multiple patients,
patient groups, filtering, or comparisons.

NEVER invent patient information.

Only use information returned by the provided patient search tools.

Do not generate the final medical report. Downstream agents handle this.

If a patient does not exist, report that the patient was not found.

Return structured JSON:

{
    "request_type": "...",
    "requested_task": "...",
    "patient_data": [...],
    "data_source": "gbm_patient_profiles.json",
    "status": "success"
}

Possible request_type values:
- individual_patient
- patient_group
- patient_comparison

Possible requested_task values:
- retrieve_information
- generate_report
- compare_patients
- analyse_group

If unsuccessful:

{
    "request_type": "...",
    "requested_task": "...",
    "patient_data": [],
    "data_source": "gbm_patient_profiles.json",
    "status": "failed",
    "error": "..."
}
"""
)


# ---------------------------------------------------------
# Flatten patient data

def _flatten_patient_data(items) -> list:
    """
    Turn patient_data into a flat list of patient dictionaries.
    """

    flat = []

    def walk(x):
        if isinstance(x, list):
            for item in x:
                walk(item)

        elif isinstance(x, dict):

            if isinstance(x.get("patients"), list):
                walk(x["patients"])

            elif isinstance(x.get("patient"), dict):
                flat.append(x["patient"])

            else:
                flat.append(x)

    walk(items)

    # Remove duplicate patients
    seen = set()
    unique = []

    for record in flat:
        pid = record.get("Patient_ID")

        if pid is not None:
            if pid in seen:
                continue

            seen.add(pid)

        unique.append(record)

    return unique


# ---------------------------------------------------------
# Run Patient Information Agent

def run_patient_info_agent(state: dict) -> dict:
    """
    Run the Patient Information stage.

    Specific patient requests are handled directly using the parser
    and database function.

    More complex/group requests are handled by the LLM agent.
    """

    state["current_agent"] = "patient_information_agent"

    user_request = state["user_request"]

    try:

        # -------------------------------------------------
        # Specific patient request
        # -------------------------------------------------

        parsed_request = parse_patient_request(user_request)

        if parsed_request:

            logger.info(
                "Specific patient detected: %s",
                parsed_request["patient_id"]
            )

            result = get_patient_by_id(
                parsed_request["patient_id"]
            )

            if not result.get("success"):
                return update_patient_state(
                    state,
                    {
                        "request_type": "individual_patient",
                        "requested_task": parsed_request["requested_task"],
                        "patient_data": [],
                        "data_source": "gbm_patient_profiles.json",
                        "status": "failed",
                        "error": result.get(
                            "message",
                            "Patient not found."
                        )
                    }
                )

            return update_patient_state(
                state,
                {
                    "request_type": parsed_request["request_type"],
                    "requested_task": parsed_request["requested_task"],
                    "patient_data": [
                        result["patient"]
                    ],
                    "data_source": "gbm_patient_profiles.json",
                    "status": "success",
                    "error": None
                }
            )

        # -------------------------------------------------
        # Group / comparison request
        # Use LLM agent
        # -------------------------------------------------

        response = agent.run(user_request)

        if isinstance(response, str):

            response = response.strip()

            if response.startswith("```"):
                response = (
                    response
                    .strip("`")
                    .removeprefix("json")
                    .strip()
                )

            try:
                response = json.loads(response)

            except json.JSONDecodeError:
                pass

        if isinstance(response, dict) and "patient_data" in response:

            response["patient_data"] = _flatten_patient_data(
                response["patient_data"]
            )

        return update_patient_state(
            state,
            response
        )

    except Exception as e:

        logger.exception(
            "Patient Information stage failed."
        )

        message = (
            f"Patient Information stage failed: {str(e)}"
        )

        state["patient_information"]["status"] = "failed"
        state["patient_information"]["error"] = message
        state["errors"].append(message)

        return state


# ---------------------------------------------------------
# Update shared state

def update_patient_state(
    state: dict,
    patient_result
) -> dict:
    """
    Store the Patient Information result
    in the shared state.
    """

    # Convert JSON string to dictionary
    if isinstance(patient_result, str):

        try:
            patient_result = json.loads(
                patient_result
            )

        except json.JSONDecodeError:

            state["patient_information"]["status"] = "failed"

            state["patient_information"]["error"] = (
                "Patient Information Agent returned "
                "an invalid JSON response."
            )

            state["errors"].append(
                "Invalid JSON returned by "
                "Patient Information Agent."
            )

            return state

    # Check result type
    if not isinstance(patient_result, dict):

        state["patient_information"]["status"] = "failed"

        state["patient_information"]["error"] = (
            "Patient Information Agent returned "
            "an invalid result type."
        )

        state["errors"].append(
            "Invalid result type returned by "
            "Patient Information Agent."
        )

        return state

    # Check retrieval status
    if patient_result.get("status") != "success":

        state["patient_information"]["status"] = "failed"

        state["patient_information"]["error"] = (
            patient_result.get("error")
            or patient_result.get("message")
            or "Patient information retrieval failed."
        )

        return state

    # Store structured patient information
    state["patient_information"] = {

        "request_type": patient_result.get(
            "request_type"
        ),

        "requested_task": patient_result.get(
            "requested_task"
        ),

        "patient_data": patient_result.get(
            "patient_data",
            []
        ),

        "data_source": patient_result.get(
            "data_source"
        ),

        "status": "success",

        "error": None
    }

    return state


# ---------------------------------------------------------
# Main interface for testing

if __name__ == "__main__":

    print("---------------------------------------")
    print("Patient Information")
    print("---------------------------------------")
    print("Type 'exit' to quit.\n")

    while True:

        user_input = input(
            "User Input: "
        ).strip()

        if user_input.lower() == "exit":
            print("Exiting...")
            break

        if not user_input:
            print(
                "Please enter a request.\n"
            )
            continue

        logger.info(
            "New user request: %s",
            user_input
        )

        try:

            # Create shared state
            state = create_initial_state(
                user_input
            )

            # Run Patient Information stage
            state = run_patient_info_agent(
                state
            )

            # Display shared state
            print("\nShared State:")

            print(
                json.dumps(
                    state,
                    indent=2,
                    default=str
                )
            )

            print()

        except Exception as e:

            logger.exception(
                "Patient Information stage failed."
            )

            print(
                "\nAgent error:",
                str(e)
            )

            print(
                "The request was unsuccessful. "
                "Please try again.\n"
            )
