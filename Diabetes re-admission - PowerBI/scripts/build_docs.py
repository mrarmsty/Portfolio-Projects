"""Generates the technical documentation that is derived directly from code (DAX, M, model)."""
from pathlib import Path
import importlib.util, json, re
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]
DOC = ROOT / "documentation"; DOC.mkdir(exist_ok=True)
spec = importlib.util.spec_from_file_location("sm", ROOT / "scripts" / "build_semantic_model.py")
sm = importlib.util.module_from_spec(spec); spec.loader.exec_module(sm)

# ---------------- DAX measures
lines = ["# DAX Measures", "",
         "All 67 measures live in the `KPI Measures` table of the semantic model and are grouped into display folders.",
         "Readmission rates use **eligible encounters** (discharges not to death or hospice) as the denominator.", ""]
folder = None
for fo, name, fmt, expr, desc in sm.MEASURES:
    if fo != folder:
        folder = fo; lines += [f"## {fo}", ""]
    import textwrap
    lines += [f"### {name}", "", desc, "", f"Format: `{fmt or 'text'}`", "", "```dax",
              f"{name} =", textwrap.dedent(expr).strip("\n"), "```", ""]
(DOC / "dax_measures.md").write_text("\n".join(lines), encoding="utf-8")

# ---------------- Power Query
order = ["fnIcd9Group", "fnSpecialtyGroup", "fnBand", "fnReadCsv", "DiabetesMedicationColumns",
         "Raw_Encounters", "Raw_IDS_Mapping", "Fact_Encounter", "Fact_Medication", "Dim_Age",
         "Dim_Admission_Type", "Dim_Admission_Source", "Dim_Discharge_Disposition", "Dim_Diagnosis_Group",
         "Model_Selector", "Model_Metrics", "Model_Threshold_Curve", "Model_ROC_Curve",
         "Model_Feature_Importance", "Model_Odds_Ratios", "Stat_Association_Tests"]
lines = ["# Power Query (M) Code", "",
         "Every query below is embedded in the semantic model and also stored as a standalone `.m` file in "
         "`analysis/power_query/`. `DataFolder` is a text parameter pointing at the repository `data\\` folder.", "",
         "| Query | Type | Loaded to model |", "|---|---|---|"]
for q in order:
    kind = "Function" if q.startswith("fn") else ("List" if q.startswith("Diabetes") else "Table")
    loaded = "No (staging)" if q.startswith(("fn", "Raw", "Diabetes")) else "Yes"
    lines.append(f"| {q} | {kind} | {loaded} |")
lines.append("")
for q in order:
    lines += [f"## {q}", "", "```powerquery", (ROOT / "analysis" / "power_query" / f"{q}.m").read_text().strip(), "```", ""]
(DOC / "power_query_m_code.md").write_text("\n".join(lines), encoding="utf-8")

# ---------------- data dictionary (cleaned fact table)
fact = pd.read_csv(ROOT / "data" / "processed" / "fact_encounter_clean.csv", low_memory=False)
desc = {
 "encounter_id": "Unique identifier of a hospital encounter (primary key).",
 "patient_nbr": "Patient identifier; a patient can have several encounters.",
 "race": "Recorded race. '?' recoded to 'Not recorded'; 'AfricanAmerican' relabelled.",
 "gender": "Female / Male / Unknown (3 'Unknown/Invalid' records).",
 "age_band": "10-year age band (brackets removed, e.g. '70-80').",
 "admission_type_id": "Admission type code; decoded with IDS_mapping (Dim_Admission_Type).",
 "discharge_disposition_id": "Discharge disposition code; decoded with IDS_mapping (Dim_Discharge_Disposition).",
 "admission_source_id": "Admission source code; decoded with IDS_mapping (Dim_Admission_Source).",
 "payer_code": "Payer code; 39.6% missing, recoded 'Not recorded'. Not used in analysis.",
 "medical_specialty": "Specialty of admitting physician; 49.1% missing, recoded 'Not recorded'.",
 "specialty_group": "Derived: specialty collapsed to the 10 most frequent groups + Surgery / Other.",
 "time_in_hospital": "Length of stay in days (1-14).",
 "num_lab_procedures": "Number of lab tests during the encounter.",
 "num_procedures": "Number of non-lab procedures (0-6).",
 "num_medications": "Number of distinct generic medications administered.",
 "number_outpatient": "Outpatient visits in the year before the encounter.",
 "number_emergency": "Emergency visits in the year before the encounter.",
 "number_inpatient": "Inpatient visits in the year before the encounter.",
 "number_diagnoses": "Number of diagnoses entered (1-16).",
 "diag_1": "Primary diagnosis (ICD-9 code as text).", "diag_2": "Secondary diagnosis (ICD-9).", "diag_3": "Additional diagnosis (ICD-9).",
 "diag_1_group": "Derived ICD-9 chapter of diag_1 (Strack et al. 2014 grouping).",
 "diag_2_group": "Derived ICD-9 chapter of diag_2.", "diag_3_group": "Derived ICD-9 chapter of diag_3.",
 "any_diabetes_diag": "Derived: 1 if any of the three diagnoses is 250.xx.",
 "max_glu_serum": "Max glucose serum test result; 'None' = Not measured.",
 "A1Cresult": "HbA1c test result; 'None' = Not measured; 'Norm' = Normal.",
 "diabetes_meds_count": "Derived: number of the 21 diabetes medications prescribed (status not 'No').",
 "med_dose_changes": "Derived: number of diabetes medications with dose Up or Down.",
 "on_insulin": "Derived flag: insulin prescribed.", "on_metformin": "Derived flag: metformin prescribed.",
 "insulin": "Insulin status: No / Steady / Up / Down.",
 "med_change_flag": "Derived flag: any change in diabetes medication ('change' = Ch).",
 "diabetes_med_flag": "Derived flag: any diabetes medication prescribed ('diabetesMed' = Yes).",
 "readmitted": "Original outcome: '<30', '>30' or 'NO'.",
 "readmission_status": "Derived label of readmitted.",
 "readmit_30": "Target: 1 if readmitted within 30 days.",
 "readmit_any": "1 if readmitted at any time.",
 "eligible_for_readmission": "0 if discharged to death or hospice (codes 11, 13, 14, 19, 20, 21), else 1.",
 "prior_visits_total": "Derived: outpatient + emergency + inpatient visits in prior year.",
 "prior_inpatient_band": "Band of number_inpatient: 0, 1, 2, 3-4, 5+.",
 "prior_emergency_band": "Band of number_emergency: 0, 1, 2+.", "prior_outpatient_band": "Band of number_outpatient: 0, 1, 2+.",
 "prior_visits_band": "Band of prior_visits_total: 0, 1, 2, 3-4, 5+.",
 "los_band": "Length of stay band: 1-2, 3-4, 5-7, 8-14 days.", "medications_band": "Medications band: 1-10, 11-15, 16-20, 21-30, 31+.",
 "lab_procedures_band": "Lab procedures band: 1-30, 31-45, 46-60, 61+.", "diagnoses_band": "Diagnoses band: 1-4, 5-6, 7-8, 9+.",
 "patient_encounter_seq": "Derived: order of the encounter within the patient (by encounter_id; assumption, no dates).",
 "patient_encounter_total": "Derived: number of encounters for the patient in the extract.",
}
rows = ["# Data Dictionary", "",
        "## Raw source", "",
        "`data/raw/diabetic_data.xlsx` - sheet `diabetic_data` (101,766 rows x 50 columns) and sheet `IDS_mapping` "
        "(three stacked lookup tables for admission type, discharge disposition and admission source).", "",
        "Columns dropped during cleaning: `weight` (96.9% missing), `examide` and `citoglipton` (constant 'No'). "
        "The other 21 medication columns are kept in long form in `fact_encounter_medication.csv`.", "",
        "## Cleaned fact table - `data/processed/fact_encounter_clean.csv`", "",
        "| Variable | Data type | Description | Example / value range | Data quality observations |", "|---|---|---|---|---|"]
for c in fact.columns:
    s = fact[c]
    if s.dtype.kind in "if":
        ex = f"{s.min():g} to {s.max():g}"
    else:
        vc = s.astype(str).value_counts()
        ex = ", ".join(vc.index[:4]) + (f" (+{len(vc)-4} more)" if len(vc) > 4 else "")
    nr = (s.astype(str) == "Not recorded").mean()
    q = f"{nr:.1%} 'Not recorded'" if nr > 0 else ("No missing values" if s.notna().all() else f"{s.isna().mean():.1%} blank")
    rows.append(f"| {c} | {'integer' if s.dtype.kind=='i' else 'decimal' if s.dtype.kind=='f' else 'text'} | {desc.get(c,'')} | {ex.replace('|','/')} | {q} |")
rows += ["", "## Other processed tables", "",
         "| File | Grain | Columns |", "|---|---|---|",
         "| fact_encounter_medication.csv | encounter x prescribed diabetes medication | encounter_id, medication, dose_status (Steady/Up/Down) |",
         "| dim_admission_type.csv | admission type code | id, description, group |",
         "| dim_discharge_disposition.csv | discharge code | id, description, group |",
         "| dim_admission_source.csv | admission source code | id, description, group |",
         "| dim_age.csv | age band | age_band, age_sort, age_group |",
         "| dim_patient.csv | patient | patient_nbr, encounters, readmissions_30, patient_type |",
         "", "## Model output tables (`data/model_outputs/`)", "",
         "| File | Content |", "|---|---|",
         "| encounter_predictions.csv | encounter_id, data_split (Train/Test), p_lr, p_rf, risk_decile, risk_tier |",
         "| model_metrics.csv | CV and test metrics per model and the baseline rule |",
         "| model_threshold_curve.csv | confusion matrix and precision/recall at thresholds 0.02-0.60 (test set) |",
         "| model_roc_curve.csv | ROC curve points (FPR grid 0-1) per model |",
         "| feature_importance.csv | permutation importance (drop in test ROC-AUC) per feature and model |",
         "| lr_odds_ratios.csv | statsmodels logistic regression odds ratios with 95% CI |",
         "| association_tests.csv | chi-square / Mann-Whitney results with effect sizes |", "",
         "Assumptions requiring confirmation: the meaning of codes without a description in IDS_mapping "
         "(admission type 6, admission source 17, discharge 18) is unknown; they are grouped as 'Not recorded'."]
(DOC / "data_dictionary.md").write_text("\n".join(rows), encoding="utf-8")
print("docs written")
