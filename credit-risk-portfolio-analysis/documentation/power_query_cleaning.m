// =====================================================================
// Credit Risk Portfolio Analysis - Power Query (M) cleaning script
// =====================================================================
// Purpose : Reproduces, natively in Excel, the cleaning rules documented in
//           documentation/data_cleaning_log.md, turning the raw CSV into the
//           base columns of tblLoans (Data_Clean sheet, columns A-O).
// How to use:
//   1. Excel > Data > Get Data > From Other Sources > Blank Query.
//   2. Home > Advanced Editor, paste this script, and set RawFilePath and
//      SplitFilePath below to where the files sit on your machine.
//   3. Close & Load To... a table. The 19 formula columns of tblLoans (bands,
//      model inputs, model scores) are Excel formulas and are not part of
//      this query - append the query output to tblLoans columns A-O.
// Notes   :
//   - The train/test assignment comes from data/processed/credit_risk_clean.csv,
//     because a random split cannot be regenerated identically in Power Query.
//   - Table.Buffer is used before Table.Distinct so the FIRST occurrence of each
//     duplicate is kept, matching the documented rule.
//   - Status: written to mirror the pandas implementation rule for rule; it has
//     not been executed in Excel in the build environment. Check the output
//     against the QA_Checks sheet (32,411 rows, 165 duplicates, 5 invalid ages,
//     889 unknown employment, 3,105 unrecorded rates, 428 LTI mismatches).
// =====================================================================
let
    RawFilePath   = "C:\credit-risk-portfolio-analysis\data\raw\credit_risk_dataset.csv",
    SplitFilePath = "C:\credit-risk-portfolio-analysis\data\processed\credit_risk_clean.csv",

    KeyColumns = {"person_age", "person_income", "person_home_ownership", "person_emp_length",
                  "loan_intent", "loan_grade", "loan_amnt", "loan_int_rate", "loan_status",
                  "loan_percent_income", "cb_person_default_on_file", "cb_person_cred_hist_length"},

    // ---- Load and type the raw file (blank fields become null) ----
    Source   = Csv.Document(File.Contents(RawFilePath), [Delimiter = ",", Columns = 12, Encoding = 65001, QuoteStyle = QuoteStyle.None]),
    Promoted = Table.PromoteHeaders(Source, [PromoteAllScalars = true]),
    Typed    = Table.TransformColumnTypes(Promoted, {
                  {"person_age", Int64.Type}, {"person_income", Int64.Type},
                  {"person_home_ownership", type text}, {"person_emp_length", type number},
                  {"loan_intent", type text}, {"loan_grade", type text},
                  {"loan_amnt", Int64.Type}, {"loan_int_rate", type number},
                  {"loan_status", Int64.Type}, {"loan_percent_income", type number},
                  {"cb_person_default_on_file", type text}, {"cb_person_cred_hist_length", Int64.Type}}, "en-US"),

    // ---- Step 1: traceable ID from raw file order ----
    Indexed = Table.AddIndexColumn(Typed, "row_no", 1, 1, Int64.Type),
    WithId  = Table.AddColumn(Indexed, "loan_id", each "LN" & Text.PadStart(Text.From([row_no]), 5, "0"), type text),

    // ---- Step 2: remove exact duplicates (all 12 source fields), keep first ----
    Deduped = Table.Distinct(Table.Buffer(WithId), KeyColumns),

    // ---- Step 3: exclude impossible ages ----
    ValidAge = Table.SelectRows(Deduped, each [person_age] <= 100),

    // ---- Step 4: impossible employment length -> missing ----
    EmpFlag  = Table.AddColumn(ValidAge, "emp_invalid",
                  each [person_emp_length] <> null and [person_emp_length] > [person_age] - 14, type logical),
    EmpClean = Table.AddColumn(EmpFlag, "emp_clean",
                  each if [emp_invalid] then null else [person_emp_length], type nullable number),

    // ---- Step 6: 6.00% placeholder rates in grades B-E -> missing ----
    RateFlag  = Table.AddColumn(EmpClean, "rate_placeholder",
                  each [loan_int_rate] = 6 and List.Contains({"B", "C", "D", "E"}, [loan_grade]), type logical),
    RateClean = Table.AddColumn(RateFlag, "rate_clean",
                  each if [rate_placeholder] then null else [loan_int_rate], type nullable number),

    // ---- Step 8: recomputed loan-to-income, used only to flag mismatches here ----
    WithLti = Table.AddColumn(RateClean, "lti_check", each [loan_amnt] / [person_income], type number),

    // ---- Data-quality flags (same order as the pandas implementation) ----
    WithFlags = Table.AddColumn(WithLti, "dq_flags", each Text.Combine(List.RemoveNulls({
                    if [emp_invalid] then "EMP_INVALID" else null,
                    if [rate_placeholder] then "RATE_PLACEHOLDER" else null,
                    if [person_emp_length] = null then "EMP_MISSING" else null,
                    if [loan_int_rate] = null then "RATE_MISSING" else null,
                    if Number.Abs([lti_check] - [loan_percent_income]) > 0.0051 then "LTI_MISMATCH" else null
                 }), "; "), type text),

    // ---- Replace cleaned columns ----
    Dropped  = Table.RemoveColumns(WithFlags, {"person_emp_length", "loan_int_rate", "emp_invalid", "rate_placeholder", "lti_check", "row_no"}),
    Renamed  = Table.RenameColumns(Dropped, {{"emp_clean", "person_emp_length"}, {"rate_clean", "loan_int_rate"}}),

    // ---- Step 11: attach the fixed train/test assignment ----
    SplitSrc = Table.PromoteHeaders(Csv.Document(File.Contents(SplitFilePath), [Delimiter = ",", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]), [PromoteAllScalars = true]),
    SplitMap = Table.SelectColumns(SplitSrc, {"loan_id", "data_split"}),
    Merged   = Table.NestedJoin(Renamed, {"loan_id"}, SplitMap, {"loan_id"}, "split", JoinKind.LeftOuter),
    WithSplit = Table.ExpandTableColumn(Merged, "split", {"data_split"}, {"data_split"}),

    // ---- Final column order = tblLoans columns A-O ----
    Result = Table.SelectColumns(WithSplit, {"loan_id", "person_age", "person_income", "person_home_ownership",
                 "person_emp_length", "loan_intent", "loan_grade", "loan_amnt", "loan_int_rate", "loan_status",
                 "loan_percent_income", "cb_person_default_on_file", "cb_person_cred_hist_length", "data_split", "dq_flags"}),
    Sorted = Table.Sort(Result, {{"loan_id", Order.Ascending}})
in
    Sorted
