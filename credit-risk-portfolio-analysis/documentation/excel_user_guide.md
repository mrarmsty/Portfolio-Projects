# Excel User Guide — Credit Risk Monitoring Tool

**File:** `analysis/Credit_Risk_Monitoring_Tool.xlsx`
**Requires:** Excel 2016 or later (Microsoft 365 recommended). No macros, no external data connections and no Power Query refresh are needed.

The workbook opens on the **Home** sheet, which links to every other sheet and shows the QA status, the champion model and the headline default rate.

---

## 1. Colour conventions

| Look | Meaning | Can I edit it? |
|---|---|---|
| Blue text on a yellow background | Input or setting (filters, thresholds, Scorer inputs, model coefficients) | Yes |
| Black text | Formula | No — overwriting breaks the logic |
| Grey text | Fixed output from model estimation (standard errors, tree importance, CV results) | No |
| Navy header row | Table header | No |

Every sheet has a **◄ Home** link in cell A1.

---

## 2. Everyday use

### Dashboard — monitor the portfolio
1. Choose a value in any of the four yellow drop-downs: **Grade**, **Purpose**, **Housing**, **LTI band**. `All` removes that filter.
2. The eight KPI cards, the coloured alert bar and all six charts update immediately.
3. Each chart ignores the filter on its own dimension (the grade chart still shows every grade when you filter on grade) so you can compare the selection with its neighbours.
4. The alert bar reads:
   - **HIGH RISK** — the selection's default rate is at least 1.5× the portfolio rate (multiple set on Lists).
   - **Above average** — above the portfolio rate.
   - **At or below the portfolio average**.
   - **Too few loans** — fewer than 100 loans match (threshold set on Lists).

### Insights — management summary
Ten findings, each with a live evidence sentence, a recommended action and a timeframe, followed by suggested monitoring indicators with their current values.

### Segments — find high-risk groups
- Change **Minimum loans per segment** (C6) or **High-risk default rate ≥** (C7). The Top 15 list, the flags and the "Flagged high-risk segments" summary update automatically.
- Heat maps show default rate (left) next to loan counts (right) so small cells are not over-read.

### Model_Eval — choose an operating threshold
- **Decision threshold** (C6): loans with PD at or above this are flagged. Confusion matrices and metrics update.
- **Cost ratio** (C7): how much worse a missed default is than a false alarm. The "Lowest-cost threshold" for each model updates. The default of 5 is an assumption — agree the real figure with Finance.

### Scorer — assess a new application
1. Overwrite the yellow cells (the example applicant can be replaced). Drop-downs enforce valid grades, purposes, housing types and Y/N.
2. Leave **Employment length** or **Interest rate** blank if unknown; the models handle it the same way as in training.
3. Read the **Input check** line first — it must say *Inputs OK*.
4. Results: PD from both models, the decision-tree rule that applies, the champion PD, risk band, suggested action, and the default rate of similar historical loans.

---

## 3. Settings (Lists sheet)

| Setting | Default | Effect |
|---|---|---|
| Champion model | Decision tree | Which model feeds `model_pd`, `risk_band`, the dashboard PD card and the Scorer's champion PD |
| Dashboard minimum loans | 100 | Below this the alert says "too few loans" |
| Dashboard high-risk multiple | 1.5× | Threshold for the HIGH RISK alert |
| Employment imputation | 4.0 years | Frozen training median used by the tree (live check beside it) |
| Rate imputation by grade | Training medians | Frozen; used by the tree when a rate is not recorded |
| Band thresholds | See sheet | Lower bound inclusive; changing them re-bands every loan |
| PD risk bands | 0% / 10% / 25% / 50% | Low / Moderate / High / Very high cut-offs and suggested actions (illustrative policy) |

Band labels are used as COUNTIFS criteria, so they must stay unique and must not start with `<`, `>` or `=`.

---

## 4. Adding new loans

1. Go to **Data_Clean**. The data is the Excel table `tblLoans`.
2. Paste new records directly below the last row, in base columns **A–O** (`loan_id` … `dq_flags`) only. Use the same codes as existing data (e.g. `RENT`, `DEBTCONSOLIDATION`, grade letters, `Y`/`N`); leave blanks for missing employment length or rate.
3. The table expands and the 19 formula columns (bands, model inputs, PDs, risk band) fill automatically. All summaries, charts and the dashboard use structured references, so they include the new rows with no range edits.
4. Set `data_split` to something other than `Train`/`Test` (e.g. `New`) so new loans do not change model training or evaluation figures, or set it deliberately if you are re-validating.
5. Open **QA_Checks**. Checks against fixed counts (raw file size, exclusions, test AUC) will change by design; update their expected values deliberately and confirm all others still pass.

The `power_query_cleaning.m` script in `documentation/` reproduces the cleaning rules in Power Query if you want to refresh from a new raw CSV.

---

## 5. Re-estimating the logistic regression in Excel (optional)

The coefficients were estimated by maximum likelihood outside Excel. To confirm them with Solver:
1. Enable Solver (File ▸ Options ▸ Add-ins ▸ Excel Add-ins ▸ Solver Add-in).
2. On **Model_LR**, set the objective to the log-likelihood cell in the *Model fit* table, **Max**.
3. Variable cells: the blue coefficient cells listed on the sheet (not the reference-category zeros).
4. Untick "Make Unconstrained Variables Non-Negative", choose **GRG Nonlinear**, use central derivatives, and Solve.
5. Solver should report no meaningful improvement, because the coefficients are already at the maximum. Calculation over ~22,700 training rows can take a minute.

---

## 6. Performance and compatibility notes

- About 620,000 formulas, most in `tblLoans`. A full recalculation takes a few seconds on a modern laptop; keep calculation on Automatic.
- `INDEX`/`MATCH` is used instead of `XLOOKUP`, and no dynamic-array (spilling) functions are used, so the file works in Excel 2016/2019 as well as Microsoft 365. A few statistics use classic array formulas (`{=MEDIAN(IF(...))}`).
- The file contains no PivotTables: summaries are formula tables so they react instantly to the dashboard drop-downs without a refresh. To explore ad hoc, insert a PivotTable from `tblLoans` (Insert ▸ PivotTable ▸ Table/Range: `tblLoans`).
- If Excel opens in Protected View, click **Enable Editing** so formulas calculate.
