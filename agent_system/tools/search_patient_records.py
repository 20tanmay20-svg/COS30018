"""Patient information agent tool: search_patient_records."""

import logging

from smolagents import tool

from .patient_search import search_patients
from .tool_schemas import BinaryPatientStatus, PatientSex, ToolResult

logger = logging.getLogger(__name__)


@tool
def search_patient_records(
    age_min: int | None = None,
    age_max: int | None = None,
    sex: PatientSex | None = None,
    progression: BinaryPatientStatus | None = None,
    death_recorded: BinaryPatientStatus | None = None,
) -> ToolResult:
    """
    Search patient records using demographic and clinical filters.

    Use this tool when the user asks about a group of patients,
    comparisons between groups, or patients matching specific
    demographic or clinical criteria.

    Result: Success returns success, count, and patients. Failure returns success=false and message.

    Args:
        age_min: Minimum patient age.
        age_max: Maximum patient age.
        sex: Patient sex at birth (choices: ["Female", "Male"]).
        progression: Progression status (choices: [0, 1]).
        death_recorded: Documented death status (choices: [0, 1]).

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
