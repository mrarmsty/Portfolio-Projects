# Portfolio positioning - Grocery Demand Planning and Forecasting (Python)

*The data is synthetic and the company fictional. Present the results as findings from a simulated business, not real-world impact.*

## A. Competencies demonstrated

| Competency | Evidence in this project |
|---|---|
| Translating a business problem into analysis | Six objectives and 14 questions mapped to data, methods and outputs before any analysis |
| Data quality assessment and cleaning | 12 logged cleaning rules on a raw POS feed (mixed dates, label variants, duplicate and superseded loads, test till, sign errors, kobo values, missing values); independent 100% reconciliation |
| Data transformation and feature engineering | Complete daily panel with an explained status for every missing day; calendar, festival and promotion features; leak-free lag features; a two-tier bulk-order rule that improved on the provider's flag |
| Statistical analysis | Kruskal-Wallis and Mann-Whitney tests, STL decomposition and seasonal strength, per-family log-linear regression with clustered standard errors, Wilcoxon signed-rank test, Spearman correlation |
| Time-series forecasting and model evaluation | Rolling-origin back-test of six methods (naive rules, Holt-Winters ETS, gradient boosting), WAPE / bias / weekly WAPE, leakage control, permutation importance |
| Operations and supply-chain analytics | Safety stock from empirical forecast error over lead time + review period, order-up-to levels in case packs, shelf-life check, policy comparison |
| Business interpretation and recommendations | Prioritised actions (now / next quarter / longer term), each tied to evidence |
| Communication and documentation | Annotated notebook, technical report, README, data dictionary, cleaning log, KPI definitions |
| Analytical integrity | Confounding acknowledged, a non-significant model difference reported, an inflated festive finding corrected after better outlier handling, limitations stated |

## B. Job roles supported

| Role | Most relevant parts |
|---|---|
| **Data Analyst** | Cleaning pipeline, KPI analysis, statistical tests, clear interpretation |
| **Demand Planning / Supply Chain Analyst** | Forecast back-test, Q1 forecast, safety stock and order-up-to policy, store risk ranking |
| **Retail / Commercial Analyst** | Category and store performance, promotion uplift by family, mechanic and store, promotion diagnosis |
| **Business Intelligence Analyst** | KPI definitions, reconciled reporting tables, charts ready for dashboards |
| **Data Scientist (junior)** | Gradient-boosting forecasting with leakage control, model comparison and feature importance |
| **Product / Pricing Analyst** | Promotion effects, discount depth vs uplift, post-promotion pull-forward |

## C. CV project entry

**Grocery Demand Planning and Forecasting (Python)** | *Portfolio project, synthetic data*
- **Data:** cleaned and validated a 104,000-row daily POS extract for an 8-store grocery chain (12 documented rules, 100% reconciliation) and built a complete store-family daily panel for analysis.
- **Demand patterns:** quantified weekday, payday, seasonal and regional festival patterns with statistical tests and STL decomposition, and showed that naira growth (+80%) masked flat unit demand (-2%).
- **Promotions:** isolated promotion effects with per-family regression models. Uplift ranged from 8% (bread) to 40% (household cleaning), and multibuy outperformed price cuts. Diagnosed 113 under-performing promotion events (timing, stock-outs, pricing-execution failures).
- **Forecasting:** compared six methods in a rolling-origin back-test. A gradient-boosting model cut weekly forecast error from 14.1% to 9.9% WAPE against the current rule of thumb, and produced a Q1 2026 forecast.
- **Replenishment:** turned forecast error into a store-family safety-stock policy at a 97% service level, holding 20% less safety stock than the flat 2-day rule while raising cover for 13 at-risk series.
- **Tools:** Python (pandas, NumPy, SciPy, statsmodels, scikit-learn, Matplotlib), Jupyter.

## D. Interview preparation

**1. What was the business problem, and how did you scope it?**
The chain had inconsistent demand and planned with rules of thumb, including two days of safety stock for every product everywhere. I translated that into six objectives:
- describe sales;
- find seasonal patterns;
- measure promotions;
- compare stores;
- forecast;
- turn the forecast into ordering rules.

I mapped each to the data and method I would use, so every chart or model had to answer a business question.

**2. Why did you clean the raw feed yourself when a cleaned table was provided?**
The raw feed is the source of truth and I wanted to understand every decision. I logged 12 rules: date parsing, label standardisation, keeping the latest of repeated loads, dropping a test till, fixing sign errors, rescaling a month recorded in kobo and imputing a small number of missing values. I then reconciled my result with the provider's table. It matched on 100% of rows, which validated both. It also let me improve one thing: my bulk-order rule caught seven extreme B2B days that the provider's rule missed.

**3. Why didn't you treat missing days as zero sales?**
Because they weren't zero demand. They were Christmas closures, a refurbishment, till outages and the period before a new store opened. I built a full daily panel and gave every missing day a reason. Treating them as zeros would have dragged forecasts down and inflated volatility.

**4. How did you measure the effect of promotions, given they are not random?**
A simple promo vs non-promo comparison is confounded, because promotions cluster in certain months. I fitted a log-linear regression per product family with:
- store levels and trends;
- weekday by format;
- month, Christmas, January, Easter and Eid windows;
- payday, holidays and store events;
- the promotion and a 14-day post-promotion dip.

The promotion coefficient gives the controlled uplift. For each promotion at each store, I compared actual sales with the model's no-promotion prediction. I describe these as associations controlled for measured drivers, not proven causal effects.

**5. What surprised you in the promotion results?**
Two things:
- **Mechanic:** display-only promotions, with no price cut, delivered almost the same uplift as price discounts, and multibuy beat both.
- **Under-performing promotions:** 15% coincided with lower sales, but most were explainable. January promotions looked bad only because December was higher. Some promotions ran out of stock. In four cases the shelf price never changed, always in the same two stores, which points to an execution problem rather than a demand problem.

**6. Which forecasting methods did you compare, and how did you avoid overfitting or leakage?**
I compared six methods:
- last week's same day;
- a 4-week weekday average (the typical store rule);
- last year scaled to the current level;
- Holt-Winters ETS per series;
- two versions of a global gradient-boosting model.

To keep it honest:
- **Back-test:** I used a rolling-origin back-test with seven origins, each forecasting 28 days and trained only on earlier data.
- **No leakage:** every lag feature was at least as old as the horizon.
- **Scoring:** stock-out and bulk days were excluded from scoring, because their actual sales do not reflect demand.

**7. What were the results, and which model did you choose?**
Gradient boosting was best: daily WAPE 20.7% and weekly WAPE 9.9%, against 25.1% and 14.1% for the 4-week weekday average. The 91-day-lag version tied with the 28-day version (Wilcoxon p = 0.54), so I chose it because one model can forecast the whole quarter. It also tells you that recent weeks add little beyond the calendar, promotions and longer-run level.

**8. How did you turn the forecast into a replenishment recommendation?**
For each store-family I took the protection period (lead time + review period) and measured, from the back-test, the standard deviation of the cumulative forecast error over that period. Safety stock = 1.88 x that standard deviation for a 97% service level. The order-up-to level = forecast over the period + safety stock, rounded to full cases.

Against the flat 2-day rule:
- 37 series are over-stocked, mostly bread, dairy and fresh produce with daily local delivery;
- 13 are under-protected, mostly in Port Harcourt and Kano with 5-7-day lead times.

In total the policy holds 20% less safety stock. It needs 42% less than the same service level would with the naive forecast.

**9. Did the analysis show anything you couldn't fix with forecasting?**
Yes. Historical stock-outs were not related to the gap between recommended and current safety stock (Spearman about 0.03). Together with the promotion stock-outs, that suggests many shortages come from supply failures, not forecast error. So I recommended a separate supply-reliability review for Port Harcourt and Kano.

**10. What are the main limitations?**
- **Data:** the data is synthetic and at product-family level, not SKU level.
- **Censored demand:** stock-out days understate demand and lost sales are not recorded.
- **Promotion effects:** they are associations from observational data.
- **No cost data:** with no costs or inventory positions, recommendations are in units and service level rather than profit.
- **Safety-stock assumption:** the levels assume next quarter's errors look like the back-test's.

**11. What would you do next with more time or data?**
- Add inventory positions and lost-sales estimates so the model learns true demand on stock-out days.
- Move to SKU level with hierarchical reconciliation between SKU, family and store.
- Add margin and promotion cost data to optimise promotions for profit.
- Test promotion effects with controlled store-level experiments.
- Put the forecast into a weekly pipeline with monitoring of WAPE and bias.

**12. Was there a moment when your analysis changed a conclusion?**
Yes. My first bulk-order rule excluded festive windows, to avoid flagging genuine festive peaks. That meant an 18,000-unit B2B order four days before Eid in Kano slipped through and made the Eid peak look like 2.7x normal. I added a second tier for extreme spikes (more than 8x, far above any festive peak), and the Eid effect corrected to 1.6x. It reinforced why I check outliers before interpreting peaks.
