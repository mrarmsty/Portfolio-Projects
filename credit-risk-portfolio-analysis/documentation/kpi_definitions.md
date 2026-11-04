# KPI & Metric Definitions

All measures are calculated with live Excel formulas over the `tblLoans` table unless stated. Rates are count-based (each loan weighted equally) unless labelled value-weighted.

| KPI / metric | Definition | Excel implementation | Notes |
|---|---|---|---|
| Loans | Number of loans in the cleaned portfolio (or the current selection). | COUNTIFS(tblLoans[...], criteria) | Cleaned portfolio = 32,411 loans. |
| Defaults | Loans with loan_status = 1. | COUNTIFS(..., tblLoans[loan_status], 1) |  |
| Default rate | Defaults ÷ Loans. The share of borrowers who defaulted. | Defaults / Loans | Count-based; every loan weighted equally. |
| Total lent | Sum of loan_amnt. | SUMIFS(tblLoans[loan_amnt], ...) | Currency not documented. |
| Defaulted loan value | Sum of loan_amnt for defaulted loans. | SUMIFS(tblLoans[loan_amnt], ..., tblLoans[loan_status], 1) | Original amount, not loss. Balance at default and recoveries are not in the data. |
| Value-weighted default rate | Defaulted loan value ÷ Total lent. |  | Higher than the count-based rate when larger loans default more. |
| Share of portfolio | Selection loans ÷ all loans. |  |  |
| Lift | Segment default rate ÷ portfolio default rate. |  | 1.0 = average; 2.0 = twice the average. |
| Share of defaults | Segment defaults ÷ all defaults. |  | Shows where defaults concentrate. |
| Average interest rate | Mean loan_int_rate where recorded. | AVERAGEIFS ignores blank rates | Excludes the 9.6% of loans with no recorded rate. |
| Loan-to-income (LTI) | loan_amnt ÷ person_income. | [@loan_amnt]/[@person_income] | Recomputed field, see cleaning log step 8. |
| Probability of default (PD) | Model-estimated probability that a loan defaults. | Logistic: 1/(1+EXP(−logit)); Tree: leaf PD |  |
| Recall (default capture rate) | Share of actual defaults the model flags at the chosen threshold. | TP / (TP + FN) | Answers 'what proportion of defaults can the model identify?' |
| Precision | Share of flagged loans that actually defaulted. | TP / (TP + FP) |  |
| Specificity | Share of non-defaults correctly not flagged. | TN / (TN + FP) |  |
| AUC (ROC) | Probability the model ranks a random defaulter above a random non-defaulter. | Trapezoid rule over a 101-point ROC table | 0.5 = no better than chance; 1.0 = perfect ranking. |
| Gini | 2 × AUC − 1. Common credit-scoring summary of ranking power. |  |  |
| KS statistic | Maximum gap between true-positive and false-positive rates. | MAX(TPR − FPR) |  |
| Cramér's V | Effect size for a chi-square test of association (0 = none, 1 = perfect). | SQRT(χ² / N) for a k × 2 table | Judged alongside p-values, which are tiny at this sample size. |
| Information Value (IV) | Predictive strength of a banded variable on the training set. | Σ (%non-default − %default) × WoE | <0.02 not useful; 0.02–0.1 weak; 0.1–0.3 medium; 0.3–0.5 strong; >0.5 very strong / check for leakage. |
