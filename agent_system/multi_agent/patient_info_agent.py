import os
import sys
import json
import logging

from dotenv import load_dotenv
from smolagents import LiteLLMModel, ToolCallingAgent, tool


# ---------------------------------------------------------
#find root configuration

PROJECT_ROOT = os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))
)

sys.path.append(PROJECT_ROOT)


# ---------------------------------------------------------
#import existing patient search functions from patient_search.py

from tools.patient_search import (
    search_patients,
    get_patient_by_id
)

#import create initial shared state function from shared_state.py
from shared_state import create_initial_state


load_dotenv() #load enviornment variables


# configure logging messages

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)

logger = logging.getLogger(__name__)



# ---------------------------------------------------------
# Patient Search Tools

@tool
def search_patient_records(
    age_min: int = None,
    age_max: int = None,
    sex: str = None,
    progression: int = None,
    death_recorded: int = None
) -> dict:
    """
    Search patient records using demographic and clinical filters.

    Use this tool when the user asks about a group of patients,
    comparisons between groups, or patients matching specific
    demographic or clinical criteria.

    Args:
        age_min: Minimum patient age.
        age_max: Maximum patient age.
        sex: Patient sex at birth.
        progression: Progression status, 0 or 1.
        death_recorded: Documented death status, 0 or 1.

    Returns:
        Dictionary containing matching patient records.
    """

    #Record search operation in logs
    logger.info(
        "Tool action: search_patient_records "
        "(age_min=%s, age_max=%s, sex=%s, progression=%s, "
        "death_recorded=%s)",
        age_min,
        age_max,
        sex,
        progression,
        death_recorded
    )

    try:

        #pass values into search function
        result = search_patients(
            age_min=age_min,
            age_max=age_max,
            sex=sex,
            progression=progression,
            death_recorded=death_recorded
        )

        return result

    except Exception as e:

        logger.exception(
            "Patient search failed."
        )

        return {
            "success": False,
            "message": f"Patient search failed: {str(e)}"
        }


@tool

#agent tool for retrieving one patient
def retrieve_patient(
    patient_id: str
) -> dict:
    """
    -retrieve a patient record using their unique Patient ID.

    -use this tool when the user identifies a specific patient.

    Args:
        patient_id: Unique patient identifier.

    Returns:
        Dictionary containing the patient record or an error message.
    """

    #log patient id
    logger.info(
        "Tool action: retrieve_patient(patient_id=%s)",
        patient_id
    )

    #pass id to the function for patient record retrieval
    try: 
        result = get_patient_by_id(
            patient_id
        )

        return result

    #catch and log errors in retrieval 
    except Exception as e:

        logger.exception(
            "Patient retrieval failed."
        )

        return {
            "success": False,
            "message": f"Patient retrieval failed: {str(e)}"
        }



# ---------------------------------------------------------
#Gemini model configuration

#get api key from .env
api_key = os.getenv("GEMINI_API_KEY" )

if not api_key:
    raise ValueError(
        "GEMINI_API_KEY was not found. "
        "Make sure it is defined in your .env file."
    )

#confugure model
model = LiteLLMModel(
    model_id="gemini/gemini-3.6-flash",
    api_key=api_key
)



# ---------------------------------------------------------
#patient infomation agent 

agent = ToolCallingAgent(

    #provide functions(tools) to agent
    tools=[
        search_patient_records,
        retrieve_patient
    ],

    model=model,

    max_steps=5,

    #agent instructions
    instructions="""

You are the Patient Information Agent in a multi-agent
medical decision-support system.

Your responsibility is to interpret the user's request and
retrieve the relevant patient information from the provided
GBM patient dataset.

You do NOT make medical decisions and you do NOT generate
medical recommendations.

AVAILABLE TOOLS
---------------

1. retrieve_patient

Use this when the user asks about a specific patient and
provides a Patient ID.

Example:

"Make a report for PatientID_0004"

You should identify:

PatientID_0004

and call:

retrieve_patient("PatientID_0004")


2. search_patient_records

Use this when the user asks about multiple patients,
patient groups, filtering, or comparisons.

Examples:

"Find female patients"

"Find patients aged 50 to 60"

"Find patients with progression"

"Compare male and female patients"

Use the appropriate search filters.

For comparisons, perform separate searches when necessary.

For example, a male vs female comparison should retrieve
the male and female patient groups separately.


IMPORTANT RULES
---------------

1. NEVER invent patient information.

2. NEVER create or fabricate clinical notes.

3. NEVER modify the patient dataset.

4. Only use information returned by the provided patient
   search tools.

5. Do not make treatment recommendations or medical
   conclusions.

6. Do not generate the final medical report. That will be
   handled by downstream agents.

7. If a patient does not exist, clearly report that the
   patient was not found.

8. If a search fails, clearly report the failure.

9. If the user's request is ambiguous and patient data
   cannot be determined safely, report the ambiguity rather
   than inventing information.

10. For a group comparison, retrieve the relevant groups
    separately so the downstream agents can compare them.


OUTPUT FORMAT
-------------

After completing the required tool calls, return a
structured JSON object with the following fields:

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

If the request cannot be completed, use:

{
    "request_type": "...",
    "requested_task": "...",
    "patient_data": [],
    "data_source": "gbm_patient_profiles.json",
    "status": "failed",
    "error": "..."
}

The patient_data field must contain ONLY information
retrieved from the patient dataset.

"""
)


# ---------------------------------------------------------
# update shared state

def update_patient_state(
    state: dict,
    patient_result
) -> dict:
    """
    add the patient information agent's result
    to the shared state.

    -the agent may return JSON as a string, so this function
     converts it into a python dictionary before updating
     the shared state.
    """

    # -----------------------------------------------------
    #convert JSON string into python dictionary
    if isinstance(patient_result, str):

        #convert JSON string to python object
        try:

            patient_result = json.loads(
                patient_result
            )

        #handle invalid JSON
        except json.JSONDecodeError:

            state["patient_information"]["status"] = "failed"

            state["patient_information"]["error"] = (
                "Patient Information Agent returned "
                "an invalid JSON response."
            )

            #add error to shared error list
            state["errors"].append(
                "Invalid JSON returned by "
                "Patient Information Agent."
            )

            return state

    
    # ---------------------------------------------------------
    #check if result is a dictionary
    if not isinstance(patient_result, dict):

        #mark pation status as failed
        state["patient_information"]["status"] = "failed"

        #store error message with explanation
        state["patient_information"]["error"] = (
            "Patient Information Agent returned "
            "an invalid result type."
        )

        #add error to shared error list
        state["errors"].append(
            "Invalid result type returned by "
            "Patient Information Agent."
        )

        return state

    
    
    # ---------------------------------------------------------
    #verify that retrieval succeeded

    if patient_result.get("status") != "success":

        state["patient_information"]["status"] = "failed"

        state["patient_information"]["error"] = (
            patient_result.get(
                "error"
            )
            or patient_result.get(
                "message"
            )
            or "Patient information retrieval failed."
        )

        return state




    # ---------------------------------------------------------
    #store structured patient info

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
#  Main interface for testing

if __name__ == "__main__":

    print("---------------------------------------")
    print("Patient Information Agent")
    print("---------------------------------------")
    print("Type 'exit' to quit.\n")



    while True:

        user_input = input(
            "You: "
        ).strip()

        # -------------------------------------------------
        #exit
        if user_input.lower() == "exit":

            print("Exiting...")

            break

        # -------------------------------------------------
        #empty input
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

            # -------------------------------------------------
            #create shared state

            state = create_initial_state(
                user_input
            )

            # Record current agent
            state["current_agent"] = (
                "patient_information_agent"
            )

            # -------------------------------------------------
            #Run agent
            response = agent.run(
                user_input
            )

            print("\nAgent:")
            print(response)

            # -------------------------------------------------
            # update shared state

            state = update_patient_state(
                state,
                response
            )

            # -------------------------------------------------
            #display shared state
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
                "Patient Information Agent failed."
            )

            print(
                "\nAgent error:",
                str(e)
            )

            print(
                "The request was unsuccessful. "
                "Please try again.\n"
            )