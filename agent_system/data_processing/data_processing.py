import pandas as pd
import json
from pathlib import Path
import random
from collections import Counter

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
    "Overall Survival (Death)",
    "Initial Chemo Therapy",
    "Name of Initial Chemo Therapy",
    "Radiation Therapy",
    "Dose",
    "Number of Fractions"
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

# ----------------------------------------------------------------------
print("\nRunning validation checks...")
 
errors = []
 
with open(OUTPUT_FILE, encoding="utf-8") as file:
    saved = json.load(file)
 
#1. duplicate patient IDs
ids = [p["Patient_ID"] for p in saved]
duplicate_ids = [i for i, n in Counter(ids).items() if n > 1]
if duplicate_ids:
    errors.append(f"Duplicate Patient_IDs: {duplicate_ids}")
 
#2. consistent category labels
#prints the distinct values for review, and flags labels that differ only by case
category_fields = [
    "Sex at Birth",
    "Grade of Primary Brain Tumor",
    "Progression",
    "Overall Survival (Death)",
    "Initial Chemo Therapy",
    "Radiation Therapy",
]
 
for field in category_fields:
    counts = Counter(p[field] for p in saved)
    print(f"  {field}: {dict(counts)}")
 
    seen = {}
    for label in counts:
        if label is None:
            continue
        key = label.lower()
        if key in seen:
            errors.append(f"Inconsistent labels in '{field}': {seen[key]!r} and {label!r}")
        seen[key] = label
 
#3. realistic age values
for p in saved:
    try:
        age = float(p["Age at diagnosis"])
    except (TypeError, ValueError):
        errors.append(f"Age missing or not numeric for {p['Patient_ID']}: {p['Age at diagnosis']!r}")
        continue
    if not 0 < age < 120:
        errors.append(f"Unrealistic age for {p['Patient_ID']}: {age}")
 
#report
if errors:
    for e in errors:
        print(f"  ERROR: {e}")
    raise ValueError(f"Validation failed with {len(errors)} error(s). See output above.")
 
print("All validation checks passed.")

