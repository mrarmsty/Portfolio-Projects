# Portfolio positioning

## What this project demonstrates

| Competency | Evidence in this project |
|---|---|
| Relational modelling and data loading | DDL with PK, FK, UNIQUE and CHECK constraints (including arithmetic rules such as `order_total = items_subtotal + shipping_fee`); read-only attach of the source; TEMP staging table; load audit |
| Data-quality assessment | 19-check register across completeness, uniqueness, validity, consistency, integrity and timeliness; tracking loss detected and handled |
| Advanced SQL | Multi-CTE pipelines; recursive CTE; ROW_NUMBER, RANK, DENSE_RANK, NTILE, LAG and LEAD; running totals, moving averages and custom ROWS frames; FILTER; correlated EXISTS; conditional aggregation |
| Statistics in SQL | Medians via ROW_NUMBER; Spearman rank correlation with tied ranks; Wilson 95% lower bound for ranking conversion |
| Product analytics | User and session funnels, cart and checkout abandonment, cohort retention, censoring-aware return rates, product quadrants, promotion analysis |
| Analytical judgement | Chose orders as the system of record; preferred the user funnel over the session funnel because of cross-session journeys; corrected for left- and right-censoring; flagged reverse causation and seasonal confounding |
| Performance tuning | Diagnosed query-planner problems (wrong index choice, nested scans) and rewrote them as pre-aggregated anti-joins and indexed EXISTS: one step went from 116 s to 0.2 s, and the full build runs in about 35 s |
| Testing and validation | 27 reconciliation and business-rule checks (all PASS); a seeded-error test showing the checks catch problems; identical results from two execution paths |
| Communication | Findings written into the SQL as comments; insights in finding / evidence / interpretation / implication / action form; analyst report; charts |

## Roles this project supports

| Role | Why it is relevant |
|---|---|
| Product Data Analyst / Product Analyst | Funnel, abandonment, retention and product-performance analysis for a Product Manager. This is the exact brief. |
| Data Analyst (e-commerce / retail) | Category and product performance, promotions, repeat purchase, revenue reconciliation |
| Growth / Marketing Analyst | Acquisition-channel quality, paid-social diagnosis, cohort retention, promotion cohorts |
| Analytics Engineer (junior) | Layered SQL model (staging → typed tables → derived tables → views), constraints, tests, reproducible build script |
| BI Analyst | Reusable views (`vw_daily_kpis`, `vw_weekly_kpis`, scorecards, cohort view) ready for a BI tool |
| CRM / Lifecycle Analyst | First-week retention window, repeat-purchase timing, cart-reminder opportunity |

## CV entry

**E-commerce Product Analytics in SQL** (SQLite; synthetic marketplace data, 590k events, 30k users)

- Built a constrained SQLite model from a raw event database, including staging, 19 data-quality checks and 27 automated validation checks. The build runs end to end in about 35 seconds.
- Wrote 34 analytical queries (Q01–Q28) and 8 reusable views using recursive CTEs, window functions (LAG/LEAD, NTILE, running totals, moving averages), Spearman correlation and Wilson intervals in pure SQL.
- Found that 56.8% of product viewers never add to cart, and that mobile-web checkout abandonment is 37.2% against 21.3% on desktop. Sized the mobile-web gap at about 490 orders over 26 weeks.
- Showed that product popularity does not predict conversion (ρ = −0.18). Identified 19 high-traffic, low-conversion products and a set of under-exposed high converters for merchandising.
- Measured cohort retention with left- and right-censoring corrections (W1 26.5%, W4 11.0%), and showed that retention is decided in the first week.

## Interview questions and answers

**1. Why did you use the orders table rather than purchase events to count purchases?**
The reconciliation (Q07b, DQ08) showed that 206 orders (3%) have no purchase event: the event stream loses data. Orders are the transactional system of record, so they define purchases. Events are used for behaviour before the purchase, and the gap is reported as a tracking issue.

**2. Why is the user-level funnel your primary funnel and not the session funnel?**
28% of orders were placed in a session with no add-to-cart, because the cart was filled earlier (DQ11). A session funnel treats those journeys as abandonment followed by an unexplained order. The closed user funnel follows the person across sessions. I still show the session funnel, because it answers a different question: what happens within a single visit.

**3. How did you handle censoring in retention?**
There are two forms.

- *Right-censoring:* users first seen near the end of the window cannot yet show a 28-day return. Their return flag is NULL, and they are excluded from the denominator. Cohort cells exist only for weeks that have been observed.
- *Left-censoring:* the data starts on 7 July, so customers who existed before then look new in weeks 1–2. I flagged the 6,000 users who signed up before the window and reported retention three ways: all users, cohorts 3–26, and users not registered before the window.

**4. How do you rank products by conversion without small products winning?**
I used the Wilson 95% lower bound, computed in SQL, together with a minimum of 500 viewers. A product with 2 buyers out of 5 viewers has a 40% raw rate, but a wide interval and a low lower bound. So products rank high only when the evidence is strong.

**5. How did you compute a Spearman correlation in SQLite?**
I converted views and conversion to ranks, using `RANK()` plus half the number of ties to get average ranks. Then I applied the Pearson formula to the ranks with SUMs and `sqrt()`. The result for views vs conversion is −0.18: popular products do not convert better.

**6. A query took two minutes. What did you do?**
The query plan showed SQLite choosing the event_type index for a correlated NOT EXISTS, which scanned every cart event for each order. In another case, joining two DISTINCT subqueries forced nested scans. I rewrote them as a pre-aggregated CTE with an anti-join, and as EXISTS against an indexed purchases table with composite indexes. The product step fell from 116 s to 0.2 s.

**7. How do you know your derived tables are right?**
Section 7 runs 27 checks:

- row counts against source;
- no duplicate keys and no foreign-key violations;
- event, session, order and unit totals reconcile;
- net revenue reconciles across four layers;
- funnel stages never increase from one stage to the next;
- week-0 retention is 100%;
- rates are within [0, 1].

All pass. I then deleted a session and altered a product total in a copy, and six checks failed as expected. That shows the checks can detect errors, not just pass.

**8. Is the high retention of loyalty members evidence that the loyalty programme works?**
No. Loyalty status is recorded at extract date, and engaged users are the ones who join. The 88.5% vs 39.7% difference is an association that may run in reverse. To test the programme you would randomise the invitation and compare retention against a control group.

**9. Black Friday cohorts retained worse. Does that mean promotions bring poor customers?**
It is consistent with that, but it is not proven. Those cohorts reach week 4 in late December, when activity drops for everyone. To separate the two effects you would compare against non-promotion cohorts acquired at the same time of year, or use a longer history.

**10. What single recommendation would you make to the Product Manager?**
Fix the mobile-web checkout. It is the largest segment by sessions, and the checkout gap against desktop (37.2% vs 21.3% abandonment) appears among users who have already shown strong intent. That makes it the most direct path to more orders. I would audit the flow and A/B test the fixes, measuring the checkout → order rate on web mobile.

**11. Why not just report "conversion rate"?**
Because there are several, and they answer different questions:

| Rate | Value |
|---|---:|
| Session conversion | 7.7% |
| Viewer → buyer conversion (user funnel) | 17.4% |
| Checkout → order conversion | 79.1% |
| Product view-to-purchase conversion (catalogue median) | 3.9% |

The KPI definitions file states the numerator and denominator of each, so stakeholders do not compare unlike rates.

**12. What would you do next with more data?**
- Page-level and checkout-step events, to see *why* users drop at each step.
- Marketing spend, to judge channel return.
- A longer history, to separate seasonality.
- Experiment data, to turn the associations in this analysis into causal estimates.
