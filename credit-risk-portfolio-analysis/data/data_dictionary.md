# Data Dictionary

Source file: `data/raw/credit_risk_dataset.csv` (32,581 records, 12 fields). Analysis dataset: `data/processed/credit_risk_clean.csv` and the `tblLoans` table in the workbook (32,411 records).

The source file came with no documentation. Definitions below are taken from the field names and observed values; where meaning is assumed, it is stated. Fields marked *Derived (formula)* are calculated live in the workbook; the processed CSV contains the base fields plus `lti` and the seven band fields as values.

| Variable | Type | Description | Example / range | Data-quality observations | Source |
|---|---|---|---|---|---|
| loan_id | Text | Record identifier created during preparation: 'LN' + the record's position in the raw file (LN00001 = first data row). | LN00001 – LN32581 | The raw file has no identifier; this key makes every cleaned and excluded record traceable to the raw file. | Derived |
| person_age | Integer | Borrower age in years (assumed to be at application). | Raw 20–144; cleaned 20–94 | 5 records with age > 100 (123, 144) excluded as impossible. | Raw |
| person_income | Integer | Borrower annual income. Currency is not documented in the source. | 4,000 – 2,039,784 (cleaned) | Strongly right-skewed (median 55,000). 8 incomes above 1,000,000 retained as plausible high earners; analysed through bands and ln(income). | Raw |
| person_home_ownership | Text | Housing status of the borrower. | RENT, MORTGAGE, OWN, OTHER | 'OTHER' (106 loans) is not defined in the source; kept as its own category. | Raw |
| person_emp_length | Decimal (years) | Length of current employment in years. | 0 – 41 (cleaned) | 895 missing in the raw file (887 after exclusions) plus 2 impossible values of 123 years set to missing = 889 unknown (2.7%). Missing is informative: 31.7% default vs 21.9% overall. | Raw |
| loan_intent | Text | Stated purpose of the loan. | EDUCATION, MEDICAL, VENTURE, PERSONAL, DEBTCONSOLIDATION, HOMEIMPROVEMENT | No spelling, case or whitespace inconsistencies found. | Raw |
| loan_grade | Text | Credit grade assigned by the lender, A (best) to G (worst). Grading methodology not documented. | A – G | Prior default flag 'Y' appears only in grades C–G, so grade partly encodes credit history. | Raw |
| loan_amnt | Integer | Amount lent (exposure at origination). | 500 – 35,000 | Maximum of exactly 35,000 suggests a product cap (assumption). | Raw |
| loan_int_rate | Decimal (%) | Interest rate charged, in percentage points. | 5.42 – 23.22 | 3,116 missing in the raw file (3,094 after exclusions) plus 11 placeholder values of 6.00% in grades B–E set to missing = 3,105 not recorded (9.6%). Missingness is spread evenly across grades and does not change the default rate. | Raw |
| loan_status | Integer (0/1) | Repayment outcome: 1 = defaulted, 0 = did not default. | 0 / 1 | Definition of default (e.g. days past due, write-off) is not documented. Observation window is not documented. | Raw |
| loan_percent_income | Decimal | Loan amount as a share of income, as supplied (rounded to 2 dp). | 0.00 – 0.83 | 428 records (all defaults) disagree with loan_amnt ÷ person_income beyond rounding. Kept for audit only; analysis uses the recomputed lti field. | Raw |
| cb_person_default_on_file | Text (Y/N) | Whether a historical default is recorded on the borrower's credit file (assumed credit bureau). | Y / N | No missing values. | Raw |
| cb_person_cred_hist_length | Integer (years) | Length of the borrower's credit history in years. | 2 – 30 | No missing values; no value exceeds age − 16. | Raw |
| data_split | Text | Model development partition: 70% Train / 30% Test, stratified on loan_status, random seed 42. | Train / Test | Train 22,687 (21.87% default); Test 9,724 (21.87% default). | Derived |
| dq_flags | Text | Data-quality flags for the record (semicolon separated). | EMP_MISSING; EMP_INVALID; RATE_MISSING; RATE_PLACEHOLDER; LTI_MISMATCH | Blank where the record had no issues. | Derived |
| lti | Decimal | Loan-to-income ratio recomputed as loan_amnt ÷ person_income. | 0.0008 – 0.83 | Replaces the supplied loan_percent_income (see above). | Derived (formula) |
| ln_income | Decimal | Natural log of annual income, used to reduce skew in tests and the logistic model. | 8.29 – 14.53 |  | Derived (formula) |
| grade_num | Integer | Grade as an ordinal number: A = 1 … G = 7. | 1 – 7 |  | Derived (formula) |
| emp_unknown | Integer (0/1) | 1 if employment length is missing or invalid. | 0 / 1 |  | Derived (formula) |
| emp_length_model | Decimal | Employment length with missing values filled by the frozen training median (4 years). Used by the decision tree only. | 0 – 41 |  | Derived (formula) |
| int_rate_model | Decimal | Interest rate with missing values filled by the frozen training median for the loan's grade. Used by the decision tree only. | 5.42 – 23.22 |  | Derived (formula) |
| age_band … hist_band | Text | Analysis bands (lower bound inclusive) for age, income, LTI, employment length, interest rate, loan amount and credit history. Thresholds live on the Lists sheet. | e.g. lti_band '30–40%' | Missing employment length → 'Unknown'; missing rate → 'Not recorded'. | Derived (formula) |
| lr_logit / lr_pd | Decimal | Logistic regression linear predictor and probability of default. | PD 0 – 1 |  | Derived (formula) |
| tree_leaf / tree_pd | Text / Decimal | Decision tree leaf (L01–L32) and its Laplace-corrected training default rate. | PD 0 – 1 |  | Derived (formula) |
| model_pd / risk_band | Decimal / Text | PD from the champion model selected on the Lists sheet, and its risk band (Low, Moderate, High, Very high). |  |  | Derived (formula) |

## Assumptions requiring confirmation

- `loan_status = 1` means default; the default definition (days past due, write-off) and observation window are unknown.
- `loan_grade` A is the lowest-risk grade (supported by default rates rising A→G).
- `cb_person_default_on_file` and `cb_person_cred_hist_length` come from a credit bureau (inferred from the `cb_` prefix).
- Monetary fields share one currency, which is not documented.
- Age, income and employment length are as at application.
