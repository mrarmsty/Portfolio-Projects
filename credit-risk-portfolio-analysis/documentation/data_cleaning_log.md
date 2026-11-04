# Data Cleaning & Transformation Log

Raw file: 32,581 records → cleaned analysis table: **32,411 records** (170 excluded; every excluded record is listed with its reason in `data/processed/excluded_records.csv` and on the workbook's `Data_Exclusions` sheet). The raw file is preserved unchanged in `data/raw/` and on the `Data_Raw` sheet.

The rules were applied with `scripts/prepare_data_and_fit_models.py` (pandas) and are mirrored in `documentation/power_query_cleaning.m` for an Excel-native refresh.

| Step | Issue | Variable / table | Action taken | Reason | Effect on data |
|---|---|---|---|---|---|
| 1 | No unique record identifier | All records | Created loan_id = 'LN' + raw row position | Needed to trace cleaned and excluded records back to the raw file and to support audit. | 32,581 IDs created before any exclusions. |
| 2 | Exact duplicate records (all 12 fields identical) | All fields | Removed the later copy, kept the first occurrence | 165 pairs; second copies sit in two contiguous blocks of the file (rows ~15,977–17,999 and 25,000+), consistent with an overlapping extract rather than coincidence. | −165 records. Duplicates had an 11.5% default rate, so keeping them would slightly understate risk. |
| 3 | Impossible ages | person_age | Excluded records with age > 100 | Ages of 123 and 144 are impossible; the same records include an income of 6,000,000, so the whole record is unreliable. | −5 records (all non-defaults). Ages 84 and 94 retained as plausible. |
| 4 | Impossible employment length | person_emp_length | Set to missing (record kept) | 123 years of employment for borrowers aged 21–22. The rest of each record looks valid. | 2 values set to missing; counted with the 'Unknown' employment group. |
| 5 | Missing employment length | person_emp_length | Retained as missing; 'Unknown' band; emp_unknown flag; median (4 yrs) imputation for the tree only | Missingness is informative (31.7% default vs 21.9% overall), so deleting or silently imputing would hide a risk signal. | 889 records (2.7%) flagged. |
| 6 | Placeholder interest rates | loan_int_rate | Set 6.00% to missing for grades B–E | 6.00% sits far below each grade's otherwise-minimum rate (B 8.70%, C 10.28%, D 11.86%, E 13.43%). For grade A it is plausible and kept. | 11 values set to missing. |
| 7 | Missing interest rate | loan_int_rate | Retained as missing; 'Not recorded' band; excluded from rate averages and tests; grade-median imputation for the tree only | Missing evenly across grades (8–11%) with a similar default rate (20.7% vs 21.9%), consistent with random missingness. Rate is not used by the final logistic model. | 3,105 records (9.6%) not recorded. |
| 8 | Supplied loan_percent_income inconsistent with its components | loan_percent_income | Recomputed lti = loan_amnt ÷ person_income; flagged LTI_MISMATCH; supplied field kept for audit | 428 records differ beyond 2-dp rounding and every one is a default (supplied ratio ≈ 0.85 × computed). The recomputed value is precise and consistent with the loan amounts used for exposure. | Sensitivity check: band default rates move by ≤2.5 points and conclusions are unchanged. |
| 9 | Extreme incomes | person_income | Retained | Values up to ~2.0M are plausible; no evidence of entry error once the age-144 record is excluded. | Handled with income bands and ln(income) rather than removal. |
| 10 | Categorical label consistency | Text fields | Checked; no change required | No leading/trailing spaces, case or spelling variants found. | None. |
| 11 | Model development split | All records | Stratified 70/30 Train/Test split (seed 42) | The file is ordered in blocks (e.g. by credit history), so a random stratified split avoids a biased hold-out set. | Train 22,687 / Test 9,724; identical default rates (21.87%). |
| 12 | Analysis fields | Derived | Added lti, ln_income, grade_num, emp_unknown, imputed model inputs, 7 band fields, model scores and risk band as live table formulas | Lets every summary update automatically and lets new records be scored when added to the table. | 19 formula columns in tblLoans. |

## Record reconciliation

| Stage | Records |
|---|---|
| Raw file | 32,581 |
| Less exact duplicates (later copy) | −165 |
| Less impossible ages (> 100) | −5 |
| **Cleaned analysis table** | **32,411** |
| of which training sample (70%) | 22,687 |
| of which test sample (30%) | 9,724 |

## Sensitivity check: supplied vs recomputed loan-to-income

| LTI band | Default rate using recomputed LTI | Default rate using supplied `loan_percent_income` |
|---|---|---|
| 0–10% | 11.6% | 11.6% |
| 10–20% | 14.6% | 14.7% |
| 20–30% | 21.4% | 21.0% |
| 30–40% | 64.2% | 61.9% |
| 40%+ | 74.5% | 73.6% |
| Renters with LTI ≥ 30% | 94.8% (2,533 loans) | 92.3% (2,621 loans) |

The choice of field moves band default rates by at most 2.5 percentage points and does not change any conclusion. Logistic regression test AUC was 0.8756 with the recomputed ratio and 0.8746 with the supplied one during development (linear-LTI specification).
