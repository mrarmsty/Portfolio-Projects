// Builds documentation/Analyst_Technical_Report.docx
// Run: node scripts/build_analyst_report.js   (from the repository root)
const fs = require("fs");
const path = require("path");
const {
  Document, Packer, Paragraph, TextRun, HeadingLevel, Table, TableRow, TableCell, WidthType,
  ShadingType, AlignmentType, LevelFormat, ImageRun, PageBreak, Footer, PageNumber, TableOfContents, BorderStyle,
} = require("docx");

const ROOT = path.resolve(__dirname, "..");
const IMG = path.join(ROOT, "outputs", "charts");
const NAVY = "1F3A5F";
const W = 9026; // A4 text width in DXA with 1" margins

const p = (text, opts = {}) => new Paragraph({ spacing: { after: 120 }, ...opts,
  children: (Array.isArray(text) ? text : [text]).map(t => typeof t === "string" ? new TextRun(t) : t) });
const b = (t) => new TextRun({ text: t, bold: true });
const h1 = (t) => new Paragraph({ heading: HeadingLevel.HEADING_1, children: [new TextRun(t)] });
const h2 = (t) => new Paragraph({ heading: HeadingLevel.HEADING_2, children: [new TextRun(t)] });
const h3 = (t) => new Paragraph({ heading: HeadingLevel.HEADING_3, children: [new TextRun(t)] });
const bullet = (t) => new Paragraph({ numbering: { reference: "bul", level: 0 }, spacing: { after: 60 },
  children: (Array.isArray(t) ? t : [t]).map(x => typeof x === "string" ? new TextRun(x) : x) });
const code = (t) => new Paragraph({ spacing: { after: 0 }, shading: { type: ShadingType.CLEAR, fill: "F3F5F8" },
  children: [new TextRun({ text: t, font: "Consolas", size: 17 })] });
const codeBlock = (txt) => txt.split("\n").map(code).concat([p("")]);

function table(header, rows, widths) {
  const total = widths.reduce((a, c) => a + c, 0);
  const scale = W / total; const ws = widths.map(x => Math.floor(x * scale));
  const border = { style: BorderStyle.SINGLE, size: 4, color: "C9D2DC" };
  const borders = { top: border, bottom: border, left: border, right: border };
  const cell = (t, i, head) => new TableCell({ width: { size: ws[i], type: WidthType.DXA }, borders,
    shading: head ? { type: ShadingType.CLEAR, fill: NAVY } : undefined,
    margins: { top: 50, bottom: 50, left: 80, right: 80 },
    children: [new Paragraph({ children: [new TextRun({ text: String(t), bold: head, size: 17, color: head ? "FFFFFF" : "222222" })] })] });
  return new Table({ width: { size: ws.reduce((a, c) => a + c, 0), type: WidthType.DXA }, columnWidths: ws,
    rows: [new TableRow({ tableHeader: true, children: header.map((t, i) => cell(t, i, true)) }),
           ...rows.map(r => new TableRow({ children: r.map((t, i) => cell(t, i, false)) }))] });
}
const gap = () => p("");
function image(file, caption, h = 338) {
  const f = path.join(IMG, file);
  if (!fs.existsSync(f)) throw new Error("missing image " + file);
  return [new Paragraph({ alignment: AlignmentType.CENTER, keepNext: true, children: [new ImageRun({ type: "png", data: fs.readFileSync(f),
            transformation: { width: h === 338 ? 600 : 470, height: h } })] }),
          new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 200 },
            children: [new TextRun({ text: caption, italics: true, size: 18, color: "52606D" })] })];
}

// ------------------------------------------------------------------ content
const S = [];
S.push(new Paragraph({ spacing: { before: 2400, after: 200 }, children: [new TextRun({ text: "Diabetes Readmission Risk Analytics", bold: true, size: 52, color: NAVY })] }));
S.push(p([new TextRun({ text: "Analyst's Technical Report - Power BI end-to-end project", size: 30, color: "3D6A99" })]));
S.push(p([new TextRun({ text: "Primary tool: Power BI Desktop (Power Query, DAX, PBIP). Supporting tool: Python (statistics and modelling).", size: 22 })]));
S.push(p([new TextRun({ text: "Dataset: Diabetes 130-US Hospitals 1999-2008 (UCI, public, de-identified). Business scenario is illustrative.", size: 22, color: "52606D" })]));
S.push(p([new TextRun({ text: "November 2026", size: 22, color: "52606D" })]));
S.push(new Paragraph({ children: [new PageBreak()] }));

// 1
S.push(h1("1. Project overview"));
S.push(table(["Item", "Description"], [
  ["Project title", "Diabetes Readmission Risk Analytics"],
  ["Business scenario", "A healthcare organisation wants to understand hospital readmission patterns among patients diagnosed with diabetes. Repeated admissions increase cost, put pressure on beds and staff, and signal gaps in care coordination."],
  ["Business problem", "Management does not know what share of diabetic discharges return within 30 days, where that risk is concentrated, whether recent hospital use is a reliable warning sign, or whether a risk score could direct limited follow-up resources without overwhelming staff."],
  ["Purpose", "Quantify 30-day readmission, identify associated patient and encounter characteristics, describe utilisation, and build and evaluate a readmission classification framework that managers can tune."],
  ["Scope", "101,766 inpatient encounters (71,518 patients, 130 US hospitals, 1999-2008). Readmission rates use 99,343 eligible encounters (excludes death and hospice discharges). No dates, so no trend analysis."],
  ["Intended users", "Hospital management, care-coordination and discharge-planning leads, quality improvement team."],
  ["Tools", "Power BI Desktop October 2026 (Power Query M, tabular model in TMDL, DAX, PBIR report). Python 3 (pandas, SciPy, statsmodels, scikit-learn) for statistical tests and models only."],
  ["Success criteria", "Every objective answered with evidence; numbers reconcile across Power BI, Python and documents; report opens and refreshes in Power BI Desktop; limitations stated."],
], [1, 3]));

// 2
S.push(h1("2. Business objectives and analytical questions"));
S.push(p("The six objectives and thirteen questions supplied were translated into analytical requirements as follows."));
S.push(table(["Objective", "Analytical question", "Data required", "Analysis", "Output"], [
  ["1 Frequency of readmission", "What proportion is readmitted within 30 days? How does it vary by age, admission type, discharge?", "readmitted, eligibility flag, age, admission/discharge IDs", "Eligibility-aware rate KPIs; group rates vs overall benchmark", "Pages 1-2, measures 30-Day Readmission Rate, Rate Difference vs Overall"],
  ["2 Associated characteristics", "Which characteristics are associated with readmission?", "All patient/encounter attributes", "Chi-square + Cramer's V; Mann-Whitney + rank-biserial; logistic regression odds ratios", "Page 5; association_tests.csv; lr_odds_ratios.csv"],
  ["3 Utilisation", "How does LOS vary? Who has more procedures? How do medications relate to readmission? What is linked to longer stays?", "time_in_hospital, procedures, labs, medications, diagnoses", "Averages by group; medication band vs rate; LOS by admission type, diagnosis, age", "Page 4"],
  ["4 Prior visits", "How do previous inpatient/emergency/outpatient visits relate to readmission?", "number_inpatient, number_emergency, number_outpatient", "Banded rates, cross-tab heat map, adjusted OR, permutation importance", "Page 3"],
  ["5 Predictive model", "Can we predict 30-day readmission? Which variables matter? LR vs RF? Alerts vs false alarms?", "All pre-discharge features, patient_nbr for grouping", "Patient-grouped split, 5-fold grouped CV, ROC/PR-AUC, Brier, permutation importance, threshold curve", "Pages 6-7; model output CSVs; DAX confusion matrix"],
  ["6 Present to management", "What should management do?", "All of the above", "Insight panels, recommendations, README", "Report, this document, README"],
], [1.2, 2, 1.6, 2, 1.6]));
S.push(gap());
S.push(p([b("Data gaps identified early: "), "no admission or discharge dates (no time-based KPIs, no time-to-readmission); no cost data (cost impact cannot be quantified); the readmission flag does not distinguish planned from unplanned or preventable readmissions."]));

// 3
S.push(h1("3. Dataset overview"));
S.push(table(["Property", "Value"], [
  ["Source file", "diabetic_data.xlsx - sheets diabetic_data and IDS_mapping"],
  ["Records", "101,766 encounters; 71,518 distinct patients (16,773 with more than one encounter)"],
  ["Variables", "50: identifiers (2), demographics (4), admission/discharge codes (3), utilisation counts (8), diagnoses (3 ICD-9 codes + count), lab results (2), 23 medication status columns, change, diabetesMed, readmitted"],
  ["Keys", "encounter_id unique (0 duplicates) - primary key; patient_nbr - patient key; three code columns are foreign keys to IDS_mapping"],
  ["Outcome", "readmitted: NO 54,864; >30 35,545; <30 11,357"],
  ["Lookup sheet", "IDS_mapping: three lookup tables stacked vertically (admission type 8 codes, discharge disposition 30 codes, admission source 25 codes); some codes have NULL descriptions"],
  ["Limitations", "No dates; weight 96.9% missing; payer 39.6%; specialty 49.1%; HbA1c not measured 83.3%; data are 1999-2008 and ICD-9 coded"],
], [1, 3]));
S.push(p("A full variable-level data dictionary is in documentation/data_dictionary.md."));

// 4
S.push(h1("4. Data quality assessment"));
S.push(table(["Dimension", "Finding", "Impact / action"], [
  ["Completeness", "'?' used for missing in race (2.2%), payer (39.6%), specialty (49.1%), diag_1/2/3 (21 / 358 / 1,423). weight 96.9% missing. 'None' in lab tests = test not done.", "Weight dropped. Others kept with explicit 'Not recorded'. 'None' treated as a meaningful 'Not measured' category."],
  ["Uniqueness", "encounter_id unique. patient_nbr repeats for 16,773 patients.", "Encounter grain kept; model split grouped by patient to avoid leakage."],
  ["Validity", "gender 'Unknown/Invalid' (3 rows). Mapping codes with NULL descriptions (admission type 6, source 17, discharge 18).", "Recoded 'Unknown'; codes labelled 'Not recorded' and flagged as assumptions."],
  ["Consistency", "Diagnosis codes stored as integers, decimals and text (V/E codes) in the same column. Age stored as '[70-80)'.", "Converted to text before processing; age labels cleaned and sorted."],
  ["Referential integrity", "All admission type, source and discharge codes in the fact exist in IDS_mapping.", "Verified: 0 orphan keys."],
  ["Constant columns", "examide and citoglipton are always 'No'.", "Removed."],
  ["Outliers", "Max 76 emergency visits, 42 outpatient, 21 inpatient, 81 medications.", "Plausible for very high users; kept and handled with bands."],
  ["Measurement", "'readmitted' captures any readmission, not cause or plannedness. Death/hospice discharges cannot be readmitted.", "2,423 death/hospice encounters excluded from rate denominators via a flag."],
], [1, 2.2, 2.2]));

// 5
S.push(h1("5. Data cleaning and preparation"));
S.push(p("All cleaning is implemented in Power Query (the production layer of the Power BI model). An identical pandas implementation (scripts/01_reference_preparation.py) exports the cleaned CSV files and provides an independent check of Power BI totals. The raw file is never modified, and no rows are removed: 101,766 rows in, 101,766 rows out."));
S.push(table(["Issue", "Variable / table", "Action", "Reason", "Effect"], [
  ["'?' missing marker", "race, payer, specialty, diag", "null then 'Not recorded'", "Explicit category; no deletion", "Rows retained"],
  ["Mostly missing", "weight", "Dropped", "96.9% missing", "-1 column"],
  ["Constant", "examide, citoglipton", "Dropped", "No information", "-2 columns"],
  ["'None' lab result", "A1Cresult, max_glu_serum", "'Not measured'; 'Norm' to 'Normal'", "Absence of test is informative", "Readable categories"],
  ["Mixed-type ICD-9", "diag_1-3", "Text conversion; fnIcd9Group to 9 chapters", "Granularity; follows Strack et al.", "3 group columns"],
  ["Coded IDs", "3 ID columns", "Decoded via parsed IDS_mapping; business groups", "Readability; comparable groups", "3 dimensions"],
  ["Ineligible outcomes", "discharge 11,13,14,19,20,21", "Eligible flag = 0", "Cannot be readmitted", "Denominator 99,343"],
  ["Three-level outcome", "readmitted", "Binary 30-day target + label", "Business definition", "11,314 eligible readmissions"],
  ["High cardinality", "medical_specialty", "Specialty Group", "Readable visuals", "12 groups"],
  ["Wide medications", "21 drug columns", "Count, dose changes; unpivot to Fact_Medication", "Analysis without 21 columns", "Child fact"],
  ["Skewed counts", "visits, LOS, meds, labs, diagnoses", "Bands + sort columns", "Stable group comparisons", "16 columns"],
  ["Repeat patients", "patient_nbr", "Encounter count, patient type", "Context; leakage control", "23.4% repeat"],
], [1.3, 1.4, 1.6, 1.4, 1.1]));
S.push(p("The complete log with record counts is in documentation/data_cleaning_log.md."));

// 6
S.push(h1("6. Tool-specific execution (Power BI)"));
S.push(h2("6.1 Power Query"));
S.push(p("What and why: all cleaning rules are expressed as Power Query steps so the report refreshes end-to-end from the raw Excel file. Queries are organised as staging queries (not loaded), reusable functions and loaded tables."));
S.push(table(["Query", "Technique", "Output"], [
  ["DataFolder", "Text parameter (IsParameterQuery)", "Single place to change the source path"],
  ["Raw_Encounters", "Csv.Document on a value-for-value CSV export of the workbook sheet (faster than parsing the 22 MB .xlsx), PromoteHeaders, TransformColumns (diag codes to text), TransformColumnTypes with en-US culture", "Typed raw staging table"],
  ["Raw_IDS_Mapping", "Index-free parsing of a stacked sheet: AddColumn section marker, FillDown, SelectRows, Int64.From", "Long lookup table (section, id, description)"],
  ["fnIcd9Group", "Custom function with try/otherwise numeric parsing and ICD-9 range rules", "Clinical chapter for any code"],
  ["fnSpecialtyGroup / fnBand", "Record lookup with Record.FieldOrDefault; generic banding with List.PositionOf", "Reusable classification logic"],
  ["Fact_Encounter", "ReplaceValue, TransformColumns, AddColumn, local function AddBand, Record.SelectFields over a medication list, Table.Group + NestedJoin (patient counts), NestedJoin to model scores", "101,766-row fact with 70 columns"],
  ["Fact_Medication", "UnpivotOtherColumns + filter", "Encounter x prescribed drug"],
  ["Dimensions", "Filtered mapping + record-based group lookup; #table for Age and Diagnosis Group", "5 dimensions"],
  ["Model tables", "fnReadCsv + typed columns + rename; feature importance top-12 filter; odds-ratio chart flag", "6 reference tables"],
], [1.3, 3, 1.6]));
S.push(p("Excerpt - the ICD-9 grouping function:"));
S.push(...codeBlock(fs.readFileSync(path.join(ROOT, "analysis/power_query/fnIcd9Group.m"), "utf8").trim()));

S.push(h2("6.2 Data model"));
S.push(p("A star schema with Fact_Encounter at encounter grain; Fact_Medication as a child fact; dimensions for age, admission type, admission source, discharge disposition and primary diagnosis group; disconnected parameter tables (Model Selector, Alert Threshold) for the simulator; and a dedicated KPI Measures table. All relationships are many-to-one with single-direction filtering. There is no date table because the data contain no dates; time-intelligence measures were deliberately not created."));
S.push(table(["From (many)", "To (one)"], [
  ["Fact_Encounter[Age Band]", "Dim_Age[Age Band]"], ["Fact_Encounter[Admission Type ID]", "Dim_Admission_Type"],
  ["Fact_Encounter[Admission Source ID]", "Dim_Admission_Source"], ["Fact_Encounter[Discharge Disposition ID]", "Dim_Discharge_Disposition"],
  ["Fact_Encounter[Primary Diagnosis Group]", "Dim_Diagnosis_Group"], ["Fact_Medication[Encounter ID]", "Fact_Encounter[Encounter ID]"],
  ["Model_Threshold_Curve[Model]", "Model Selector[Model]"], ["Model_Feature_Importance[Model]", "Model Selector[Model]"],
], [1, 1]));
S.push(p("Design choices: eligibility is a flag rather than a filter so totals reconcile to the raw file; derived attributes are created once in Power Query rather than as calculated columns; the medication-level rate uses TREATAS instead of a bi-directional relationship. Details in documentation/data_model.md."));

S.push(h2("6.3 DAX"));
S.push(p("67 measures in five display folders (Volume, Readmission, Utilisation, Model). Key patterns:"));
S.push(bullet([b("Eligibility-aware KPIs: "), "every readmission measure filters Eligible for Readmission = 1, so the denominator is consistent."]));
S.push(bullet([b("Benchmarks: "), "Overall 30-Day Readmission Rate uses REMOVEFILTERS(); Rate Difference vs Overall and Relative Rate vs Overall compare any group with it; Share of 30-Day Readmissions uses ALLSELECTED()."]));
S.push(bullet([b("Ranking and selection: "), "Discharge Group Rank (RANKX over ALLSELECTED); Highest-Rate Discharge Group (ADDCOLUMNS, FILTER minimum volume, TOPN)."]));
S.push(bullet([b("Conditional formatting: "), "Readmission Rate Colour returns a hex colour via SWITCH(TRUE()) relative to the benchmark and drives bar colours and matrix backgrounds."]));
S.push(bullet([b("Dynamic text: "), "Headline Readmission Text and Threshold Narrative build sentences that respond to slicers."]));
S.push(bullet([b("Confusion matrix: "), "Flagged Encounters and True Positives read the selected model and threshold, filter the test-set rows with CALCULATETABLE and FILTER, and feed Precision, Recall, Specificity, F1, Alert Rate, False Alarms per True Readmission and Lift."]));
S.push(p("Example:"));
S.push(...codeBlock(`Flagged Encounters =
VAR _thr = [Selected Threshold]
VAR _m = [Selected Model]
VAR _flagged =
    FILTER (
        CALCULATETABLE ( Fact_Encounter, Fact_Encounter[Data Split] = "Test" ),
        IF ( _m = "Random Forest", Fact_Encounter[Risk Score RF], Fact_Encounter[Risk Score LR] ) >= _thr
    )
RETURN COUNTROWS ( _flagged ) + 0`));
S.push(p("All measures with descriptions are listed in documentation/dax_measures.md."));

S.push(h2("6.4 Statistical analysis and models (supporting Python step)"));
S.push(p("Power BI is not designed for training and validating classifiers, so this step uses Python. Its outputs are imported into Power BI, where the threshold-dependent metrics are recalculated in DAX."));
S.push(bullet("Population: 99,343 eligible encounters; target = readmitted within 30 days (11.39%)."));
S.push(bullet("Association tests: chi-square (with Cramer's V and minimum expected counts) for categorical variables; Mann-Whitney U with rank-biserial r for counts (non-normal, skewed)."));
S.push(bullet("Logistic regression (statsmodels) on the training set for adjusted odds ratios with 95% confidence intervals; dummies with fewer than 30 cases dropped for stability; references: Emergency admission, Home discharge, Circulatory diagnosis, Internal Medicine, Caucasian, Female, tests 'Not measured'."));
S.push(bullet("Classifiers (scikit-learn): logistic regression (one-hot + scaling) and Random Forest (400 trees, min leaf 25). Features are pre-discharge attributes only."));
S.push(bullet("Validation: GroupShuffleSplit 80/20 by patient (0 patients in both sets); 5-fold GroupKFold cross-validation on the training set; baseline rule 'any prior inpatient visit'; metrics ROC-AUC, PR-AUC, Brier score, confusion matrix at a capacity-based operating point (top 20%), permutation importance on the test set; seed 42."));

S.push(h2("6.5 Report design and storytelling"));
S.push(p("Eight 1280 x 720 pages, each answering one question, with a navy header stating the question and an insight panel stating the answer. A custom theme provides consistent colours; red / amber / teal / blue-grey always means 'well above / above / below / near the overall rate'. Slicers are placed where segmentation answers a question (age group, gender, race, admission type, discharge group, readmission status, model, threshold)."));
S.push(table(["Page", "Question", "Main visuals"], [
  ["1 Executive Overview", "How big is the problem; what are the headline drivers?", "6 KPI cards; rate by prior inpatient band; by discharge group; volume and rate by age; outcome mix; key messages"],
  ["2 Readmission Patterns", "Variation by age, admission type, source, discharge", "Dynamic headline; 3 coloured bar charts; drillable discharge matrix with benchmark gap"],
  ["3 Prior Visits", "Does prior hospital use predict readmission?", "Rate by inpatient, emergency, outpatient bands; inpatient x emergency heat map; risk-multiple cards"],
  ["4 Utilisation", "LOS, procedures, medications by group", "LOS by admission type and diagnosis; procedures by specialty; medication band combo; age profile matrix"],
  ["5 Risk Drivers", "What is associated with readmission?", "Association test table ranked by effect size; adjusted odds ratio chart"],
  ["6 Predictive Model", "How well do the models perform?", "Metrics table; ROC curves; risk-decile chart; permutation importance with model slicer"],
  ["7 Threshold Simulator", "Alerts vs readmissions caught", "Model and threshold slicers; narrative; 7 KPI cards; 2x2 confusion matrix; precision/recall/alert-rate curves"],
  ["8 Data and Method Notes", "Definitions and limitations", "Text panels; reconciliation cards; ICD-9 group table"],
], [1.2, 1.7, 3]));

S.push(h2("6.6 Building and validating the PBIP"));
S.push(p("The project is a genuine Power BI Project (.pbip): the semantic model is stored as TMDL and the report as PBIR JSON. Both are generated by scripts/build_semantic_model.py and scripts/build_report.py so the project is reproducible and diff-friendly in Git. All 97 report JSON files were validated against Microsoft's published PBIR JSON schemas (scripts/validate_pbir.py). The project was then opened in Power BI Desktop 2.159 (October 2026): the semantic model loaded, all 16 tables and 67 measures appeared, and all 8 pages rendered with their visuals bound to the model. Issues found and fixed during that test: the reserved table name 'Measures' (renamed 'KPI Measures'), very slow refresh from the 22 MB workbook (switched to value-for-value CSV exports), and a privacy-level prompt for combining the Excel/CSV sources (set to Organizational). The full data refresh had reached the row-loading stage but did not finish on the test PC because the machine repeatedly ran out of resources and disconnected, so the populated visuals have not yet been inspected in Power BI. Totals were instead reconciled against the independent pandas implementation."));

// 7
S.push(h1("7. Objective-by-objective analysis"));
S.push(h2("Objective 1 - Frequency of readmission"));
S.push(p("Of 99,343 eligible encounters, 11,314 (11.39%) were readmitted within 30 days and 47.1% at any time. The crude rate on all 101,766 encounters is 11.16%. Rates by group:"));
S.push(table(["Dimension", "Lowest", "Highest", "Comment"], [
  ["Age band", "0-10: 1.9% (small group)", "20-30: 14.3% (n = 1,649); adults 30+ 9.8%-12.6%", "Little practical variation among adults"],
  ["Admission type", "Elective 10.5%", "Emergency 11.8%", "Narrow spread"],
  ["Discharge group", "Home 9.3%", "Rehab / other inpatient care 26.0%", "Largest spread; SNF 14.6%, hospital transfer 14.8%"],
  ["Primary diagnosis", "Musculoskeletal 9.5%", "Diabetes 13.1%", "Narrow spread"],
], [1.2, 1.5, 2, 1.8]));
S.push(p("Interpretation: readmission is common enough to justify a targeted programme, and discharge destination, not demographics, is where the differences are."));

S.push(h2("Objective 2 - Characteristics associated with readmission"));
S.push(p("Unadjusted tests (largest effects): prior inpatient visits (rank-biserial r = 0.21), discharge disposition (Cramer's V = 0.11), length of stay (r = 0.10), number of diagnoses (0.09), number of medications (0.09), prior emergency visits (V = 0.07). Gender (p = 0.60), number of procedures (p = 0.15) and diabetes medication count (p = 0.20) were not associated. Age, race, admission type, admission source, HbA1c and glucose results were significant but with very small effects (V < 0.04)."));
S.push(p("Adjusted odds ratios (logistic regression, training set, pseudo R-squared 0.05): discharge to rehab / other inpatient care OR 3.33 (95% CI 3.01-3.67), transfer to another hospital 1.59, skilled nursing 1.46, left against medical advice 1.42, each prior inpatient visit 1.31 (1.29-1.33), on any diabetes medication 1.23, each prior emergency visit 1.05. HbA1c > 8 (OR 0.84) and > 7 (0.84) relative to 'not measured' likely reflect more engaged care rather than a protective effect of high HbA1c."));

S.push(h2("Objective 3 - Healthcare utilisation"));
S.push(p("Average stay 4.40 days (447,362 bed days); 15.0% of stays last 8+ days. LOS rises with age from 2.6 days (0-10) to 4.8 days (80-90) and is longest for neoplasm (5.4) and injury (4.6) primary diagnoses. Procedures are highest for radiology (3.2), cardiology (2.7) and surgery (2.0) admissions. Readmitted patients had slightly longer index stays (4.77 vs 4.33 days) and more medications (16.9 vs 15.9). The readmission rate rises across medication bands, but medication count adds little once other factors are known."));

S.push(h2("Objective 4 - Previous hospital visits and readmission"));
S.push(table(["Prior inpatient visits", "Eligible encounters", "30-day rate"], [
  ["0", "66,245", "8.6%"], ["1", "18,984", "13.3%"], ["2", "7,300", "17.9%"], ["3-4", "4,845", "22.0%"], ["5+", "1,969", "37.1%"],
], [1, 1, 1]));
S.push(p("Emergency visits: 10.7% (none), 14.7% (1), 21.7% (2+). Outpatient visits: 10.9% (none), 14.2% (1), 13.6% (2+). Patients with 3+ prior inpatient visits readmit at 3.1 times the rate of those with none. Prior inpatient visits is the most important feature in both models."));

S.push(h2("Objective 5 - Predictive model"));
S.push(table(["Model", "CV ROC-AUC", "Test ROC-AUC", "Test PR-AUC", "Precision @top 20%", "Recall @top 20%"], [
  ["Logistic Regression", "0.660 (sd 0.010)", "0.663", "0.219", "21.5%", "38.5%"],
  ["Random Forest", "0.671 (sd 0.009)", "0.674", "0.233", "21.9%", "39.2%"],
  ["Baseline: prior inpatient >= 1", "-", "0.602", "0.172", "16.5%", "48.5% (flags 33%)"],
], [1.6, 1, 1, 1, 1.2, 1.2]));
S.push(p("Random Forest is selected but the difference to logistic regression is small, so logistic regression remains a reasonable, more explainable alternative. Calibration is acceptable (Brier 0.095; mean predicted risk close to the 11.2% observed rate). Risk deciles separate well: 4.1% observed in decile 1 rising to 27.5% in decile 10. Permutation importance: prior inpatient visits (AUC drop 0.059) and discharge disposition (0.054) dominate; all other features each contribute less than 0.005."));
S.push(p("Balance between catching readmissions and false alarms: at the default 0.5 threshold Random Forest raises no alerts. At a 15% threshold it flags 3,903 of 19,802 test discharges, catches 864 of 2,216 readmissions (recall 39.0%), and 22.1% of alerts are correct (3.5 false alarms per readmission caught). The simulator page lets managers choose the threshold according to capacity."));

S.push(h2("Objective 6 - Presenting to management"));
S.push(p("The report pages are ordered as a narrative (size of the problem, where, why, what we can predict, what it would cost), every page carries its finding in plain language, and the README and this report provide written versions for different audiences."));

S.push(table(["Objective", "Procedure", "Power BI functionality", "Result", "Interpretation"], [
  ["1", "Eligibility-aware rates by group", "Measures, benchmark DAX, colour rule, matrix drill", "11.4%; 9.3%-26.0% by discharge", "Target discharge pathways"],
  ["2", "Tests + adjusted OR", "Imported tables, ranked table, OR bar chart with filter", "Prior visits and discharge dominate", "Demographics weak"],
  ["3", "Utilisation averages", "Average measures, combo chart, matrix", "LOS 4.4 days; rises with age", "Workload, weak predictor"],
  ["4", "Banded rates, heat map", "Band columns with sort order, matrix CF", "8.6% to 37.1%", "Simple screening flag"],
  ["5", "LR vs RF, threshold", "Model tables, ROC line, DAX confusion matrix, slicers", "AUC 0.674; top decile 27.5%", "Prioritisation tool"],
  ["6", "Narrative report", "Text panels, dynamic text, theme", "8 pages", "Decision-ready"],
], [0.6, 1.4, 1.8, 1.4, 1.3]));

// 8
S.push(h1("8. Key findings"));
const findings = [
  ["About 1 in 9 eligible discharges is readmitted within 30 days.", "11,314 / 99,343 = 11.39%; 47.1% readmitted at any time.", "Large enough volume to justify a targeted programme."],
  ["Recent hospital use is the strongest warning sign.", "8.6% with 0 prior inpatient visits vs 37.1% with 5+; OR 1.31 per visit; top model feature.", "Available at admission; usable without a model."],
  ["Discharge destination separates risk most.", "Rehab / other inpatient care 26.0% (OR 3.3); SNF 14.6%; home 9.3%.", "Handover to other institutions is a likely improvement area (hypothesis)."],
  ["Demographics and admission route matter little.", "Adult age bands 9.8%-12.6%; admission types 10.5%-11.8%; gender not significant.", "Screening by age or admission type would be inefficient."],
  ["Utilisation reflects workload more than risk.", "Readmitted: LOS 4.8 vs 4.3 days; procedures not associated (p = 0.15).", "Do not use LOS or procedures as a proxy for risk."],
  ["A risk score ranks patients usefully but moderately.", "RF ROC-AUC 0.674 vs LR 0.663 vs rule 0.602; decile 10 27.5% vs decile 1 4.1%.", "Use for prioritisation within capacity, not individual decisions."],
  ["Threshold choice drives workload.", "0.5 flags nobody; 15% flags 20% of discharges, catches 39% of readmissions, 22% precision.", "Set threshold from follow-up capacity."],
];
S.push(table(["Finding", "Evidence", "Business implication"], findings, [2, 2.4, 2]));
S.push(gap());
S.push(p("Figures 1-6 are static charts drawn in Python (scripts/04_analysis_charts.py) from the same processed data and model outputs that the Power BI model imports. They are analysis charts, not screenshots of the Power BI report."));
S.push(...image("01_rate_by_prior_inpatient.png", "Figure 1 - 30-day readmission rate by prior-year inpatient visits"));
S.push(...image("02_rate_by_discharge_group.png", "Figure 2 - 30-day readmission rate by discharge group"));
S.push(...image("03_rate_by_age.png", "Figure 3 - 30-day readmission rate by age band"));
S.push(...image("04_roc_curves.png", "Figure 4 - ROC curves, logistic regression vs Random Forest (test set)", 398));
S.push(...image("05_risk_deciles.png", "Figure 5 - Observed readmission rate by Random Forest risk decile (test set)"));
S.push(...image("06_threshold_tradeoff.png", "Figure 6 - Recall, precision and alert rate across thresholds (Random Forest)"));

// 9
S.push(h1("9. Business recommendations"));
S.push(table(["Horizon", "Recommendation", "Supported by", "Assumption / dependency"], [
  ["Immediate", "Flag patients with 1+ (and especially 3+) inpatient stays in the past year at admission and start discharge planning early.", "Objective 4", "Prior-visit history is available in the admission system."],
  ["Immediate", "Review discharge handover for transfers to rehab / other inpatient care and skilled nursing facilities.", "Objectives 1-2", "Causes of readmission in these pathways need confirming with clinicians."],
  ["Medium term", "Pilot the risk score with a threshold matched to team capacity (e.g. top 10-20%), with a comparison group to measure impact.", "Objective 5, simulator", "Model must be retrained and validated on current local data."],
  ["Medium term", "Improve capture of specialty, payer and HbA1c testing.", "Data quality", "Process change in data entry."],
  ["Longer term", "Add dates, post-discharge follow-up, social and cost data; move to ICD-10; re-evaluate models (e.g. calibrated gradient boosting).", "Limitations", "Data availability and governance approval."],
], [0.9, 2.6, 1.1, 1.8]));

// 10
S.push(h1("10. Technical and analytical limitations"));
S.push(h3("Observed limitations"));
["No admission or discharge dates; no time series, seasonality or time-to-readmission.", "Heavy missingness: weight 96.9%, HbA1c not measured 83.3%, specialty 49.1%, payer 39.6%.", "Some mapping codes have no description.", "Data from 1999-2008, ICD-9 coded."].forEach(t => S.push(bullet(t)));
S.push(h3("Methodological limitations"));
["Observational data: associations, not causal effects.", "Encounter-level rates give repeat patients more weight.", "Large sample makes trivial differences significant; effect sizes used to judge importance.", "Model ROC-AUC 0.67: moderate discrimination; scores are probabilities from an unweighted model trained on 80% of patients.", "Models trained in Python; Power BI recalculates metrics from the exported scores (6-decimal precision)."].forEach(t => S.push(bullet(t)));
S.push(h3("Contextual limitations"));
["No cost data, so financial impact cannot be quantified.", "Readmission cause, plannedness and hospital of readmission are unknown.", "No information on post-discharge care or social circumstances."].forEach(t => S.push(bullet(t)));
S.push(h3("Assumptions"));
["Death and hospice discharges (codes 11, 13, 14, 19, 20, 21) are not eligible for readmission.", "Codes without descriptions are grouped as 'Not recorded'.", "'None' in lab tests means the test was not performed.", "ICD-9 grouping follows Strack et al. (2014)."].forEach(t => S.push(bullet(t)));

// 11
S.push(h1("11. Validation and quality assurance"));
S.push(table(["Check", "Method", "Result"], [
  ["Row counts", "Raw vs cleaned (pandas and Power Query)", "101,766 = 101,766"],
  ["Key uniqueness", "encounter_id duplicates", "0"],
  ["Referential integrity", "Fact IDs present in mapping dimensions", "0 orphans"],
  ["Eligibility reconciliation", "Eligible + excluded = total", "99,343 + 2,423 = 101,766"],
  ["KPI reconciliation", "pandas reference implementation of every KPI", "documentation/reconciliation_reference_python.txt; Power BI card check outstanding"],
  ["Model leakage", "Patients in both train and test", "0"],
  ["DAX vs Python model metrics", "Recompute confusion matrix rule at thresholds 5%-40% for both models", "0 mismatches after aligning on exported 6-decimal scores"],
  ["Report definition", "97 PBIR JSON files vs Microsoft schemas", "0 errors"],
  ["Deliverable test", "Open .pbip in Power BI Desktop 2.159; refresh", "Model loads, 8 pages render; 3 issues fixed (see 6.6). Full refresh not completed on test PC - outstanding"],
  ["Narrative accuracy", "Every number in text panels checked against data", "Corrected 7 draft statements before release"],
], [1.3, 2.4, 2]));
S.push(p("The open items are listed in documentation/qa_checklist.md: refresh once in Power BI Desktop, compare the page 8 cards with the reference values, and export the report pages to PDF/PNG."));

// 12
S.push(h1("12. Lessons and competencies demonstrated"));
["Business problem framing: translating a broad management concern into six objectives, thirteen questions and an action-oriented report.",
 "Data preparation: handling healthcare-specific quirks (ICD-9 codes, 'None' tests, death/hospice eligibility, stacked lookup sheet) reproducibly in Power Query.",
 "Data modelling: star schema, single-direction relationships, parameter tables, measure table, sort-by columns.",
 "DAX: filter context manipulation, benchmarks, ranking, conditional colour, dynamic text, a slicer-driven confusion matrix.",
 "Statistical reasoning: choosing tests by data type, reporting effect sizes and adjusted odds ratios, avoiding causal language.",
 "Predictive modelling: leakage-safe validation, baselines, threshold selection based on operational capacity.",
 "Communication: one question per page, explicit limitations, recommendations with assumptions.",
 "Lesson: accuracy-type metrics at a default 0.5 threshold are misleading for rare outcomes; operating-point choice is a business decision.",
 "Lesson: with very large samples, significance is cheap; effect size and practical difference drive the story."].forEach(t => S.push(bullet(t)));

// 13
S.push(h1("13. Conclusion"));
S.push(p("The project answers all six objectives. About 11% of eligible diabetic discharges return within 30 days. Risk is concentrated among patients with recent inpatient stays and those discharged to further institutional care, while demographics and admission route add little. A Random Forest model ranks patients usefully (ROC-AUC 0.674; top decile 27.5% vs 4.1% bottom) and the Power BI threshold simulator turns it into a capacity-planning tool. The deliverable is a refreshable, documented Power BI Project that management can use to target discharge planning, with its limitations stated plainly."));

// ------------------------------------------------------------------ document
const doc = new Document({
  creator: "Data Analyst", title: "Diabetes Readmission Risk Analytics - Analyst Technical Report",
  styles: {
    default: { document: { run: { font: "Arial", size: 20 } } },
    paragraphStyles: [
      { id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { font: "Arial", size: 30, bold: true, color: NAVY }, paragraph: { spacing: { before: 360, after: 160 }, keepNext: true, outlineLevel: 0 } },
      { id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { font: "Arial", size: 24, bold: true, color: "3D6A99" }, paragraph: { spacing: { before: 240, after: 120 }, keepNext: true, outlineLevel: 1 } },
      { id: "Heading3", name: "Heading 3", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { font: "Arial", size: 21, bold: true, color: "243B53" }, paragraph: { spacing: { before: 160, after: 80 }, keepNext: true, outlineLevel: 2 } },
    ],
  },
  numbering: { config: [{ reference: "bul", levels: [{ level: 0, format: LevelFormat.BULLET, text: "•", alignment: AlignmentType.LEFT,
    style: { paragraph: { indent: { left: 540, hanging: 270 } } } }] }] },
  sections: [{ properties: { page: { margin: { top: 1440, bottom: 1440, left: 1440, right: 1440 } } },
    footers: { default: new Footer({ children: [new Paragraph({ alignment: AlignmentType.RIGHT,
      children: [new TextRun({ text: "Diabetes Readmission Risk Analytics - page ", size: 16, color: "8D99AE" }),
                 new TextRun({ children: [PageNumber.CURRENT], size: 16, color: "8D99AE" })] })] }) },
    children: S }],
});
Packer.toBuffer(doc).then(buf => {
  const out = path.join(ROOT, "documentation", "Analyst_Technical_Report.docx");
  fs.writeFileSync(out, buf); console.log("written", out);
});
