import pandas as pd
import json
from pathlib import Path

#import file paths 
INPUT_FILE = Path("../data/raw/MU-Glioma-Post_ClinicalData-July2025.xlsx")
OUTPUT_FILE = Path("../data/processed/gbm_patient_profiles.json")

#read the patient data sheet
df = pd.read_excel(
    INPUT_FILE,
    sheet_name="MU Glioma Post",
    na_filter=False
)

#strip extra spaces from column names
df.columns = df.columns.astype(str).str.strip()

#extract fields
selected_fields = [
    "Patient_ID",
    "Sex at Birth",
    "Age at diagnosis",
    "Primary Diagnosis",
    "Grade of Primary Brain Tumor",
    "Progression",
    "Time to First Progression (Days)",
    "Overall Survival (Death)"
]

""" fields for historical data
optional_fields = [
    "Initial Chemo Therapy",
    "Name of Initial Chemo Therapy",
    "Radiation Therapy",
    "Dose",
    "Number of Fractions"
]
"""


#check required fields
missing_fields = [
    field for field in selected_fields
    if field not in df.columns
]

if missing_fields:
    raise ValueError(
        f"Missing columns: {missing_fields}"
    )

#filter for Glioblastoma (GBM) patients
gbm_df = df[
    df["Primary Diagnosis"]
    .astype(str)
    .str.contains("GBM", case=False, na=False)
].copy()

#select fields
gbm_df = gbm_df[selected_fields]



#convert missing values 
def clean_value(value):
    if pd.isna(value):
        return None

    value = str(value).strip()

    if value == "":
        return None

    return value

profiles = [
    {
        key: clean_value(value)
        for key, value in patient.items()
    }
    for patient in gbm_df.to_dict(orient="records")
]

#save output as JSON
OUTPUT_FILE.parent.mkdir(
    parents=True,
    exist_ok=True
)

with open(OUTPUT_FILE, "w", encoding="utf-8") as file:
    json.dump(
        profiles,
        file,
        indent=2,
        ensure_ascii=False
    )

#verify
print(f"Extracted {len(profiles)} GBM patient profiles.")
print(f"Saved to: {OUTPUT_FILE}")

