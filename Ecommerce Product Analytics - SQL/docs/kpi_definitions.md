# KPI definitions

Every KPI below is computed in SQL. Each one names the object it comes from and the value from the tested run (26 weeks, 7 Jul 2025 – 4 Jan 2026).

| KPI | Definition | Numerator / denominator | Source | Value |
|---|---|---|---|---:|
| Unique users | Distinct users with at least one session | – | user_summary | 30,000 |
| Sessions | Distinct sessions | – | session_summary | 89,557 |
| Product views | product_view events, including the 1,414 that cannot be traced to a product | – | events | 311,955 |
| Product interactions per session | product_view + add_to_cart + remove_from_cart + purchase events ÷ sessions | events ÷ sessions | Q02 | 3.99 (median 3) |
| Sessions per user | Sessions ÷ users | | Q01 | 2.99 (median 1) |
| Weekly active users (WAU) | Distinct users with a session in the Monday-start week | | vw_weekly_kpis | 1,857 – 3,441 |
| Returning user rate | Users with a session on a later calendar day ÷ all users | | Q19 | 42.2% |
| Return within N days | Returned within N days ÷ users with at least N days of follow-up | censored users excluded | Q19 | 31.4% / 39.4% / 43.2% (7 / 14 / 28 days) |
| Week-N retention | Cohort users active in week (cohort + N) ÷ cohort users, pooled over cohorts where week N is observed | | Q21 | W1 26.5%, W2 19.3%, W4 11.0% |
| View → cart rate (user) | Viewers who added to cart ÷ product viewers | closed funnel | Q07 | 43.2% |
| Cart → checkout rate (user) | Cart users who began checkout ÷ cart users | closed funnel | Q07 | 50.9% |
| Checkout → order rate (user) | Checkout users who ordered ÷ checkout users | closed funnel | Q07 | 79.1% |
| Viewer → buyer rate (user) | Buyers ÷ product viewers | closed funnel | Q07 | 17.4% |
| Session conversion | Sessions containing an order ÷ sessions | | Q05, vw_daily_kpis | 7.7% |
| Checkout abandonment | Sessions with begin_checkout and no order ÷ sessions with begin_checkout | | Q12 | 29.7% |
| Cart abandonment | Traceable cart additions not ordered by the same user within 7 days ÷ additions with a 7-day outcome | censored additions excluded | Q12b | 67.9% |
| Product view-to-purchase rate | Viewers of the product who later ordered it ÷ viewers of the product | | product_performance | catalogue median 3.9% |
| Wilson lower bound | 95% lower confidence bound of the view-to-purchase rate; ranks conversion fairly across sample sizes | z = 1.96 | product_performance | – |
| Category view-to-purchase rate | Users who viewed any product in the category and ordered any product in it ÷ category viewers | | category_performance | 5.2% – 15.9% |
| Net order | Order whose status is not cancelled or returned | | orders | 6,235 of 6,896 |
| Net revenue | Sum of `items_subtotal` of net orders (excludes shipping) | | orders | 512.2m (NGN assumed) |
| Average net order value | Net revenue ÷ net orders | | Q01 | 82,149 |
| Repeat buyer rate | Buyers with two or more orders ÷ buyers | | Q24 | 28.4% |

## Conventions

- A **closed funnel** counts a user at a stage only if they also reached every earlier stage.
- A **percentage point (pp)** difference is the segment rate minus the overall rate.
- **Medians** are computed with ROW_NUMBER, because SQLite has no median function.
- **Rates in the result files** are percentages rounded to 1 or 2 decimals.
- **Rates in the derived tables** are stored as 0–1 fractions.
