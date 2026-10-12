"""Patient information agent tool: retrieve_patient."""

import logging

from smolagents import tool

from .patient_search import get_patient_by_id

logger = logging.getLogger(__name__)


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
