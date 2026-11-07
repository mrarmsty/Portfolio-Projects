# Project brief

## Business problem

The company runs an e-commerce marketplace on the web, an Android app and an iOS app. Its Product Manager can see traffic and orders, but cannot see how users get from one to the other. They want to know:

- how users engage with the platform;
- where users abandon their shopping journeys;
- which products and behaviours are associated with purchases.

The answers will set priorities for the next product cycle: what to fix in the funnel, which products to promote or repair, and which users to target for retention.

**Role:** Product Data Analyst.
**Stakeholder:** Product Manager. Secondary readers are the growth, merchandising and engineering leads.
**Tool:** SQL (SQLite), on the supplied event database.

## Objectives and success measures

| # | Objective | What a useful answer looks like |
|---|---|---|
| 1 | Measure user engagement with the digital platform | Unique users, sessions, product views, interactions per session, return frequency, most-viewed products, weekly trend |
| 2 | Analyse the conversion funnel from product views to purchases | User counts and rates at view → cart → checkout → order, at user and session level |
| 3 | Identify stages at which users abandon their shopping journeys | The largest drop-off, where it is worst (platform, device, source), and what users do after adding to cart |
| 4 | Examine product and category performance | Most-viewed products, best converters (statistically fair), whether popularity predicts purchases, category purchase activity, products with high cart abandonment |
| 5 | Analyse returning-user behaviour and retention | Share returning, return within 1 / 2 / 4 weeks, weekly cohort matrix, which groups return more |
| 6 | Identify opportunities to improve conversion and engagement | Sized opportunities with evidence and recommended actions |

## Scope

- **In scope:**
  - all 26 weeks of the supplied data (7 Jul 2025 – 4 Jan 2026);
  - all platforms, users, products and orders;
  - descriptive and diagnostic analysis.
- **Out of scope:**
  - causal attribution (no experiments in the data);
  - forecasting;
  - marketing spend and profitability (no cost data);
  - inventory.

## Objective-to-analysis mapping

| Objective | Business question | SQL output (file in `outputs/results/`) | Technique | Derived table / view |
|---|---|---|---|---|
| 1 Engagement | How many unique users? How many product views? | Q01_platform_overview | Scalar subqueries | user_summary, session_summary |
| 1 | Interactions per session | Q02_session_engagement | Conditional aggregation, median via ROW_NUMBER | session_summary |
| 1 | How frequently do users return? | Q03_return_frequency, Q03b_time_between_sessions | CASE bucketing, running SUM, LAG gaps | user_summary, session_summary |
| 1 | Engagement over time | Q04_weekly_engagement_trend, Q27/Q28 | LAG week-over-week, 4-week and 7-day moving averages, running totals | vw_weekly_kpis, vw_daily_kpis |
| 1 | Engagement by platform | Q05_engagement_by_platform | GROUP BY, window share, pp vs overall | session_summary |
| 1 | Most-viewed products | Q06_top_viewed_products, Q06b_view_concentration | RANK, cumulative share window | product_performance |
| 2 Funnel | Users who viewed / carted / checked out / purchased | Q07_user_funnel | Closed funnel, LAG, RANK of drop-off | user_summary, vw_user_funnel |
| 2 | Are event and order purchases consistent? | Q07b_purchase_reconciliation | Reconciliation | orders, events |
| 2 | Funnel within a session | Q08_session_funnel | Closed session funnel | session_summary |
| 2 / 3 | Where is the funnel weakest by segment? | Q09_funnel_by_segment | Conditional aggregation, pp vs overall | session_summary |
| 3 Abandonment | When do carts turn into orders? | Q10_cart_to_order_timing | UNION ALL timeline, running MAX over a ROWS frame ending 1 PRECEDING, CASE buckets, running SUM | events, orders |
| 3 | What happens right after add-to-cart? | Q11_after_add_to_cart | LEAD over the session sequence | events_enriched |
| 3 | Checkout abandonment by platform and device | Q12_checkout_abandonment | Conditional aggregation, RANK, UNION ALL total row | session_summary |
| 3 | Overall cart abandonment | Q12b_cart_abandonment_overall | Censored 7-day outcome | cart_add_outcomes |
| 4 Products | Do popular products generate the most purchases? | Q13_popularity_vs_purchases, Q13b, Q26_product_quadrants | Spearman rank correlation in SQL, overlap of top-N lists, median quadrants | product_performance, vw_product_scorecard |
| 4 | Highest view-to-purchase conversion | Q14_top_conversion_products | Wilson 95% lower bound, minimum sample of 500 viewers | product_performance |
| 4 | High interest, low conversion | Q15_high_interest_low_conversion | NTILE quartiles, category benchmark via windowed SUM | product_performance |
| 4 | Categories with highest purchase activity | Q16_category_performance | DENSE_RANK, window shares | category_performance |
| 4 | Products with high cart abandonment | Q17_cart_abandonment_products, Q17b | Minimum of 100 observed additions; category and overall benchmarks; NTILE price quintiles | product_performance, cart_add_outcomes |
| 1 / 4 | Do promotions change behaviour? | Q18_promotion_periods | Calendar join, per-day normalisation | session_summary, calendar |
| 5 Retention | Users who return after their first interaction | Q19_returning_users | Censoring-aware 7 / 14 / 28-day flags, median | user_summary |
| 5 | Activity across weekly cohorts | Q20_cohort_retention_matrix | Recursive CTE, conditional pivot | cohort_retention |
| 5 | Share returning after 1, 2 or 4 weeks | Q21_retention_week_1_2_4 | Weighted pooling over observed cohorts, three populations | cohort_retention, user_summary |
| 5 | Are newer cohorts better or worse? | Q22_cohort_quality_trend | LAG change in week-1 retention | cohort_retention |
| 5 | Groups with stronger repeat engagement | Q23_segment_repeat_engagement | UNION of dimensions, RANK within dimension, pp vs overall | user_summary |
| 5 | Repeat purchase | Q24_repeat_purchase | LAG between orders, median | orders |
| 6 Opportunities | Where is the biggest prize? | Q25_opportunity_summary | Consolidation of funnel, abandonment and retention outputs | all |

## Key definitions

See [`kpi_definitions.md`](kpi_definitions.md) and [`data_quality_and_cleaning_log.md`](data_quality_and_cleaning_log.md).

## Deliverables

- One SQL file covering setup, loading, data quality, cleaning, analysis, views and validation.
- Exported results and cleaned tables.
- Charts.
- A data dictionary.
- A data-quality and cleaning log.
- An analyst report (DOCX and PDF).
- A README.
- A QA checklist.
- Portfolio material.
