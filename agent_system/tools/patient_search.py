import json
from pathlib import Path


#locate the processed patient dataset
PROJECT_ROOT = Path(__file__).resolve().parents[1]

DATA_FILE = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "gbm_patient_profiles.json"
)


#load GBM patient records from the JSON dataset
def load_patients():
   
    #check if file exists
    if not DATA_FILE.exists():
        raise FileNotFoundError(
            f"Patient dataset not found: {DATA_FILE}"
        )
    
    #open file
    with open( DATA_FILE, "r", encoding="utf-8") as file:
        return json.load(file) #convert to python objects


#optional filters for searching patients 
def search_patients(
    age_min=None,
    age_max=None,
    sex=None,
    progression=None,
    death_recorded=None
):
    """
    Search GBM patients using optional criteria.

    Parameters:
        age_min (int | None):
            Minimum age at diagnosis.

        age_max (int | None):
            Maximum age at diagnosis.

        sex (str | None):
            Sex at birth.

        progression (int | None):
            0 = No progression
            1 = Progression recorded

        death_recorded (int | None):
            0 = No death recorded
            1 = Documented death

    Returns:
        dict:
            Structured search results.
    """

    #validate age range
    if age_min is not None and age_min < 0:
        return {
            "success": False,
            "message": "Minimum age cannot be negative."
        }

    if age_max is not None and age_max < 0:
        return {
            "success": False,
            "message": "Maximum age cannot be negative."
        }

    if (
        age_min is not None
        and age_max is not None
        and age_min > age_max
    ):
        return {
            "success": False,
            "message": (
                "Minimum age cannot be greater "
                "than maximum age."
            )
        }

    #validate progression
    if progression not in (None, 0, 1):
        return {
            "success": False,
            "message": (
                "Progression must be 0, 1, or None."
            )
        }

    #validate death status
    if death_recorded not in (None, 0, 1):
        return {
            "success": False,
            "message": (
                "Death status must be 0, 1, or None."
            )
        }

    patients = load_patients()
    results = []

    for patient in patients:

        #convert age from string to integer
        age_value = patient.get(
            "Age at diagnosis"
        )

        try:
            age = (
                int(age_value)
                if age_value is not None
                else None
            )
        except (ValueError, TypeError):
            age = None

        #apply minimum age filter
        if age_min is not None:
            if age is None or age < age_min:
                continue

        #apply maximum age filter
        if age_max is not None:
            if age is None or age > age_max:
                continue

        #apply sex filter
        if sex is not None:
            patient_sex = patient.get(
                "Sex at Birth"
            )

            if not patient_sex:
                continue

            if patient_sex.lower() != sex.lower():
                continue

        #apply progression filter
        if progression is not None:
            patient_progression = patient.get(
                "Progression"
            )

            if patient_progression != str(progression):
                continue

        #apply death status filter
        if death_recorded is not None:
            patient_death = patient.get(
                "Overall Survival (Death)"
            )

            if patient_death != str(death_recorded):
                continue

        #add current patient to results list
        results.append(patient)


    #return dictionary with search findings
    return {
        "success": True,
        "count": len(results),
        "patients": results
    }


def get_patient_by_id(patient_id):
    """
    Retrieve a patient using their Patient ID.

    Parameters:
        patient_id (str):
            Unique patient identifier.

    Returns:
        dict:
            Patient information or an error message.
    """

    if not patient_id or not patient_id.strip():
        return {
            "success": False,
            "message": "Patient ID is required."
        }

    patients = load_patients()

    for patient in patients:
        if patient.get("Patient_ID") == patient_id.strip():
            return {
                "success": True,
                "patient": patient
            }

    return {
        "success": False,
        "message": (
            f"Patient {patient_id} was not found."
        )
    }


if __name__ == "__main__":

    #test 01: search patients
    search_result = search_patients(
        age_min=50,
        age_max=60,
        progression=1
    )

    print(
        f"Search successful: "
        f"{search_result['success']}"
    )

    print(
        f"Found {search_result['count']} patients."
    )

    #test 2: retrieve a specific patient
    patient_result = get_patient_by_id(
        "PatientID_0003"
    )

    print("\nPatient lookup result:")
    print(patient_result)