"""
build_semantic_model.py
Writes the Power BI semantic model (TMDL) for the .pbip project.
Power Query M is read from analysis/power_query/*.m so the M files in the
repository and the M inside the model are always identical.
"""
from pathlib import Path
import uuid, json, textwrap

ROOT = Path(__file__).resolve().parents[1]
PQ = ROOT / "analysis" / "power_query"
NAME = "Diabetes_Readmission_Analysis"
SM = ROOT / "analysis" / f"{NAME}.SemanticModel"
DEF = SM / "definition"
DATA_FOLDER = r"C:\Users\HP\Desktop\Mine\AI Portfolio projects\Power BI\Diabetes_Readmission_Risk_Analytics\data" + "\\"

NS = uuid.UUID("6f1c2a2e-1d1e-4a57-9a61-3b2f0c9d7e11")
def tag(*parts):
    return str(uuid.uuid5(NS, "|".join(parts)))

def q(name):          # TMDL object name quoting
    return f"'{name}'" if any(c in name for c in " -()%.<>/'+") or name[0].isdigit() else name

def m_block(text, indent=4):
    pad = "\t" * indent
    return "\n".join(pad + line if line.strip() else "" for line in text.strip("\n").splitlines())

def dax_block(text, indent=3):
    pad = "\t" * indent
    return "\n".join(pad + line for line in textwrap.dedent(text).strip("\n").splitlines())

# ---------------------------------------------------------------- columns
INT, DBL, TXT = "int64", "double", "string"
def col(name, dtype, fmt=None, summarize="none", sort_by=None, hidden=False, folder=None):
    return dict(name=name, dtype=dtype, fmt=fmt, summarize=summarize, sort_by=sort_by,
                hidden=hidden, folder=folder)

FACT_COLS = [
    col("Encounter ID", INT, "0"), col("Patient Number", INT, "0"),
    col("Race", TXT), col("Gender", TXT), col("Age Band", TXT, hidden=True),
    col("Admission Type ID", INT, "0", hidden=True), col("Discharge Disposition ID", INT, "0", hidden=True),
    col("Admission Source ID", INT, "0", hidden=True),
    col("Length of Stay", INT, "0", "sum"), col("Payer Code", TXT), col("Medical Specialty", TXT),
    col("Lab Procedures", INT, "0", "sum"), col("Procedures", INT, "0", "sum"),
    col("Medications", INT, "0", "sum"), col("Prior Outpatient Visits", INT, "0", "sum"),
    col("Prior Emergency Visits", INT, "0", "sum"), col("Prior Inpatient Visits", INT, "0", "sum"),
    col("Primary Diagnosis Code", TXT), col("Secondary Diagnosis Code", TXT), col("Additional Diagnosis Code", TXT),
    col("Diagnoses Count", INT, "0", "sum"), col("Max Glucose Serum", TXT), col("HbA1c Result", TXT),
    col("Metformin Status", TXT), col("Insulin Status", TXT), col("On Diabetes Medication", TXT),
    col("Readmitted Code", TXT), col("Specialty Group", TXT),
    col("Primary Diagnosis Group", TXT, hidden=True), col("Secondary Diagnosis Group", TXT),
    col("Additional Diagnosis Group", TXT),
    col("Readmitted 30 Days", INT, "0", "sum"), col("Readmitted Any", INT, "0", "sum"),
    col("Readmission Status", TXT, sort_by="Readmission Status Sort"), col("Readmission Status Sort", INT, "0", hidden=True),
    col("Eligible for Readmission", INT, "0"),
    col("Total Prior Visits", INT, "0", "sum"),
]
for b in ["Prior Inpatient Band", "Prior Emergency Band", "Prior Outpatient Band", "Prior Visits Band",
          "Length of Stay Band", "Medications Band", "Lab Procedures Band", "Diagnoses Band"]:
    FACT_COLS += [col(b, TXT, sort_by=f"{b} Sort", folder="Bands"),
                  col(f"{b} Sort", INT, "0", hidden=True, folder="Bands")]
FACT_COLS += [
    col("Diabetes Medications Count", INT, "0", "sum"), col("Medication Dose Changes", INT, "0", "sum"),
    col("Medication Changed", TXT), col("Patient Encounter Count", INT, "0"), col("Patient Type", TXT),
    col("Data Split", TXT, folder="Model scores"),
    col("Risk Score LR", DBL, "0.0%", folder="Model scores"), col("Risk Score RF", DBL, "0.0%", folder="Model scores"),
    col("Risk Decile", INT, "0", folder="Model scores"),
    col("Risk Tier", TXT, sort_by="Risk Tier Sort", folder="Model scores"),
    col("Risk Tier Sort", INT, "0", hidden=True, folder="Model scores"),
]

TABLES = {
    "Fact_Encounter": dict(m="Fact_Encounter", cols=FACT_COLS),
    "Fact_Medication": dict(m="Fact_Medication", cols=[
        col("Encounter ID", INT, "0", hidden=True), col("Medication", TXT), col("Dose Status", TXT)]),
    "Dim_Admission_Type": dict(m="Dim_Admission_Type", cols=[
        col("Admission Type ID", INT, "0"), col("Admission Type", TXT), col("Admission Type Group", TXT)]),
    "Dim_Discharge_Disposition": dict(m="Dim_Discharge_Disposition", cols=[
        col("Discharge Disposition ID", INT, "0"), col("Discharge Disposition", TXT),
        col("Discharge Group", TXT), col("Readmission Possible", TXT)]),
    "Dim_Admission_Source": dict(m="Dim_Admission_Source", cols=[
        col("Admission Source ID", INT, "0"), col("Admission Source", TXT), col("Admission Source Group", TXT)]),
    "Dim_Age": dict(m="Dim_Age", cols=[
        col("Age Band", TXT, sort_by="Age Sort"), col("Age Sort", INT, "0", hidden=True),
        col("Age Group", TXT, sort_by="Age Group Sort"), col("Age Group Sort", INT, "0", hidden=True)]),
    "Dim_Diagnosis_Group": dict(m="Dim_Diagnosis_Group", cols=[
        col("Diagnosis Group", TXT, sort_by="Diagnosis Group Sort"),
        col("Diagnosis Group Sort", INT, "0", hidden=True), col("ICD9 Range", TXT)]),
    "Model Selector": dict(m="Model_Selector", cols=[
        col("Model", TXT, sort_by="Model Sort"), col("Model Sort", INT, "0", hidden=True)]),
    "Model_Metrics": dict(m="Model_Metrics", cols=[
        col("Model", TXT, sort_by="Model Order"), col("Model Order", INT, "0", hidden=True),
        col("CV ROC-AUC", DBL, "0.000"), col("CV ROC-AUC SD", DBL, "0.000"), col("Test ROC-AUC", DBL, "0.000"),
        col("Test PR-AUC", DBL, "0.000"), col("Brier Score", DBL, "0.0000"), col("Threshold (top 20%)", DBL, "0.000"),
        col("True Positives", INT, "#,0"), col("False Positives", INT, "#,0"), col("False Negatives", INT, "#,0"),
        col("True Negatives", INT, "#,0"), col("Precision", DBL, "0.0%"), col("Recall", DBL, "0.0%"),
        col("Specificity", DBL, "0.0%"), col("F1 Score", DBL, "0.000"), col("Alert Rate", DBL, "0.0%")]),
    "Model_Threshold_Curve": dict(m="Model_Threshold_Curve", cols=[
        col("Model", TXT), col("Threshold", DBL, "0%"), col("True Positives", INT, "#,0", "sum"),
        col("False Positives", INT, "#,0", "sum"), col("False Negatives", INT, "#,0", "sum"),
        col("True Negatives", INT, "#,0", "sum"), col("Precision", DBL, "0.0%"), col("Recall", DBL, "0.0%"),
        col("Specificity", DBL, "0.0%"), col("F1 Score", DBL, "0.000"), col("Alert Rate", DBL, "0.0%"),
        col("Accuracy", DBL, "0.0%")]),
    "Model_ROC_Curve": dict(m="Model_ROC_Curve", cols=[
        col("Curve", TXT), col("False Positive Rate", DBL, "0.00"), col("True Positive Rate", DBL, "0.00")]),
    "Model_Feature_Importance": dict(m="Model_Feature_Importance", cols=[
        col("Model", TXT), col("Feature", TXT), col("Feature Code", TXT, hidden=True),
        col("AUC Drop", DBL, "0.0000"), col("AUC Drop SD", DBL, "0.0000"), col("Importance Rank", INT, "0")]),
    "Model_Odds_Ratios": dict(m="Model_Odds_Ratios", cols=[
        col("Term Code", TXT, hidden=True), col("Coefficient", DBL, "0.000"), col("Odds Ratio", DBL, "0.00"),
        col("OR 95% CI Low", DBL, "0.00"), col("OR 95% CI High", DBL, "0.00"), col("P Value", DBL, "0.0000"),
        col("Term", TXT), col("Significant", TXT), col("Direction", TXT), col("Chart Flag", TXT)]),
    "Stat_Association_Tests": dict(m="Stat_Association_Tests", cols=[
        col("Variable", TXT), col("Variable Type", TXT), col("Test", TXT), col("Test Statistic", DBL, "#,0.0"),
        col("Degrees of Freedom", DBL, "0"), col("P Value", DBL, "0.0000"), col("Effect Size", DBL, "0.000"),
        col("Effect Measure", TXT), col("Min Expected Count", DBL, "#,0.0"), col("Highest-Rate Group", TXT),
        col("Highest Rate (%)", DBL, "0.00"), col("Lowest-Rate Group", TXT), col("Lowest Rate (%)", DBL, "0.00"),
        col("Significant (p<0.05)", TXT), col("P Value (display)", TXT)]),
}

# ---------------------------------------------------------------- measures
F = "Fact_Encounter"
MEASURES = [
    # (folder, name, format, expression, description)
    ("1 Volume", "Encounters", "#,0", f"COUNTROWS ( {F} )", "Number of hospital encounters in the current filter context."),
    ("1 Volume", "Patients", "#,0", f"DISTINCTCOUNT ( {F}[Patient Number] )", "Distinct patients."),
    ("1 Volume", "Eligible Encounters", "#,0",
     f"CALCULATE ( [Encounters], {F}[Eligible for Readmission] = 1 )",
     "Encounters where a readmission was possible (excludes death and hospice discharges). Denominator for readmission rates."),
    ("1 Volume", "Excluded Encounters (Expired or Hospice)", "#,0",
     f"CALCULATE ( [Encounters], {F}[Eligible for Readmission] = 0 )", "Encounters excluded from readmission denominators."),
    ("1 Volume", "Encounters per Patient", "0.00", "DIVIDE ( [Encounters], [Patients] )", "Average encounters per patient."),
    ("1 Volume", "Repeat Patient Share", "0.0%",
     f"DIVIDE ( CALCULATE ( [Patients], {F}[Patient Type] = \"Repeat patient\" ), [Patients] )",
     "Share of patients with more than one encounter in the extract."),
    ("1 Volume", "Share of Encounters", "0.0%", "DIVIDE ( [Encounters], CALCULATE ( [Encounters], ALLSELECTED () ) )",
     "Encounters as a share of all encounters visible in the visual."),

    ("2 Readmission", "30-Day Readmissions", "#,0",
     f"CALCULATE ( [Encounters], {F}[Readmitted 30 Days] = 1, {F}[Eligible for Readmission] = 1 )",
     "Eligible encounters followed by a readmission within 30 days."),
    ("2 Readmission", "30-Day Readmission Rate", "0.0%", "DIVIDE ( [30-Day Readmissions], [Eligible Encounters] )",
     "Primary KPI: 30-day readmissions / eligible encounters."),
    ("2 Readmission", "Readmissions After 30 Days", "#,0",
     f"CALCULATE ( [Encounters], {F}[Readmission Status] = \"After 30 days\", {F}[Eligible for Readmission] = 1 )",
     "Eligible encounters readmitted after more than 30 days."),
    ("2 Readmission", "Any Readmission Rate", "0.0%",
     f"DIVIDE ( CALCULATE ( [Encounters], {F}[Readmitted Any] = 1, {F}[Eligible for Readmission] = 1 ), [Eligible Encounters] )",
     "Readmitted at any time (within or after 30 days) / eligible encounters."),
    ("2 Readmission", "Crude 30-Day Rate (All Encounters)", "0.00%",
     f"DIVIDE ( SUM ( {F}[Readmitted 30 Days] ), [Encounters] )",
     "Unadjusted rate on all 101,766 encounters, kept for reconciliation with the raw file."),
    ("2 Readmission", "Overall 30-Day Readmission Rate", "0.0%",
     "CALCULATE ( [30-Day Readmission Rate], REMOVEFILTERS () )", "Organisation-wide benchmark, ignores all filters."),
    ("2 Readmission", "Rate Difference vs Overall (pp)", "+0.0;-0.0;0.0",
     """
     VAR _rate = [30-Day Readmission Rate]
     RETURN IF ( ISBLANK ( _rate ), BLANK (), ( _rate - [Overall 30-Day Readmission Rate] ) * 100 )
     """, "Percentage-point gap between the group rate and the overall rate."),
    ("2 Readmission", "Relative Rate vs Overall", "0.00\"x\"",
     "DIVIDE ( [30-Day Readmission Rate], [Overall 30-Day Readmission Rate] )", "Group rate divided by the overall rate."),
    ("2 Readmission", "Share of 30-Day Readmissions", "0.0%",
     "DIVIDE ( [30-Day Readmissions], CALCULATE ( [30-Day Readmissions], ALLSELECTED () ) )",
     "Contribution of the group to all 30-day readmissions in view."),
    ("2 Readmission", "Readmission Rate Colour", None,
     """
     VAR _rate = [30-Day Readmission Rate]
     VAR _overall = [Overall 30-Day Readmission Rate]
     RETURN
         SWITCH (
             TRUE (),
             ISBLANK ( _rate ), "#B8C1CC",
             _rate >= _overall * 1.2, "#C0392B",
             _rate >= _overall * 1.05, "#E67E22",
             _rate <= _overall * 0.85, "#2A9D8F",
             "#5B7A99"
         )
     """, "Colour rule: red >= 1.2x overall, amber >= 1.05x, teal <= 0.85x, otherwise blue-grey."),
    ("2 Readmission", "Rate - No Prior Inpatient Visit", "0.0%",
     f"CALCULATE ( [30-Day Readmission Rate], {F}[Prior Inpatient Visits] = 0 )", "Rate for encounters with no inpatient visit in the prior year."),
    ("2 Readmission", "Rate - 3+ Prior Inpatient Visits", "0.0%",
     f"CALCULATE ( [30-Day Readmission Rate], {F}[Prior Inpatient Visits] >= 3 )", "Rate for encounters with three or more prior inpatient visits."),
    ("2 Readmission", "Prior Inpatient Risk Multiple", "0.0\"x\"",
     "DIVIDE ( [Rate - 3+ Prior Inpatient Visits], [Rate - No Prior Inpatient Visit] )",
     "How many times higher the rate is for 3+ prior inpatient visits versus none."),
    ("2 Readmission", "Highest-Rate Discharge Group", None,
     """
     VAR _groups =
         FILTER (
             ADDCOLUMNS (
                 VALUES ( Dim_Discharge_Disposition[Discharge Group] ),
                 "@n", [Eligible Encounters],
                 "@rate", [30-Day Readmission Rate]
             ),
             [@n] >= 500
         )
     RETURN MAXX ( TOPN ( 1, _groups, [@rate], DESC ), Dim_Discharge_Disposition[Discharge Group] )
     """, "Discharge group with the highest 30-day rate among groups with at least 500 eligible encounters."),
    ("2 Readmission", "Discharge Group Rank", "0",
     """
     IF (
         HASONEVALUE ( Dim_Discharge_Disposition[Discharge Group] ),
         RANKX ( ALLSELECTED ( Dim_Discharge_Disposition[Discharge Group] ), [30-Day Readmission Rate], , DESC, DENSE )
     )
     """, "Rank of the discharge group by 30-day readmission rate (1 = highest)."),
    ("2 Readmission", "Headline Readmission Text", None,
     """
     "30-day readmission rate: " & FORMAT ( [30-Day Readmission Rate], "0.0%" )
         & " (" & FORMAT ( [30-Day Readmissions], "#,0" ) & " of "
         & FORMAT ( [Eligible Encounters], "#,0" ) & " eligible encounters)"
     """, "Dynamic headline that responds to slicers."),

    ("3 Utilisation", "Average Length of Stay", "0.00", f"AVERAGE ( {F}[Length of Stay] )", "Mean days in hospital."),
    ("3 Utilisation", "Total Bed Days", "#,0", f"SUM ( {F}[Length of Stay] )", "Sum of length of stay."),
    ("3 Utilisation", "Share of Bed Days", "0.0%", "DIVIDE ( [Total Bed Days], CALCULATE ( [Total Bed Days], ALLSELECTED () ) )", "Share of bed days in view."),
    ("3 Utilisation", "Average Medications", "0.0", f"AVERAGE ( {F}[Medications] )", "Mean distinct medications administered."),
    ("3 Utilisation", "Average Procedures", "0.00", f"AVERAGE ( {F}[Procedures] )", "Mean non-lab procedures."),
    ("3 Utilisation", "Average Lab Procedures", "0.0", f"AVERAGE ( {F}[Lab Procedures] )", "Mean lab tests."),
    ("3 Utilisation", "Average Diagnoses", "0.0", f"AVERAGE ( {F}[Diagnoses Count] )", "Mean diagnoses recorded."),
    ("3 Utilisation", "Average Prior Inpatient Visits", "0.00", f"AVERAGE ( {F}[Prior Inpatient Visits] )", "Mean inpatient visits in prior year."),
    ("3 Utilisation", "Average Prior Emergency Visits", "0.00", f"AVERAGE ( {F}[Prior Emergency Visits] )", "Mean emergency visits in prior year."),
    ("3 Utilisation", "Average Prior Outpatient Visits", "0.00", f"AVERAGE ( {F}[Prior Outpatient Visits] )", "Mean outpatient visits in prior year."),
    ("3 Utilisation", "Long Stay Share (8+ days)", "0.0%",
     f"DIVIDE ( CALCULATE ( [Encounters], {F}[Length of Stay] >= 8 ), [Encounters] )", "Share of stays of 8 days or more."),
    ("3 Utilisation", "Share with Procedures", "0.0%",
     f"DIVIDE ( CALCULATE ( [Encounters], {F}[Procedures] > 0 ), [Encounters] )", "Share of encounters with at least one procedure."),
    ("3 Utilisation", "Share with Prior Inpatient Visit", "0.0%",
     f"DIVIDE ( CALCULATE ( [Encounters], {F}[Prior Inpatient Visits] >= 1 ), [Encounters] )", "Share with at least one prior inpatient visit."),
    ("3 Utilisation", "Avg LOS - Readmitted 30 Days", "0.00",
     f"CALCULATE ( [Average Length of Stay], {F}[Readmitted 30 Days] = 1, {F}[Eligible for Readmission] = 1 )", "Mean LOS for index stays followed by a 30-day readmission."),
    ("3 Utilisation", "Avg LOS - Not Readmitted 30 Days", "0.00",
     f"CALCULATE ( [Average Length of Stay], {F}[Readmitted 30 Days] = 0, {F}[Eligible for Readmission] = 1 )", "Mean LOS for other eligible stays."),
    ("3 Utilisation", "Avg Medications - Readmitted 30 Days", "0.0",
     f"CALCULATE ( [Average Medications], {F}[Readmitted 30 Days] = 1, {F}[Eligible for Readmission] = 1 )", "Mean medications, readmitted group."),
    ("3 Utilisation", "Avg Medications - Not Readmitted 30 Days", "0.0",
     f"CALCULATE ( [Average Medications], {F}[Readmitted 30 Days] = 0, {F}[Eligible for Readmission] = 1 )", "Mean medications, not readmitted group."),
    ("3 Utilisation", "Encounters with Medication", "#,0",
     "CALCULATE ( DISTINCTCOUNT ( Fact_Medication[Encounter ID] ) )", "Encounters prescribed the medication(s) in context."),
    ("3 Utilisation", "Medication 30-Day Readmission Rate", "0.0%",
     """
     VAR _enc = VALUES ( Fact_Medication[Encounter ID] )
     RETURN CALCULATE ( [30-Day Readmission Rate], TREATAS ( _enc, Fact_Encounter[Encounter ID] ) )
     """, "30-day readmission rate for encounters prescribed the medication in context."),

    ("4 Model", "Selected Threshold", "0%", "SELECTEDVALUE ( 'Alert Threshold'[Alert Threshold], 0.15 )", "Risk threshold chosen in the slicer (default 15%)."),
    ("4 Model", "Selected Model", None, "SELECTEDVALUE ( 'Model Selector'[Model], \"Random Forest\" )", "Model chosen in the slicer (default Random Forest)."),
    ("4 Model", "Test Encounters", "#,0", f"CALCULATE ( [Encounters], {F}[Data Split] = \"Test\" )", "Hold-out test encounters (20% of patients)."),
    ("4 Model", "Test Readmissions", "#,0",
     f"CALCULATE ( [Encounters], {F}[Data Split] = \"Test\", {F}[Readmitted 30 Days] = 1 )", "Actual 30-day readmissions in the test set."),
    ("4 Model", "Observed Test Readmission Rate", "0.0%", "DIVIDE ( [Test Readmissions], [Test Encounters] )", "Observed rate in the test set."),
    ("4 Model", "Average Predicted Risk", "0.0%",
     f"""
     VAR _m = [Selected Model]
     RETURN
         CALCULATE (
             IF ( _m = "Random Forest", AVERAGE ( {F}[Risk Score RF] ), AVERAGE ( {F}[Risk Score LR] ) ),
             {F}[Data Split] = "Test"
         )
     """, "Mean predicted probability in the test set (calibration check)."),
    ("4 Model", "Flagged Encounters", "#,0",
     f"""
     VAR _thr = [Selected Threshold]
     VAR _m = [Selected Model]
     VAR _flagged =
         FILTER (
             CALCULATETABLE ( {F}, {F}[Data Split] = "Test" ),
             IF ( _m = "Random Forest", {F}[Risk Score RF], {F}[Risk Score LR] ) >= _thr
         )
     RETURN COUNTROWS ( _flagged ) + 0
     """, "Test encounters whose predicted risk is at or above the threshold (alerts)."),
    ("4 Model", "True Positives", "#,0",
     f"""
     VAR _thr = [Selected Threshold]
     VAR _m = [Selected Model]
     VAR _hits =
         FILTER (
             CALCULATETABLE ( {F}, {F}[Data Split] = "Test", {F}[Readmitted 30 Days] = 1 ),
             IF ( _m = "Random Forest", {F}[Risk Score RF], {F}[Risk Score LR] ) >= _thr
         )
     RETURN COUNTROWS ( _hits ) + 0
     """, "Flagged encounters that were readmitted within 30 days."),
    ("4 Model", "False Positives", "#,0", "[Flagged Encounters] - [True Positives]", "Flagged encounters that were not readmitted (false alarms)."),
    ("4 Model", "False Negatives", "#,0", "[Test Readmissions] - [True Positives]", "Readmissions the model missed."),
    ("4 Model", "True Negatives", "#,0", "[Test Encounters] - [Flagged Encounters] - [False Negatives]", "Correctly not flagged."),
    ("4 Model", "Precision", "0.0%", "DIVIDE ( [True Positives], [Flagged Encounters] )", "Share of alerts that are true readmissions (PPV)."),
    ("4 Model", "Recall", "0.0%", "DIVIDE ( [True Positives], [Test Readmissions] )", "Share of readmissions that were flagged (sensitivity)."),
    ("4 Model", "Specificity", "0.0%", "DIVIDE ( [True Negatives], [True Negatives] + [False Positives] )", "Share of non-readmissions correctly not flagged."),
    ("4 Model", "F1 Score", "0.000", "DIVIDE ( 2 * [Precision] * [Recall], [Precision] + [Recall] )", "Harmonic mean of precision and recall."),
    ("4 Model", "Alert Rate", "0.0%", "DIVIDE ( [Flagged Encounters], [Test Encounters] )", "Share of discharges that would trigger an alert."),
    ("4 Model", "False Alarms per True Readmission", "0.0", "DIVIDE ( [False Positives], [True Positives] )", "Workload cost of each readmission caught."),
    ("4 Model", "Lift over Base Rate", "0.00\"x\"", "DIVIDE ( [Precision], [Observed Test Readmission Rate] )", "How much more concentrated readmissions are among alerts."),
    ("4 Model", "Threshold Narrative", None,
     """
     "At a " & FORMAT ( [Selected Threshold], "0%" ) & " risk threshold the " & [Selected Model]
         & " flags " & FORMAT ( [Flagged Encounters], "#,0" ) & " of " & FORMAT ( [Test Encounters], "#,0" )
         & " test discharges (" & FORMAT ( [Alert Rate], "0.0%" ) & "). It catches "
         & FORMAT ( [Recall], "0%" ) & " of 30-day readmissions; " & FORMAT ( [Precision], "0%" )
         & " of alerts are true readmissions (" & FORMAT ( [False Alarms per True Readmission], "0.0" )
         & " false alarms per readmission caught)."
     """, "Plain-English summary of the selected operating point."),
    ("4 Model", "Curve Precision", "0.0%", "AVERAGE ( Model_Threshold_Curve[Precision] )", "Precision from the Python threshold curve."),
    ("4 Model", "Curve Recall", "0.0%", "AVERAGE ( Model_Threshold_Curve[Recall] )", "Recall from the Python threshold curve."),
    ("4 Model", "Curve Alert Rate", "0.0%", "AVERAGE ( Model_Threshold_Curve[Alert Rate] )", "Alert rate from the Python threshold curve."),
    ("4 Model", "ROC True Positive Rate", "0.00", "AVERAGE ( Model_ROC_Curve[True Positive Rate] )", "TPR for the ROC chart."),
    ("4 Model", "Feature Importance (AUC Drop)", "0.0000", "SUM ( Model_Feature_Importance[AUC Drop] )", "Permutation importance."),
    ("4 Model", "Odds Ratio", "0.00", "AVERAGE ( Model_Odds_Ratios[Odds Ratio] )", "Logistic regression odds ratio."),
]

# ---------------------------------------------------------------- writers
def write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.replace("\r\n", "\n"), encoding="utf-8")

def table_tmdl(tname, spec):
    out = [f"table {q(tname)}", f"\tlineageTag: {tag('table', tname)}", ""]
    if tname == "KPI Measures":
        for folder, name, fmt, expr, desc in MEASURES:
            out.append(f"\t/// {desc}")
            expr = expr.strip("\n")
            if "\n" in textwrap.dedent(expr).strip():
                out.append(f"\tmeasure {q(name)} =")
                out.append(dax_block(expr))
            else:
                out.append(f"\tmeasure {q(name)} = {expr.strip()}")
            if fmt:
                out.append(f"\t\tformatString: {fmt}")
            out.append(f"\t\tdisplayFolder: {folder}")
            out.append(f"\t\tlineageTag: {tag('measure', name)}")
            out.append("")
    for c in spec["cols"]:
        out.append(f"\tcolumn {q(c['name'])}")
        out.append(f"\t\tdataType: {c['dtype']}")
        if c["fmt"]:
            out.append(f"\t\tformatString: {c['fmt']}")
        if c["hidden"]:
            out.append("\t\tisHidden")
        if c["folder"]:
            out.append(f"\t\tdisplayFolder: {c['folder']}")
        out.append(f"\t\tlineageTag: {tag('col', tname, c['name'])}")
        out.append(f"\t\tsummarizeBy: {c['summarize']}")
        if spec.get("calculated"):
            out.append("\t\tisNameInferred")
            out.append(f"\t\tsourceColumn: [{c['name']}]")
        else:
            out.append(f"\t\tsourceColumn: {c['name']}")
        if c["sort_by"]:
            out.append(f"\t\tsortByColumn: {q(c['sort_by'])}")
        out.append("")
        out.append("\t\tannotation SummarizationSetBy = Automatic")
        out.append("")
    if spec.get("calculated"):
        out.append(f"\tpartition {q(tname)} = calculated")
        out.append("\t\tmode: import")
        out.append(f"\t\tsource = {spec['calculated']}")
    else:
        m = (PQ / f"{spec['m']}.m").read_text()
        out.append(f"\tpartition {q(tname)} = m")
        out.append("\t\tmode: import")
        out.append("\t\tsource =")
        out.append(m_block(m))
    out.append("")
    out.append("\tannotation PBI_ResultType = Table")
    out.append("")
    return "\n".join(out)

def main():
    import shutil
    if SM.exists():
        shutil.rmtree(SM)
    write(SM / "definition.pbism", json.dumps({
        "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/semanticModel/definitionProperties/1.0.0/schema.json",
        "version": "4.2", "settings": {}}, indent=2))
    write(DEF / "database.tmdl", "database\n\tcompatibilityLevel: 1600\n\n")

    tables = dict(TABLES)
    tables["Alert Threshold"] = dict(cols=[col("Alert Threshold", DBL, "0%")],
                                     calculated='SELECTCOLUMNS ( GENERATESERIES ( 5, 40, 1 ), "Alert Threshold", [Value] / 100 )')
    tables["KPI Measures"] = dict(m="Measures", cols=[col("Measure Group", TXT, hidden=True)])
    write(PQ / "Measures.m", '// Placeholder table that holds the report measures.\nlet\n    Source = #table(type table [Measure Group = text], {})\nin\n    Source\n')

    order = ["KPI Measures", "Fact_Encounter", "Fact_Medication", "Dim_Age", "Dim_Admission_Type",
             "Dim_Admission_Source", "Dim_Discharge_Disposition", "Dim_Diagnosis_Group",
             "Model Selector", "Alert Threshold", "Model_Metrics", "Model_Threshold_Curve",
             "Model_ROC_Curve", "Model_Feature_Importance", "Model_Odds_Ratios", "Stat_Association_Tests"]
    model = ["model Model", "\tculture: en-US", "\tdefaultPowerBIDataSourceVersion: powerBI_V3",
             "\tsourceQueryCulture: en-US", "\tdataAccessOptions", "\t\tlegacyRedirects", "\t\treturnErrorValuesAsNull", "",
             "queryGroup 'Staging and functions'", "", "\tannotation PBI_QueryGroupOrder = 0", "",
             "queryGroup Parameters", "", "\tannotation PBI_QueryGroupOrder = 1", "",
             "annotation __PBI_TimeIntelligenceEnabled = 0", "",
             "annotation PBI_QueryOrder = " + json.dumps(["DataFolder", "Raw_Encounters", "Raw_IDS_Mapping",
                 "DiabetesMedicationColumns", "fnIcd9Group", "fnSpecialtyGroup", "fnBand", "fnReadCsv"] +
                 [t for t in order if t != "Alert Threshold"]), ""]
    model += [f"ref table {q(t)}" for t in order]
    model += [""]
    write(DEF / "model.tmdl", "\n".join(model))

    # expressions: parameter, staging queries, functions
    exprs = [f'expression DataFolder = "{DATA_FOLDER}" meta [IsParameterQuery = true, Type = "Text", IsParameterQueryRequired = true]',
             f"\tlineageTag: {tag('expr', 'DataFolder')}", "\tqueryGroup: Parameters", "",
             "\tannotation PBI_ResultType = Text", "", "\tannotation PBI_NavigationStepName = Navigation", ""]
    for name, rtype in [("Raw_Encounters", "Table"), ("Raw_IDS_Mapping", "Table"),
                        ("DiabetesMedicationColumns", "List"), ("fnIcd9Group", "Function"),
                        ("fnSpecialtyGroup", "Function"), ("fnBand", "Function"), ("fnReadCsv", "Function")]:
        m = (PQ / f"{name}.m").read_text()
        exprs += [f"expression {name} =", m_block(m, 3),
                  f"\tlineageTag: {tag('expr', name)}", "\tqueryGroup: 'Staging and functions'", "",
                  f"\tannotation PBI_ResultType = {rtype}", ""]
    write(DEF / "expressions.tmdl", "\n".join(exprs) + "\n")

    for t in order:
        write(DEF / "tables" / f"{t}.tmdl", table_tmdl(t, tables[t]))

    rels = [("Fact_Encounter", "Admission Type ID", "Dim_Admission_Type", "Admission Type ID"),
            ("Fact_Encounter", "Discharge Disposition ID", "Dim_Discharge_Disposition", "Discharge Disposition ID"),
            ("Fact_Encounter", "Admission Source ID", "Dim_Admission_Source", "Admission Source ID"),
            ("Fact_Encounter", "Age Band", "Dim_Age", "Age Band"),
            ("Fact_Encounter", "Primary Diagnosis Group", "Dim_Diagnosis_Group", "Diagnosis Group"),
            ("Fact_Medication", "Encounter ID", "Fact_Encounter", "Encounter ID"),
            ("Model_Threshold_Curve", "Model", "Model Selector", "Model"),
            ("Model_Feature_Importance", "Model", "Model Selector", "Model")]
    lines = []
    for ft, fc, tt, tc in rels:
        lines += [f"relationship {tag('rel', ft, fc, tt)}", f"\tfromColumn: {q(ft)}.{q(fc)}",
                  f"\ttoColumn: {q(tt)}.{q(tc)}", ""]
    write(DEF / "relationships.tmdl", "\n".join(lines))
    print("semantic model written:", len(order), "tables,", len(MEASURES), "measures,", len(rels), "relationships")

if __name__ == "__main__":
    main()
