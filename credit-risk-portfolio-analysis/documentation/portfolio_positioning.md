# Portfolio Positioning — Loan Portfolio Credit Risk Analysis (Excel)

How to present this project to employers: what it proves, which roles it supports, a CV entry, and interview preparation grounded in the actual results.

---

## A. Competencies this project genuinely demonstrates

| Competency | Evidence in the project |
|---|---|
| Translating a business problem into analytical questions | Objective-to-analysis mapping; every output tied to a lending decision (limits, review routing, monitoring) |
| Data quality assessment and cleaning | Duplicate detection (and spotting that the copies sat in two file blocks), invalid-value handling, informative-missingness analysis, full cleaning log with record reconciliation |
| Investigating anomalies rather than hiding them | Found 428 defaulted records whose loan-to-income field disagreed with its components; recomputed, flagged and ran a sensitivity check |
| Advanced Excel | Structured tables with calculated columns, `COUNTIFS`/`SUMIFS`/`AVERAGEIFS`/`MINIFS`/`MAXIFS`, `INDEX`/`MATCH`, array formulas, `SUMPRODUCT`-based statistics, data validation, conditional formatting, defined names, interactive charts, a Solver-ready log-likelihood |
| Statistical reasoning | Chi-square tests with Cramér's V, Welch t-tests, Cohen's d, assumption checks, using effect sizes when p-values are uninformative, a within-grade test for confounding |
| Predictive modelling and validation | Stratified train/test split, likelihood-ratio variable selection, linearity check, cross-validated tree tuning, baseline comparison, ROC/AUC, KS, gains, calibration, cost-based threshold choice |
| Credit-risk domain knowledge | PD, risk bands, Weight of Evidence / Information Value, Gini, affordability (LTI), awareness of reject inference, LGD/EAD gaps |
| Building a usable business tool | Dashboard with filters and alerts, applicant scorer with input validation, settings sheet, QA sheet, in-workbook documentation |
| Communicating to decision-makers | Live findings sheet, prioritised recommendations, monitoring indicators, plain-English README |
| Professional integrity | Clear disclosure of supporting tools, what was and was not tested, data provenance and limitations |

**Not claimed:** SQL, Power BI, production model deployment, or work on a real lender's data — none of these were part of this project.

---

## B. Job roles this project supports

| Role | What to highlight |
|---|---|
| **Credit Risk Analyst / Risk Analytics Analyst** (banks, microfinance, digital lenders) | PD modelling, WoE/IV, Gini/KS, risk bands, segment-based policy rules, KRIs, the LTI × housing finding |
| **Data Analyst (fintech / lending)** | End-to-end workflow, data-quality investigation, dashboard, translating results into rules that touch < 8% of lending but target a third of defaults |
| **Business Intelligence Analyst** | Interactive dashboard design (wildcard filters, charts that ignore their own filter, alert logic), KPI definitions, reconciled reporting |
| **Financial Data Analyst** | Value-weighted vs count-based default rates, pricing-vs-grade analysis, cost-based threshold logic |
| **Analytics Consultant** | Problem framing, prioritised recommendations with assumptions, honest limitations, stakeholder-ready documentation |
| **Research Analyst** | Hypothesis testing with effect sizes, confounding checks, transparent methodology and reproducibility |

---

## C. CV project entry

**Loan Portfolio Credit Risk Analysis & Monitoring Tool** — *Portfolio project (public practice dataset)*
*Tools: Microsoft Excel (advanced formulas, structured tables, data validation, conditional formatting, charts), Python (pandas, statsmodels, scikit-learn), Power Query*

- Analysed 32,581 loan records for a lending-institution case study to profile portfolio risk, identify default drivers and build a credit-risk monitoring tool.
- Cleaned and validated the data (165 duplicates, 18 invalid or placeholder values, explicit missing-data categories) and uncovered a loan-to-income inconsistency affecting 428 defaulted records; a sensitivity check showed conclusions were robust.
- Built a 21-sheet Excel tool with ~620,000 live formulas: interactive dashboard with drop-down filters and risk alerts, chi-square and Welch t-tests with effect sizes, Weight of Evidence/Information Value, a 140-segment risk ranking and an applicant risk scorer.
- Implemented a logistic regression and a 32-rule decision tree as Excel formulas; on a 30% hold-out the tree reached AUC 0.905 versus 0.728 for the existing loan grade, catching 68% of defaults with 96% precision at a 50% threshold.
- Found that renters borrowing 30%+ of income (7.8% of loans) generated 33.9% of all defaults (94.8% default rate) and recommended loan-to-income policy rules and monitoring indicators.

*Short version (one line):* Built an Excel credit-risk monitoring tool on 32k loans — dashboard, statistical driver analysis, segment ranking and two PD models (tree AUC 0.905 vs 0.728 for grade alone) — and identified a renter/loan-to-income rule covering a third of defaults.

---

## D. Interview preparation

**1. Walk me through this project in two minutes.**
A lender wanted to understand its loan book and monitor credit risk better. I had 32,581 historical loans with borrower details and repayment outcomes. I assessed and cleaned the data, then answered four questions: how risky is the book, what drives default, where risk concentrates, and can we predict it. About 22% of loans defaulted. Loan-to-income was the strongest driver — default jumps from about 21% to 64% once a loan passes 30% of income — and renters above that line defaulted 95% of the time, accounting for a third of all defaults. I built a logistic regression and a decision tree, implemented both as Excel formulas, and the tree reached an AUC of 0.905 on held-out data versus 0.728 for the lender's own grade. Everything is packaged in an Excel tool with a filterable dashboard, a segment ranking, a model comparison and an applicant scorer.

**2. What data-quality problems did you find, and how did you decide what to do with each?**
I found 165 exact duplicates, five impossible ages, two impossible employment lengths, eleven 6.00% "placeholder" rates in grades where 6% is far below the normal price, and missing employment length and interest rate. I didn't apply one rule to everything. Duplicates were removed because the second copies sat in two contiguous blocks of the file, which looks like an overlapping extract. Records with ages of 123 and 144 were excluded because the same records had other implausible values. Missing values were kept as explicit categories — and that mattered, because borrowers with unknown employment defaulted at 32% versus 22% overall, so deleting them would have hidden a risk signal.

**3. You mentioned a loan-to-income inconsistency. Tell me about it.**
The dataset includes a supplied loan-as-percent-of-income field. When I recomputed it from loan amount and income, 428 records disagreed beyond rounding — and every one was a default. That pattern is a red flag: it could mean amounts were changed after the outcome, or something about how the data was produced. I used the recomputed value, flagged the records and reran the key analysis with the supplied field. Band default rates moved by at most 2.5 points and the conclusions didn't change, so I documented it as a limitation rather than letting it drive the results.

**4. Why use chi-square tests and Cramér's V rather than just default rates?**
Default rates show the pattern; the test tells me whether it could be chance. But with 32,000 loans almost everything is "significant" — even age, which has a p-value around 0.000004 and practically no effect. So I ranked factors by Cramér's V, an effect size. That separated real drivers like loan-to-income (0.43) and grade (0.42) from negligible ones like age and credit-history length (about 0.03).

**5. Interest rate is strongly related to default. Why isn't it in your logistic model?**
Because the rate is set from the grade. Overall, defaulters paid about 2.6 points more, but when I split each grade at its median rate, loans priced above and below the median defaulted at almost the same rate — for grade C it was 20.8% in both halves. Adding the rate to a model that already had grade changed the test AUC by less than 0.001. So the rate's strong raw association is really the grade showing through.

**6. How did you build the models, and how did you make sure they weren't overfitting?**
I split the data 70/30, stratified on the outcome, and only used the test set once at the end. For the logistic regression I tested which candidates added information with a likelihood-ratio test and added a squared loan-to-income term after a linearity check. For the tree I capped depth at six so it stays readable and can run as an Excel formula, and chose the minimum leaf size by five-fold cross-validation. Training and test AUCs were almost identical for both models (0.881 vs 0.880; 0.906 vs 0.905), so there's no sign of overfitting.

**7. Why did the decision tree beat the logistic regression?**
Because the risk is driven by interactions. A high loan-to-income ratio is far more dangerous for a renter than for a homeowner — 95% versus 24% default at the same LTI. A main-effects logistic model adds those effects together and can't capture that, while a tree splits on housing *within* the high-LTI branch. The trade-off is that the tree gives only 32 distinct probabilities, so it's coarser for pricing.

**8. What proportion of defaults can the model identify?**
It depends on the threshold. At a 50% PD cut-off, the tree catches 68% of defaults, and 96% of what it flags really does default. If a missed default costs five times as much as turning away a good borrower, the lowest-cost threshold is 0.18, where it catches 74% of defaults while flagging only about 4% of good loans. I built the threshold and cost ratio as inputs so the business can set them once Finance agrees the real costs.

**9. How did you implement the models in Excel?**
The logistic coefficients sit in a parameter table, and each loan's score uses `SUMIFS` to look up its grade, housing and purpose effects plus named cells for the continuous terms, then `1/(1+EXP(-logit))`. I also recompute the log-likelihood in Excel, so the coefficients can be re-checked with Solver. The tree is a six-level nested `IF` in the table, and I verified that all 32,411 loans land in exactly the same leaf as the original model. Evaluation is all `COUNTIFS`: confusion matrices, a 101-point ROC table for AUC, gains and calibration.

**10. What would you recommend the lender do first?**
Three things straight away: put a review threshold at 30% loan-to-income, treat renters above that line as decline-or-restructure, and make employment length a mandatory, verified field. Then, in the medium term, pilot the tree score as a second-line check and review pricing for grades D–G, where default rates of 59–98% are very unlikely to be covered by 15–20% interest.

**11. What are the main limitations?**
The data has no dates, so I can't look at trends or validate the model out of time. There's no loss data, so I can measure how often loans default but not how much the lender loses. Only approved loans are included, so the models know nothing about applicants who were turned down. And some segments default at exactly 100%, which is unusual in real lending and suggests the dataset may be partly rule-generated — so real-world accuracy would be lower than what I measured.

**12. If you had more time or a different tool, what would you do next?**
I'd validate the rules on recent, dated data and add loss given default so the threshold can be set on expected loss rather than an assumed cost ratio. On a proper modelling platform I'd try gradient boosting — as a benchmark it reached an AUC of 0.944 here, versus 0.905 for the tree — with monitoring for drift and governance around it. And I'd connect the Excel tool to a refreshed data source through Power Query so the dashboard updates automatically each month.

---

### Talking points to keep handy

- 32,411 loans · 21.9% default · 310.9m lent · 24.8% of value in defaulted loans
- LTI: 21% → 64% default across the 30% line · Cramér's V 0.43
- Renters with LTI ≥ 30%: 7.8% of loans, 33.9% of defaults, 94.8% default rate
- 16 segments ≥ 50% default hold 15% of loans and 55% of defaults
- AUC: tree 0.905 · logistic 0.880 · grade alone 0.728
- At 50% threshold: tree recall 68%, precision 96%
