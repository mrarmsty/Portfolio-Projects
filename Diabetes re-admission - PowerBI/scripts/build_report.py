"""
build_report.py
Writes the Power BI report definition (PBIR format) for the .pbip project.
Each page answers one business question; visuals are bound to the semantic
model written by build_semantic_model.py.
"""
from pathlib import Path
import json, shutil

ROOT = Path(__file__).resolve().parents[1]
NAME = "Diabetes_Readmission_Analysis"
RPT = ROOT / "analysis" / f"{NAME}.Report"
DEF = RPT / "definition"
S = "https://developer.microsoft.com/json-schemas/fabric/item/report/definition"
V_REPORT, V_PAGE, V_VISUAL = "3.0.0", "2.0.0", "2.4.0"

NAVY, BLUE, TEAL, AMBER, RED, GREY, LIGHT, INK = ("#1F3A5F", "#3D6A99", "#2A9D8F", "#E9A23B",
                                                   "#C0392B", "#8D99AE", "#F4F6F9", "#243B53")
W, H = 1280, 720

# ---------------------------------------------------------------- expression helpers
def lit(v):
    if isinstance(v, bool):
        return {"expr": {"Literal": {"Value": "true" if v else "false"}}}
    if isinstance(v, (int, float)):
        return {"expr": {"Literal": {"Value": f"{v}D"}}}
    return {"expr": {"Literal": {"Value": "'" + str(v).replace("'", "''") + "'"}}}

def solid(color):
    return {"solid": {"color": lit(color)}}

def C(entity, prop):
    return {"Column": {"Expression": {"SourceRef": {"Entity": entity}}, "Property": prop}}

def M(prop, entity="KPI Measures"):
    return {"Measure": {"Expression": {"SourceRef": {"Entity": entity}}, "Property": prop}}

def proj(field, display=None):
    kind = "Column" if "Column" in field else "Measure"
    ent = field[kind]["Expression"]["SourceRef"]["Entity"]
    prop = field[kind]["Property"]
    p = {"field": field, "queryRef": f"{ent}.{prop}", "nativeQueryRef": prop}
    if display:
        p["displayName"] = display
    return p

def measure_colour(measure="Readmission Rate Colour"):
    return [{"properties": {"fill": {"solid": {"color": {"expr": M(measure)}}}},
             "selector": {"data": [{"dataViewWildcard": {"matchingOption": 1}}]}}]

def title_obj(text, size=11):
    return {"title": [{"properties": {"show": lit(True), "text": lit(text), "fontSize": lit(size),
                                      "fontColor": solid(NAVY), "bold": lit(True)}}]}

def run(text, size=11, bold=False, color=INK, italic=False):
    style = {"fontSize": f"{size}pt", "color": color}
    if bold:
        style["fontWeight"] = "bold"
    if italic:
        style["fontStyle"] = "italic"
    return {"value": text, "textStyle": style}

# ---------------------------------------------------------------- visual builders
class Page:
    def __init__(self, name, display, title, subtitle):
        self.name, self.display = name, display
        self.visuals = []
        self.z = 0
        self.textbox("header", 0, 0, W, 64,
                     [[run(title, 18, True, "#FFFFFF")], [run(subtitle, 10, False, "#D9E2EC")]],
                     bg=NAVY, border=False)

    def _add(self, vname, x, y, w, h, visual, filters=None):
        self.z += 1000
        vc = {"$schema": f"{S}/visualContainer/{V_VISUAL}/schema.json",
              "name": f"{self.name}_{vname}"[:50],
              "position": {"x": x, "y": y, "z": self.z, "height": h, "width": w, "tabOrder": self.z},
              "visual": visual}
        if filters:
            vc["filterConfig"] = {"filters": filters}
        self.visuals.append(vc)

    def textbox(self, vname, x, y, w, h, paragraphs, bg="#FFFFFF", border=True):
        vis = {"visualType": "textbox",
               "objects": {"general": [{"properties": {"paragraphs": [{"textRuns": p} for p in paragraphs]}}]},
               "visualContainerObjects": {
                   "background": [{"properties": {"show": lit(True), "color": solid(bg), "transparency": lit(0)}}],
                   "border": [{"properties": {"show": lit(border), "color": solid("#D9E2EC")}}],
                   "padding": [{"properties": {"top": lit(8), "bottom": lit(8), "left": lit(14), "right": lit(14)}}]},
               "drillFilterOtherVisuals": True}
        self._add(vname, x, y, w, h, vis)

    def insight(self, vname, x, y, w, h, heading, bullets):
        paras = [[run(heading, 12, True, NAVY)]]
        for b in bullets:
            paras.append([run("- " + b, 10)])
        self.textbox(vname, x, y, w, h, paras, bg="#FFFFFF")

    def card(self, vname, x, y, w, h, measure, label=None, color=NAVY, size=22, wrap=False):
        objs = {"labels": [{"properties": {"color": solid(color), "fontSize": lit(size)}}],
                "categoryLabels": [{"properties": {"show": lit(True), "fontSize": lit(9), "color": solid("#52606D")}}]}
        if wrap:
            objs["wordWrap"] = [{"properties": {"show": lit(True)}}]
        vis = {"visualType": "card",
               "query": {"queryState": {"Values": {"projections": [proj(M(measure), label)]}}},
               "objects": objs,
               "visualContainerObjects": {"title": [{"properties": {"show": lit(False)}}]},
               "drillFilterOtherVisuals": True}
        self._add(vname, x, y, w, h, vis)

    def slicer(self, vname, x, y, w, h, field, title, single=False, default=None):
        objs = {"data": [{"properties": {"mode": lit("Dropdown")}}],
                "header": [{"properties": {"show": lit(True), "text": lit(title), "fontColor": solid(NAVY)}}]}
        if single:
            objs["selection"] = [{"properties": {"singleSelect": lit(True), "strictSingleSelect": lit(True)}}]
        if default is not None:
            ent = field["Column"]["Expression"]["SourceRef"]["Entity"]
            prop = field["Column"]["Property"]
            value = f"{default}D" if isinstance(default, (int, float)) else f"'{default}'"
            objs["general"] = [{"properties": {"filter": {"filter": {
                "Version": 2, "From": [{"Name": "s", "Entity": ent, "Type": 0}],
                "Where": [{"Condition": {"In": {"Expressions": [{"Column": {"Expression": {"SourceRef": {"Source": "s"}}, "Property": prop}}],
                                                "Values": [[{"Literal": {"Value": value}}]]}}}]}}}}]
        vis = {"visualType": "slicer",
               "query": {"queryState": {"Values": {"projections": [proj(field)]}}},
               "objects": objs, "drillFilterOtherVisuals": True}
        self._add(vname, x, y, w, h, vis)

    def chart(self, vname, vtype, x, y, w, h, roles, title, sort=None, colour_measure=False,
              labels=True, label_fmt=None, filters=None, series_colours=None, extra_objects=None):
        qs = {role: {"projections": [proj(f) for f in fields]} for role, fields in roles.items()}
        query = {"queryState": qs}
        if sort:
            field, direction = sort
            query["sortDefinition"] = {"sort": [{"field": field, "direction": direction}], "isDefaultSort": True}
        objs = {}
        if labels:
            objs["labels"] = [{"properties": {"show": lit(True), "fontSize": lit(9), "color": solid(INK)}}]
        if colour_measure:
            objs["dataPoint"] = measure_colour()
        elif series_colours is None and vtype in ("clusteredBarChart", "clusteredColumnChart"):
            objs["dataPoint"] = [{"properties": {"fill": solid(BLUE)}}]
        if extra_objects:
            objs.update(extra_objects)
        vis = {"visualType": vtype, "query": query, "objects": objs,
               "visualContainerObjects": title_obj(title), "drillFilterOtherVisuals": True}
        self._add(vname, x, y, w, h, vis, filters)

    def table(self, vname, vtype, x, y, w, h, roles, title, sort=None, cf=None):
        qs = {role: {"projections": [proj(f) for f in fields]} for role, fields in roles.items()}
        query = {"queryState": qs}
        if sort:
            query["sortDefinition"] = {"sort": [{"field": sort[0], "direction": sort[1]}], "isDefaultSort": True}
        objs = {"grid": [{"properties": {"textSize": lit(9)}}],
                "columnHeaders": [{"properties": {"fontColor": solid("#FFFFFF"), "backColor": solid(NAVY), "fontSize": lit(9)}}]}
        if cf:   # conditional background colour from a measure for one value column
            meas_field, colour_measure = cf
            objs["values"] = [{"properties": {"backColor": {"solid": {"color": {"expr": M(colour_measure)}}},
                                              "fontColor": solid("#FFFFFF")},
                               "selector": {"data": [{"dataViewWildcard": {"matchingOption": 1}}],
                                            "metadata": f"KPI Measures.{meas_field}"}}]
        vis = {"visualType": vtype, "query": query, "objects": objs,
               "visualContainerObjects": title_obj(title), "drillFilterOtherVisuals": True}
        self._add(vname, x, y, w, h, vis)


def categorical_filter(name, entity, prop, values):
    return {"name": name, "field": C(entity, prop), "type": "Categorical",
            "filter": {"Version": 2, "From": [{"Name": "f", "Entity": entity, "Type": 0}],
                       "Where": [{"Condition": {"In": {
                           "Expressions": [{"Column": {"Expression": {"SourceRef": {"Source": "f"}}, "Property": prop}}],
                           "Values": [[{"Literal": {"Value": f"'{v}'"}}] for v in values]}}}]},
            "howCreated": "User"}

# ---------------------------------------------------------------- fields
FE, RATE, COL = "Fact_Encounter", M("30-Day Readmission Rate"), M("Readmission Rate Colour")
ELIG, READ30 = M("Eligible Encounters"), M("30-Day Readmissions")

def kpi_row(page, y, measures, h=78, x0=16, total=1248, gap=10, size=20):
    w = (total - gap * (len(measures) - 1)) / len(measures)
    for i, (m, lab) in enumerate(measures):
        page.card(f"kpi{i}", round(x0 + i * (w + gap)), y, round(w), h, m, lab, size=size)

pages = []

# ================================================================ 1 Executive overview
p = Page("p1", "1 Executive Overview", "Diabetes Readmission Risk - Executive Overview",
         "101,766 inpatient encounters of diabetic patients, 130 US hospitals (1999-2008). "
         "Readmission rates exclude 2,423 discharges to death or hospice.")
kpi_row(p, 74, [("Encounters", None), ("Patients", None), ("30-Day Readmission Rate", None),
                ("30-Day Readmissions", None), ("Any Readmission Rate", None), ("Average Length of Stay", "Average Length of Stay (days)")])
p.chart("inp", "clusteredColumnChart", 16, 162, 400, 266,
        {"Category": [C(FE, "Prior Inpatient Band")], "Y": [RATE]},
        "30-day readmission rate by inpatient visits in the prior year", colour_measure=True)
p.chart("dis", "clusteredBarChart", 428, 162, 440, 266,
        {"Category": [C("Dim_Discharge_Disposition", "Discharge Group")], "Y": [RATE]},
        "30-day readmission rate by discharge destination", sort=(RATE, "Descending"), colour_measure=True)
p.chart("age", "lineClusteredColumnComboChart", 880, 162, 384, 266,
        {"Category": [C("Dim_Age", "Age Band")], "Y": [ELIG], "Y2": [RATE]},
        "Encounter volume (columns) and 30-day rate (line) by age", labels=False,
        extra_objects={"dataPoint": [{"properties": {"fill": solid("#BCCCDC")}}]})
p.chart("status", "clusteredBarChart", 16, 440, 400, 264,
        {"Category": [C(FE, "Readmission Status")], "Y": [M("Share of Encounters")]},
        "Readmission outcome of each encounter (all encounters)")
p.insight("msg", 428, 440, 836, 264, "What management needs to know", [
    "About 1 in 9 eligible discharges (11.4%) returns within 30 days; 47% return at some point.",
    "Prior hospital use is the strongest signal: the rate climbs from 8.6% with no inpatient visit in the "
    "prior year to 37% with five or more.",
    "Where patients go after discharge matters: transfers to rehab / other inpatient care readmit at 26% "
    "(2.3x the overall rate); routine home discharges sit below it at 9.3%.",
    "Across adult age bands, admission types and diagnosis groups the rate moves only between about 10% and 13%.",
    "A Random Forest risk score ranks patients usefully (ROC-AUC 0.67): the top risk decile readmits at 27%, "
    "2.5x the average, but the model is a triage aid, not a diagnostic test.",
    "See pages 2-7 for the evidence behind each point and the alert-threshold trade-off."])
pages.append(p)

# ================================================================ 2 Readmission patterns
p = Page("p2", "2 Readmission Patterns", "Where are 30-day readmissions concentrated?",
         "Objective 1: frequency of readmission and variation by age, admission type, admission source and discharge disposition.")
p.slicer("s_age", 16, 72, 200, 56, C("Dim_Age", "Age Group"), "Age group")
p.slicer("s_gen", 226, 72, 180, 56, C(FE, "Gender"), "Gender")
p.slicer("s_race", 416, 72, 200, 56, C(FE, "Race"), "Race")
p.card("headline", 628, 72, 636, 56, "Headline Readmission Text", " ", size=13, wrap=True)
p.chart("age", "clusteredColumnChart", 16, 138, 400, 270,
        {"Category": [C("Dim_Age", "Age Band")], "Y": [RATE]},
        "30-day readmission rate by age band", colour_measure=True)
p.chart("adm", "clusteredBarChart", 428, 138, 410, 270,
        {"Category": [C("Dim_Admission_Type", "Admission Type Group")], "Y": [RATE]},
        "30-day readmission rate by admission type", sort=(RATE, "Descending"), colour_measure=True)
p.chart("src", "clusteredBarChart", 850, 138, 414, 270,
        {"Category": [C("Dim_Admission_Source", "Admission Source Group")], "Y": [RATE]},
        "30-day readmission rate by admission source", sort=(RATE, "Descending"), colour_measure=True)
p.table("mx", "pivotTable", 16, 420, 860, 284,
        {"Rows": [C("Dim_Discharge_Disposition", "Discharge Group"), C("Dim_Discharge_Disposition", "Discharge Disposition")],
         "Values": [ELIG, READ30, RATE, M("Rate Difference vs Overall (pp)"), M("Share of 30-Day Readmissions")]},
        "Discharge disposition detail (expand a group to see individual codes)",
        sort=(RATE, "Descending"), cf=("30-Day Readmission Rate", "Readmission Rate Colour"))
p.insight("msg", 888, 420, 376, 284, "Reading this page", [
    "Colour key: red = at least 1.2x the overall rate, amber = 1.05x, teal = 0.85x or lower.",
    "Discharge destination separates risk far more than age or admission route.",
    "Rehab / other inpatient care has the highest rate; Expired / hospice is excluded from rates by design.",
    "Emergency and urgent admissions sit close to the overall rate, so admission type alone is a weak screen.",
    "Use the slicers to test whether patterns hold within age groups and demographics."])
pages.append(p)

# ================================================================ 3 Prior visits
p = Page("p3", "3 Prior Visits and Readmission", "Does previous hospital use predict readmission?",
         "Objective 4: association between inpatient, emergency and outpatient visits in the prior year and 30-day readmission.")
p.slicer("s_age", 16, 72, 200, 56, C("Dim_Age", "Age Group"), "Age group")
p.slicer("s_adm", 226, 72, 220, 56, C("Dim_Admission_Type", "Admission Type Group"), "Admission type")
p.slicer("s_dis", 456, 72, 260, 56, C("Dim_Discharge_Disposition", "Discharge Group"), "Discharge group")
kpi_row(p, 72, [("Rate - No Prior Inpatient Visit", "Rate with no prior inpatient visit"),
                ("Rate - 3+ Prior Inpatient Visits", "Rate with 3+ prior inpatient visits"),
                ("Prior Inpatient Risk Multiple", "Risk multiple (3+ vs none)")], h=56, x0=728, total=536, size=16)
p.chart("inp", "clusteredColumnChart", 16, 138, 410, 280,
        {"Category": [C(FE, "Prior Inpatient Band")], "Y": [RATE]},
        "Rate by inpatient visits in prior year", colour_measure=True)
p.chart("emg", "clusteredColumnChart", 436, 138, 410, 280,
        {"Category": [C(FE, "Prior Emergency Band")], "Y": [RATE]},
        "Rate by emergency visits in prior year", colour_measure=True)
p.chart("out", "clusteredColumnChart", 856, 138, 408, 280,
        {"Category": [C(FE, "Prior Outpatient Band")], "Y": [RATE]},
        "Rate by outpatient visits in prior year", colour_measure=True)
p.table("mx", "pivotTable", 16, 430, 700, 274,
        {"Rows": [C(FE, "Prior Inpatient Band")], "Columns": [C(FE, "Prior Emergency Band")], "Values": [RATE]},
        "30-day rate: prior inpatient visits (rows) x prior emergency visits (columns)",
        cf=("30-Day Readmission Rate", "Readmission Rate Colour"))
p.insight("msg", 728, 430, 536, 274, "Finding", [
    "The relationship is strong and dose-dependent: each extra prior inpatient visit raises the odds of "
    "30-day readmission by about 31% (logistic regression, other factors held constant).",
    "Emergency visits add risk on top of inpatient history; outpatient visits add a smaller amount.",
    "Prior inpatient visits is the single most important model feature (largest drop in ROC-AUC when removed).",
    "Practical use: a prior-year inpatient count is available at admission, so it can trigger early "
    "discharge planning before any model is deployed.",
    "This is an association in observational data, not proof that prior visits cause readmission."])
pages.append(p)

# ================================================================ 4 Utilisation
p = Page("p4", "4 Healthcare Utilisation", "How do diabetic patients use hospital resources?",
         "Objective 3: length of stay, procedures, lab tests and medications across patient groups, and their link to readmission.")
p.slicer("s_age", 16, 72, 190, 56, C("Dim_Age", "Age Group"), "Age group")
p.slicer("s_gen", 214, 72, 160, 56, C(FE, "Gender"), "Gender")
p.slicer("s_st", 382, 72, 220, 56, C(FE, "Readmission Status"), "Readmission status")
kpi_row(p, 72, [("Average Length of Stay", "Avg stay (days)"), ("Total Bed Days", None),
                ("Average Medications", "Avg medications"), ("Average Procedures", "Avg procedures"),
                ("Long Stay Share (8+ days)", "Stays of 8+ days")], h=56, x0=612, total=652, size=15)
p.chart("los_adm", "clusteredBarChart", 16, 138, 410, 270,
        {"Category": [C("Dim_Admission_Type", "Admission Type Group")], "Y": [M("Average Length of Stay")]},
        "Average length of stay by admission type (days)", sort=(M("Average Length of Stay"), "Descending"))
p.chart("los_dx", "clusteredBarChart", 436, 138, 410, 270,
        {"Category": [C("Dim_Diagnosis_Group", "Diagnosis Group")], "Y": [M("Average Length of Stay")]},
        "Average length of stay by primary diagnosis group (days)", sort=(M("Average Length of Stay"), "Descending"))
p.chart("proc", "clusteredBarChart", 856, 138, 408, 270,
        {"Category": [C(FE, "Specialty Group")], "Y": [M("Average Procedures")]},
        "Average procedures by admitting specialty", sort=(M("Average Procedures"), "Descending"))
p.chart("meds", "lineClusteredColumnComboChart", 16, 420, 410, 284,
        {"Category": [C(FE, "Medications Band")], "Y": [ELIG], "Y2": [RATE]},
        "Medications during stay: volume (columns) and 30-day rate (line)", labels=False,
        extra_objects={"dataPoint": [{"properties": {"fill": solid("#BCCCDC")}}]})
p.table("mx", "pivotTable", 436, 420, 520, 284,
        {"Rows": [C("Dim_Age", "Age Group")],
         "Values": [M("Encounters"), M("Average Length of Stay"), M("Average Medications"),
                    M("Average Procedures"), M("Average Lab Procedures"), M("Average Diagnoses"), RATE]},
        "Utilisation profile by age group")
p.insight("msg", 966, 420, 298, 284, "Finding", [
    "Readmitted patients stayed slightly longer on their index stay (4.8 vs 4.3 days) and received more medications (16.9 vs 15.9).",
    "Length of stay rises steadily with age (2.6 days under 10 to 4.8 days at 80-90) and is longest for neoplasm and injury admissions.",
    "Radiology, cardiology and surgery admissions carry the most procedures, yet procedure count shows no link to readmission (p = 0.15).",
    "Utilisation measures describe workload; they are weak predictors on their own."])
pages.append(p)

# ================================================================ 5 Risk drivers
p = Page("p5", "5 Risk Drivers", "Which characteristics are associated with readmission?",
         "Objective 2: chi-square / Mann-Whitney tests on 99,343 eligible encounters and adjusted odds ratios from logistic regression.")
p.table("assoc", "tableEx", 16, 72, 700, 400,
        {"Values": [C("Stat_Association_Tests", "Variable"), C("Stat_Association_Tests", "Test"),
                    C("Stat_Association_Tests", "Effect Measure"), C("Stat_Association_Tests", "Effect Size"),
                    C("Stat_Association_Tests", "P Value (display)"), C("Stat_Association_Tests", "Highest-Rate Group")]},
        "Unadjusted association with 30-day readmission (ranked by effect size)",
        sort=(C("Stat_Association_Tests", "Effect Size"), "Descending"))
p.chart("or", "clusteredBarChart", 728, 72, 536, 632,
        {"Category": [C("Model_Odds_Ratios", "Term")], "Series": [C("Model_Odds_Ratios", "Direction")],
         "Y": [M("Odds Ratio")]},
        "Adjusted odds ratios (significant, OR >= 1.15 or <= 0.85); 1.0 = no effect",
        sort=(M("Odds Ratio"), "Descending"), series_colours=True,
        filters=[categorical_filter("orFlag", "Model_Odds_Ratios", "Chart Flag", ["Yes"])])
p.insight("msg", 16, 484, 700, 220, "How to read the evidence", [
    "With ~99,000 encounters almost every variable is 'significant'; effect size shows what matters in practice.",
    "Prior inpatient visits and discharge destination have the largest effects. Gender, diabetes medication count "
    "and number of procedures show no association (p > 0.05).",
    "Odds ratios are adjusted for all other model variables. Discharge to rehab / other inpatient care: OR 3.3; "
    "each prior inpatient visit: OR 1.31.",
    "HbA1c > 7 or > 8 shows lower odds than 'not measured'; testing may mark more engaged care. It does not mean high HbA1c is protective.",
    "All results are associations in observational data, not causal effects."])
pages.append(p)

# ================================================================ 6 Predictive model
p = Page("p6", "6 Predictive Model", "Can we predict 30-day readmission?",
         "Objective 5: logistic regression vs Random Forest, trained on 80% of patients and tested on a held-out 20% (19,802 encounters).")
p.table("metrics", "tableEx", 16, 72, 760, 150,
        {"Values": [C("Model_Metrics", "Model"), C("Model_Metrics", "CV ROC-AUC"), C("Model_Metrics", "Test ROC-AUC"),
                    C("Model_Metrics", "Test PR-AUC"), C("Model_Metrics", "Precision"), C("Model_Metrics", "Recall"),
                    C("Model_Metrics", "Specificity"), C("Model_Metrics", "Alert Rate")]},
        "Model performance on the test set (precision and recall when the top 20% of risk scores are flagged)",
        sort=(C("Model_Metrics", "Model"), "Ascending"))
p.slicer("s_model", 788, 72, 476, 56, C("Model Selector", "Model"), "Model for feature importance", single=True)
p.chart("roc", "lineChart", 16, 234, 450, 470,
        {"Category": [C("Model_ROC_Curve", "False Positive Rate")], "Series": [C("Model_ROC_Curve", "Curve")],
         "Y": [M("ROC True Positive Rate")]},
        "ROC curve: true positive rate vs false positive rate (test set)", labels=False)
p.chart("decile", "clusteredColumnChart", 478, 234, 298, 470,
        {"Category": [C(FE, "Risk Decile")], "Y": [M("Observed Test Readmission Rate")]},
        "Observed 30-day rate by Random Forest risk decile (test set)",
        extra_objects={"dataPoint": [{"properties": {"fill": solid(NAVY)}}]})
p.chart("imp", "clusteredBarChart", 788, 138, 476, 360,
        {"Category": [C("Model_Feature_Importance", "Feature")], "Y": [M("Feature Importance (AUC Drop)")]},
        "Permutation importance: drop in test ROC-AUC when a feature is shuffled",
        sort=(M("Feature Importance (AUC Drop)"), "Descending"))
p.insight("msg", 788, 510, 476, 194, "Finding", [
    "Random Forest is slightly better than logistic regression (ROC-AUC 0.674 vs 0.663); both beat a "
    "prior-inpatient-visit rule (0.602).",
    "Discrimination is moderate, in line with published results on this dataset. Risk deciles separate well: "
    "4% in decile 1 vs 27% in decile 10.",
    "Two features carry most of the signal: prior inpatient visits and discharge destination."])
pages.append(p)

# ================================================================ 7 Threshold simulator
p = Page("p7", "7 Alert Threshold Simulator", "How many alerts, how many readmissions caught?",
         "Choose a model and a risk threshold to see the balance between catching readmissions and generating false alarms (test set).")
p.slicer("s_model", 16, 72, 250, 56, C("Model Selector", "Model"), "Model", single=True, default="Random Forest")
p.slicer("s_thr", 276, 72, 200, 56, C("Alert Threshold", "Alert Threshold"), "Risk threshold", single=True, default=0.15)
p.card("narr", 488, 72, 776, 56, "Threshold Narrative", " ", size=10, wrap=True, color=INK)
kpi_row(p, 140, [("Flagged Encounters", "Alerts raised"), ("True Positives", "Readmissions caught"),
                 ("False Negatives", "Readmissions missed"), ("False Positives", "False alarms"),
                 ("Precision", "Precision (alerts that are right)"), ("Recall", "Recall (readmissions caught)"),
                 ("Alert Rate", "Share of discharges flagged")], h=70, size=18)
p.chart("curve", "lineChart", 16, 222, 760, 482,
        {"Category": [C("Model_Threshold_Curve", "Threshold")],
         "Y": [M("Curve Recall"), M("Curve Precision"), M("Curve Alert Rate")]},
        "Recall, precision and alert rate across thresholds (selected model)", labels=False)
p.textbox("cm_t", 788, 222, 476, 34, [[run("Confusion matrix at the selected threshold", 11, True, NAVY)]])
p.card("cm_tp", 788, 262, 234, 96, "True Positives", "Flagged and readmitted", color=TEAL)
p.card("cm_fp", 1030, 262, 234, 96, "False Positives", "Flagged, not readmitted", color=AMBER)
p.card("cm_fn", 788, 366, 234, 96, "False Negatives", "Not flagged, readmitted", color=RED)
p.card("cm_tn", 1030, 366, 234, 96, "True Negatives", "Not flagged, not readmitted", color=GREY)
p.insight("msg", 788, 470, 476, 234, "Choosing a threshold", [
    "No single threshold is 'correct'; it should match the capacity of the discharge-planning or follow-up team.",
    "The default 0.5 cut-off flags almost nobody: with an 11% base rate, predicted risks rarely exceed 50%.",
    "Flagging the top 20% (threshold about 15% for Random Forest) catches about 39% of readmissions; "
    "about 1 in 5 alerts is a true readmission (3.6 false alarms per readmission caught).",
    "Lower thresholds catch more readmissions but the false-alarm workload rises quickly."])
pages.append(p)

# ================================================================ 8 About
p = Page("p8", "8 Data and Method Notes", "About this report: data, definitions and limitations",
         "Read before quoting any number from this report.")
p.insight("data", 16, 72, 616, 300, "Data", [
    "Source: 'Diabetes 130-US Hospitals for Years 1999-2008' (Strack et al., 2014; UCI Machine Learning Repository). "
    "Public, de-identified research data; not from any specific organisation.",
    "Unit of analysis: hospital encounter (101,766 rows, 71,518 patients). Encounters are 1-14 day inpatient stays "
    "with a diabetes diagnosis, lab tests and medications.",
    "No admission dates are provided, so trends over time cannot be analysed.",
    "Weight (97% missing) was dropped; payer code (40% missing) and specialty (49% missing) kept with a 'Not recorded' label.",
    "IDS_mapping descriptions are joined to admission type, source and discharge IDs."])
p.insight("def", 644, 72, 620, 300, "Definitions", [
    "30-Day Readmission Rate = encounters readmitted '<30' days / eligible encounters.",
    "Eligible encounter = discharge disposition is not death or hospice (codes 11, 13, 14, 19, 20, 21).",
    "Prior visits = outpatient, emergency and inpatient visits in the year before the encounter.",
    "Diagnosis groups follow ICD-9 chapters used in the original study (e.g. Circulatory 390-459, 785).",
    "Model metrics are calculated on patients never seen in training (patient-grouped 80/20 split)."])
p.insight("lim", 16, 384, 616, 320, "Limitations", [
    "Observational data: associations are not causal effects.",
    "Patients with several encounters contribute several rows; rates are encounter-based.",
    "The readmission flag does not say whether the readmission was planned, preventable or diabetes-related.",
    "Data are from 1999-2008 US hospitals; care practice and coding (ICD-9) have since changed.",
    "Model probabilities are produced in Python and imported; Power BI recalculates the confusion matrix from them."])
kpi_row(p, 384, [("Encounters", None), ("Excluded Encounters (Expired or Hospice)", "Excluded (death / hospice)"),
                 ("Crude 30-Day Rate (All Encounters)", "Crude rate, all encounters")], h=80, x0=644, total=620, size=18)
p.table("dx", "tableEx", 644, 476, 620, 228,
        {"Values": [C("Dim_Diagnosis_Group", "Diagnosis Group"), C("Dim_Diagnosis_Group", "ICD9 Range"),
                    M("Encounters"), RATE]},
        "Primary diagnosis groups (ICD-9)", sort=(C("Dim_Diagnosis_Group", "Diagnosis Group"), "Ascending"))
pages.append(p)

# ================================================================ write files
THEME = {
    "name": "Diabetes Readmission",
    "dataColors": [NAVY, TEAL, AMBER, RED, BLUE, GREY, "#6C5B7B", "#F2C14E"],
    "background": "#FFFFFF", "foreground": INK, "tableAccent": NAVY,
    "good": TEAL, "neutral": AMBER, "bad": RED,
    "textClasses": {"title": {"fontFace": "Segoe UI Semibold", "fontSize": 11, "color": NAVY},
                    "label": {"fontFace": "Segoe UI", "fontSize": 9, "color": INK}},
    "visualStyles": {
        "*": {"*": {"background": [{"show": True, "color": {"solid": {"color": "#FFFFFF"}}, "transparency": 0}],
                    "border": [{"show": True, "color": {"solid": {"color": "#D9E2EC"}}, "radius": 6}],
                    "dropShadow": [{"show": False}]}},
        "page": {"*": {"background": [{"color": {"solid": {"color": LIGHT}}, "transparency": 0}]}}},
}

def dump(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding="utf-8")

def main():
    if RPT.exists():
        shutil.rmtree(RPT)
    dump(RPT / "definition.pbir", {
        "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definitionProperties/2.0.0/schema.json",
        "version": "4.0", "datasetReference": {"byPath": {"path": f"../{NAME}.SemanticModel"}}})
    dump(DEF / "version.json", {"$schema": f"{S}/versionMetadata/1.0.0/schema.json", "version": "2.0.0"})
    dump(DEF / "report.json", {
        "$schema": f"{S}/report/{V_REPORT}/schema.json",
        "themeCollection": {"customTheme": {"name": "DiabetesReadmissionTheme.json",
                                            "reportVersionAtImport": {"visual": V_VISUAL, "report": V_REPORT, "page": V_PAGE},
                                            "type": "RegisteredResources"}},
        "resourcePackages": [{"name": "RegisteredResources", "type": "RegisteredResources",
                              "items": [{"name": "DiabetesReadmissionTheme.json", "path": "DiabetesReadmissionTheme.json",
                                         "type": "CustomTheme"}]}],
        "settings": {"useStylableVisualContainerHeader": True, "defaultDrillFilterOtherVisuals": True,
                     "exportDataMode": "AllowSummarized"}})
    dump(RPT / "StaticResources" / "RegisteredResources" / "DiabetesReadmissionTheme.json", THEME)
    dump(DEF / "pages" / "pages.json", {"$schema": f"{S}/pagesMetadata/1.0.0/schema.json",
                                        "pageOrder": [pg.name for pg in pages], "activePageName": pages[0].name})
    for pg in pages:
        dump(DEF / "pages" / pg.name / "page.json", {
            "$schema": f"{S}/page/{V_PAGE}/schema.json", "name": pg.name, "displayName": pg.display,
            "displayOption": "FitToPage", "height": H, "width": W,
            "objects": {"background": [{"properties": {"color": solid(LIGHT), "transparency": lit(0)}}]}})
        names = set()
        for v in pg.visuals:
            assert v["name"] not in names, v["name"]
            names.add(v["name"])
            pos = v["position"]
            assert pos["x"] + pos["width"] <= W + 1 and pos["y"] + pos["height"] <= H + 1, (v["name"], pos)
            dump(DEF / "pages" / pg.name / "visuals" / v["name"] / "visual.json", v)
    print("report written:", len(pages), "pages,", sum(len(p.visuals) for p in pages), "visuals")

if __name__ == "__main__":
    main()
