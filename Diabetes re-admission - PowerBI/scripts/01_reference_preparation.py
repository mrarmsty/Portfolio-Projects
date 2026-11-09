"""
01_reference_preparation.py
---------------------------------------------------------------------------
Reference (validation) implementation of the data preparation that Power Query
performs inside the Power BI project.

Why this script exists
* Power Query in the .pbip is the primary transformation layer.
* This script applies the SAME rules in pandas so that (a) the cleaned
  datasets can be shipped as standalone CSV deliverables and (b) the totals
  shown in Power BI can be reconciled against an independent implementation.
* It also produces the encounter-level feature table used by the
  predictive model (02_readmission_model.py).

Input : data/raw/diabetic_data.xlsx (sheets: diabetic_data, IDS_mapping)
Output: data/processed/*.csv
Run   : python scripts/01_reference_preparation.py   (from the repo root)
---------------------------------------------------------------------------
"""
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "diabetic_data.xlsx"
OUT = ROOT / "data" / "processed"
OUT.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------- constants
MED_COLS = ["metformin", "repaglinide", "nateglinide", "chlorpropamide",
            "glimepiride", "acetohexamide", "glipizide", "glyburide",
            "tolbutamide", "pioglitazone", "rosiglitazone", "acarbose",
            "miglitol", "troglitazone", "tolazamide", "examide",
            "citoglipton", "insulin", "glyburide-metformin",
            "glipizide-metformin", "glimepiride-pioglitazone",
            "metformin-rosiglitazone", "metformin-pioglitazone"]
CONSTANT_MEDS = ["examide", "citoglipton"]          # only value is "No"
NOT_ELIGIBLE_DISCHARGE = [11, 13, 14, 19, 20, 21]   # expired or hospice

ADMISSION_TYPE_GROUP = {1: "Emergency", 2: "Urgent", 3: "Elective",
                        4: "Newborn", 7: "Trauma Center",
                        5: "Not recorded", 6: "Not recorded", 8: "Not recorded"}

DISCHARGE_GROUP = {
    1: "Home",
    6: "Home with health service", 8: "Home with health service",
    3: "Skilled nursing / care facility", 4: "Skilled nursing / care facility",
    24: "Skilled nursing / care facility",
    2: "Transfer to another hospital", 9: "Transfer to another hospital",
    10: "Transfer to another hospital", 23: "Transfer to another hospital",
    27: "Transfer to another hospital", 29: "Transfer to another hospital",
    5: "Rehab / other inpatient care", 15: "Rehab / other inpatient care",
    22: "Rehab / other inpatient care", 28: "Rehab / other inpatient care",
    30: "Rehab / other inpatient care",
    7: "Left against medical advice",
    12: "Outpatient follow-up", 16: "Outpatient follow-up", 17: "Outpatient follow-up",
    11: "Expired / hospice", 13: "Expired / hospice", 14: "Expired / hospice",
    19: "Expired / hospice", 20: "Expired / hospice", 21: "Expired / hospice",
    18: "Not recorded", 25: "Not recorded", 26: "Not recorded",
}

ADMISSION_SOURCE_GROUP = {
    7: "Emergency room",
    1: "Referral", 2: "Referral", 3: "Referral",
    4: "Transfer from facility", 5: "Transfer from facility",
    6: "Transfer from facility", 10: "Transfer from facility",
    18: "Transfer from facility", 22: "Transfer from facility",
    25: "Transfer from facility", 26: "Transfer from facility",
    9: "Not recorded", 15: "Not recorded", 17: "Not recorded",
    20: "Not recorded", 21: "Not recorded",
    8: "Other", 11: "Other", 12: "Other", 13: "Other", 14: "Other",
    19: "Other", 23: "Other", 24: "Other",
}

AGE_ORDER = ["0-10", "10-20", "20-30", "30-40", "40-50", "50-60",
             "60-70", "70-80", "80-90", "90-100"]


# ---------------------------------------------------------------- helpers
def icd9_group(code) -> str:
    """Group an ICD-9 code into a clinical chapter (Strack et al., 2014)."""
    if code is None or (isinstance(code, float) and np.isnan(code)):
        return "Not recorded"
    s = str(code).strip()
    if s in ("", "?"):
        return "Not recorded"
    if s[0] in ("V", "E"):
        return "Other"
    try:
        v = float(s)
    except ValueError:
        return "Other"
    if 250 <= v < 251:
        return "Diabetes"
    if 390 <= v <= 459 or int(v) == 785:
        return "Circulatory"
    if 460 <= v <= 519 or int(v) == 786:
        return "Respiratory"
    if 520 <= v <= 579 or int(v) == 787:
        return "Digestive"
    if 800 <= v <= 999:
        return "Injury"
    if 710 <= v <= 739:
        return "Musculoskeletal"
    if 580 <= v <= 629 or int(v) == 788:
        return "Genitourinary"
    if 140 <= v <= 239:
        return "Neoplasms"
    return "Other"


def band(value, edges, labels):
    for upper, label in zip(edges, labels):
        if value <= upper:
            return label
    return labels[-1]


def specialty_group(s: str) -> str:
    if s == "?":
        return "Not recorded"
    if s.startswith("Surgery"):
        return "Surgery"
    if s in ("InternalMedicine", "Emergency/Trauma", "Family/GeneralPractice",
             "Cardiology", "Nephrology", "Orthopedics",
             "Orthopedics-Reconstructive", "Radiologist", "Pulmonology",
             "Psychiatry"):
        return {"InternalMedicine": "Internal Medicine",
                "Emergency/Trauma": "Emergency / Trauma",
                "Family/GeneralPractice": "Family / General Practice",
                "Orthopedics-Reconstructive": "Orthopedics"}.get(s, s)
    return "Other specialty"


# ---------------------------------------------------------------- load
def load_mapping() -> dict:
    """IDS_mapping holds three lookup tables stacked vertically."""
    m = pd.read_excel(RAW, sheet_name="IDS_mapping", header=None,
                      names=["id", "description"], dtype=str)
    out, current = {}, None
    for _, r in m.iterrows():
        if pd.isna(r.id):
            continue
        if str(r.id).endswith("_id"):
            current = r.id
            out[current] = {}
            continue
        desc = r.description if isinstance(r.description, str) else "Not recorded (no description)"
        out[current][int(r.id)] = desc.strip().rstrip(".").strip()
    return out


def main():
    raw = pd.read_excel(RAW, sheet_name="diabetic_data",
                        keep_default_na=False, na_values=[])
    mapping = load_mapping()
    n_raw = len(raw)
    df = raw.copy()

    # 1. Standardise missing-value markers ----------------------------------
    df = df.replace("?", np.nan)
    # Lab tests: blank in the extract means "test not performed" ("None" in UCI)
    for c in ["max_glu_serum", "A1Cresult"]:
        df[c] = df[c].replace({"": np.nan, "None": np.nan}).fillna("Not measured")
    df["A1Cresult"] = df["A1Cresult"].replace({"Norm": "Normal"})
    df["max_glu_serum"] = df["max_glu_serum"].replace({"Norm": "Normal"})

    # 2. Categorical cleaning -----------------------------------------------
    df["race"] = df["race"].fillna("Not recorded").replace(
        {"AfricanAmerican": "African American"})
    df["gender"] = df["gender"].replace({"Unknown/Invalid": "Unknown"})
    df["age_band"] = df["age"].str.strip("[)").str.replace("-", "-")
    df["payer_code"] = df["payer_code"].fillna("Not recorded")
    df["medical_specialty"] = df["medical_specialty"].fillna("?")
    df["specialty_group"] = df["medical_specialty"].map(specialty_group)
    df["medical_specialty"] = df["medical_specialty"].replace({"?": "Not recorded"})

    # 3. Diagnoses -----------------------------------------------------------
    for i in (1, 2, 3):
        df[f"diag_{i}"] = df[f"diag_{i}"].apply(
            lambda x: np.nan if pd.isna(x) or str(x).strip() in ("", "?") else str(x).strip())
        df[f"diag_{i}_group"] = df[f"diag_{i}"].apply(icd9_group)
    df["any_diabetes_diag"] = df[["diag_1_group", "diag_2_group", "diag_3_group"]] \
        .eq("Diabetes").any(axis=1).astype(int)

    # 4. Target and eligibility ---------------------------------------------
    df["readmit_30"] = (df["readmitted"] == "<30").astype(int)
    df["readmit_any"] = (df["readmitted"] != "NO").astype(int)
    df["readmission_status"] = df["readmitted"].map(
        {"<30": "Within 30 days", ">30": "After 30 days", "NO": "Not readmitted"})
    df["eligible_for_readmission"] = (~df["discharge_disposition_id"]
                                      .isin(NOT_ELIGIBLE_DISCHARGE)).astype(int)

    # 5. Utilisation features ------------------------------------------------
    df["prior_visits_total"] = df[["number_outpatient", "number_emergency",
                                   "number_inpatient"]].sum(axis=1)
    df["prior_inpatient_band"] = df["number_inpatient"].apply(
        lambda v: band(v, [0, 1, 2, 4], ["0", "1", "2", "3-4", "5+"]))
    df["prior_emergency_band"] = df["number_emergency"].apply(
        lambda v: band(v, [0, 1], ["0", "1", "2+"]))
    df["prior_outpatient_band"] = df["number_outpatient"].apply(
        lambda v: band(v, [0, 1], ["0", "1", "2+"]))
    df["prior_visits_band"] = df["prior_visits_total"].apply(
        lambda v: band(v, [0, 1, 2, 4], ["0", "1", "2", "3-4", "5+"]))
    df["los_band"] = df["time_in_hospital"].apply(
        lambda v: band(v, [2, 4, 7], ["1-2 days", "3-4 days", "5-7 days", "8-14 days"]))
    df["medications_band"] = df["num_medications"].apply(
        lambda v: band(v, [10, 15, 20, 30], ["1-10", "11-15", "16-20", "21-30", "31+"]))
    df["lab_procedures_band"] = df["num_lab_procedures"].apply(
        lambda v: band(v, [30, 45, 60], ["1-30", "31-45", "46-60", "61+"]))
    df["diagnoses_band"] = df["number_diagnoses"].apply(
        lambda v: band(v, [4, 6, 8], ["1-4", "5-6", "7-8", "9+"]))

    active_meds = [c for c in MED_COLS if c not in CONSTANT_MEDS]
    df["diabetes_meds_count"] = (df[active_meds] != "No").sum(axis=1)
    df["med_dose_changes"] = df[active_meds].isin(["Up", "Down"]).sum(axis=1)
    df["on_insulin"] = (df["insulin"] != "No").astype(int)
    df["on_metformin"] = (df["metformin"] != "No").astype(int)
    df["med_change_flag"] = (df["change"] == "Ch").astype(int)
    df["diabetes_med_flag"] = (df["diabetesMed"] == "Yes").astype(int)

    # 6. Encounter sequence per patient (encounter_id order as proxy) -------
    df = df.sort_values(["patient_nbr", "encounter_id"])
    df["patient_encounter_seq"] = df.groupby("patient_nbr").cumcount() + 1
    df["patient_encounter_total"] = df.groupby("patient_nbr")["encounter_id"].transform("size")
    df = df.sort_values("encounter_id").reset_index(drop=True)

    # 7. Decode IDs ----------------------------------------------------------
    df["admission_type"] = df["admission_type_id"].map(mapping["admission_type_id"])
    df["discharge_disposition"] = df["discharge_disposition_id"].map(mapping["discharge_disposition_id"])
    df["admission_source"] = df["admission_source_id"].map(mapping["admission_source_id"])
    df["admission_type_group"] = df["admission_type_id"].map(ADMISSION_TYPE_GROUP)
    df["discharge_group"] = df["discharge_disposition_id"].map(DISCHARGE_GROUP)
    df["admission_source_group"] = df["admission_source_id"].map(ADMISSION_SOURCE_GROUP)
    assert df[["admission_type_group", "discharge_group", "admission_source_group"]].notna().all().all()

    # 8. Drop columns not used ----------------------------------------------
    df = df.drop(columns=["weight", "age"] + CONSTANT_MEDS)

    assert len(df) == n_raw, "row count changed"
    assert df["encounter_id"].is_unique

    # ---------------------------------------------------------- outputs
    fact_cols = ["encounter_id", "patient_nbr", "race", "gender", "age_band",
                 "admission_type_id", "discharge_disposition_id", "admission_source_id",
                 "payer_code", "medical_specialty", "specialty_group",
                 "time_in_hospital", "num_lab_procedures", "num_procedures",
                 "num_medications", "number_outpatient", "number_emergency",
                 "number_inpatient", "number_diagnoses",
                 "diag_1", "diag_2", "diag_3", "diag_1_group", "diag_2_group",
                 "diag_3_group", "any_diabetes_diag",
                 "max_glu_serum", "A1Cresult",
                 "diabetes_meds_count", "med_dose_changes", "on_insulin",
                 "on_metformin", "insulin", "med_change_flag", "diabetes_med_flag",
                 "readmitted", "readmission_status", "readmit_30", "readmit_any",
                 "eligible_for_readmission", "prior_visits_total",
                 "prior_inpatient_band", "prior_emergency_band",
                 "prior_outpatient_band", "prior_visits_band", "los_band",
                 "medications_band", "lab_procedures_band", "diagnoses_band",
                 "patient_encounter_seq", "patient_encounter_total"]
    df[fact_cols].to_csv(OUT / "fact_encounter_clean.csv", index=False)

    # Medication-level long table (bridge for medication analysis)
    meds = df.melt(id_vars=["encounter_id"], value_vars=active_meds,
                   var_name="medication", value_name="dose_status")
    meds = meds[meds["dose_status"] != "No"]
    meds.to_csv(OUT / "fact_encounter_medication.csv", index=False)

    # Dimensions
    def dim(map_key, group_map, name):
        d = pd.DataFrame(sorted(mapping[map_key].items()), columns=[f"{name}_id", f"{name}"])
        d[f"{name}_group"] = d[f"{name}_id"].map(group_map).fillna("Not recorded")
        return d
    dim("admission_type_id", ADMISSION_TYPE_GROUP, "admission_type").to_csv(OUT / "dim_admission_type.csv", index=False)
    dim("discharge_disposition_id", DISCHARGE_GROUP, "discharge_disposition").to_csv(OUT / "dim_discharge_disposition.csv", index=False)
    dim("admission_source_id", ADMISSION_SOURCE_GROUP, "admission_source").to_csv(OUT / "dim_admission_source.csv", index=False)
    pd.DataFrame({"age_band": AGE_ORDER, "age_sort": range(1, 11),
                  "age_group": ["Under 30"] * 3 + ["30-49"] * 2 + ["50-69"] * 2 + ["70+"] * 3}
                 ).to_csv(OUT / "dim_age.csv", index=False)
    pat = df.groupby("patient_nbr").agg(
        encounters=("encounter_id", "size"),
        readmissions_30=("readmit_30", "sum")).reset_index()
    pat["patient_type"] = np.where(pat["encounters"] > 1, "Repeat patient", "Single encounter")
    pat.to_csv(OUT / "dim_patient.csv", index=False)

    # Full model-ready table for script 02
    df.to_pickle(OUT.parent / "model_outputs" / "_analysis_frame.pkl")

    # ---------------------------------------------------------- QA print
    elig = df[df.eligible_for_readmission == 1]
    print("raw rows", n_raw, "clean rows", len(df), "patients", df.patient_nbr.nunique())
    print("eligible", len(elig), "excluded (expired/hospice)", n_raw - len(elig))
    print("30-day readmit rate all", round(df.readmit_30.mean() * 100, 2),
          "eligible", round(elig.readmit_30.mean() * 100, 2))
    print("readmit any", round(df.readmit_any.mean() * 100, 2))
    print("diag_1 groups\n", df.diag_1_group.value_counts())


if __name__ == "__main__":
    main()
