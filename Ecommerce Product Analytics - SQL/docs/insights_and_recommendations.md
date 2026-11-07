# Insights and recommendations

Every number below comes from a SQL output in `outputs/results/`. The data is observational, so the findings describe associations, not causes. Where a figure sizes an opportunity, it shows the scale of a gap under a stated assumption; it is not a forecast.

## Key insights

### 1. The largest leak is between viewing a product and adding it to cart

- **Finding:** 56.8% of product viewers (15,240 of 26,810 users) never added anything to cart over 26 weeks. This is the largest drop-off in the funnel. The next largest is cart → checkout at 49.1%; checkout → order loses 20.9%.
- **Evidence:** Q07_user_funnel, Q25_opportunity_summary, chart 01.
- **Interpretation:** Most users browse without buying. Product pages, or the products shown, do not persuade a majority of viewers to commit.
- **Implication:** This is the biggest pool of users. A small rate gain here moves more users than the same gain at checkout.
- **Action:** Test product-page changes on the highest-traffic, lowest-converting products first (see insight 5): delivery date and cost shown on the page, review content, size and spec information, and stock status.

### 2. The cart is used as a shortlist, and journeys span sessions

- **Finding:** After an add-to-cart, 38.6% of users next view another product and 17.0% search; only 6.6% go straight to checkout. 67.9% of cart additions are not bought within 7 days. 28% of orders complete a journey started in an earlier session, and 9.3% of orders come more than 7 days after the last add-to-cart.
- **Evidence:** Q11, Q12b, Q08, Q10, DQ11.
- **Interpretation:** Users compare and come back. A session-only view of the funnel would understate conversion and overstate abandonment.
- **Implication:** Cart persistence and reminders matter more than in-session nudges.
- **Action:**
  - Make the cart persist across devices and sessions.
  - Add "save for later".
  - Test a cart reminder 24–72 hours after an addition. Email is the channel whose users return most (insight 8).

### 3. Mobile-web checkout loses far more buyers than desktop

- **Finding:** 37.2% of web-mobile checkout sessions end without an order, against 21.3% on web desktop (29.7% overall). Web mobile is the largest segment (38.6% of sessions) and has the lowest session conversion (5.6% vs 11.7% on desktop).
- **Evidence:** Q12, Q05, Q09, chart 06.
- **Interpretation:** The same intent (a user who reached checkout) finishes far less often on the mobile website. This points to friction in the mobile checkout flow rather than to lower intent.
- **Implication:** Suppose web-mobile checkouts had completed at the web-desktop rate. Then about 490 more of its 3,101 checkout sessions would have ended in an order over the 26 weeks, equal to 7% of all orders. This sizes the gap; it is not a forecast.
- **Action:** Audit the mobile-web checkout: form length, payment options (pay on delivery is the second most used method), page speed, and errors. Then A/B test the fixes.

### 4. Paid social brings low-intent users who rarely buy or return

- **Finding:**
  - Paid-social sessions add to cart less often than any other traffic source (18.0% vs 28.5% overall) and convert at 3.6% (overall 7.7%).
  - Users acquired through paid social have the lowest 28-day return (25.0% vs 43.2%).
- **Evidence:** Q09, Q23, chart 07.
- **Interpretation:** Paid social drives visits but not purchase intent.
- **Implication:** Judging the channel on traffic overstates its value. The data has no cost information, so return on spend cannot be assessed here.
- **Action:** Evaluate paid-social campaigns on downstream metrics (add-to-cart, orders, 28-day return) and review targeting and creative.

### 5. Popular products do not convert better

- **Finding:**
  - Views correlate moderately with units sold (Spearman ρ = 0.52), but weakly and negatively with conversion (ρ = −0.18).
  - 75 "traffic without sales" products take 47.4% of views but only 20.6% of units (2.5% conversion). The 51 "star" products take 33.7% of views and 53.4% of units (7.4%).
  - 19 products sit in the top view quartile and the bottom conversion quartile. Stride Chinos F33 is the largest gap: 9,337 views, 2.5% conversion against 4.1% for Fashion, and 86.6% cart abandonment.
- **Evidence:** Q13, Q13b, Q15, Q26, chart 04.
- **Interpretation:** Traffic is allocated to products that do not turn attention into orders. Some may be over-promoted; others may have a page, price or stock problem.
- **Implication:** If the 19 products converted at their category rate, they would add about 656 product purchases. This sizes the gap; it is not a forecast.
- **Action:**
  - Review the 19 products (price, images, size and spec information, reviews, stock).
  - Test giving more placement to "hidden gem" products (75 products, 7.0% conversion, only 11.4% of views).

### 6. Everyday consumables drive purchase activity

- **Finding:**
  - Health & Beauty (1,699 orders) and Groceries (1,505) lead orders and viewer conversion (15.5% and 15.9%), and have the lowest cart abandonment (62.9%, 63.9%).
  - All five of the best converters with at least 500 viewers are everyday consumables (instant noodles, skincare, baby wipes).
- **Evidence:** Q14, Q16, Q17b, charts 05 and 08.
- **Interpretation:** Low-price, repeat-need items convert readily.
- **Implication:** They are a natural entry point for new users and a basis for repeat purchase.
- **Action:** Test replenishment reminders or subscribe-and-save on consumables, and use them in first-purchase offers.

### 7. Retention is decided in the first week

- **Finding:**
  - 55.7% of users were seen in only one session.
  - Week-1, week-2 and week-4 retention are 26.5%, 19.3% and 11.0%. For users not registered before the window, they are 20.0%, 13.8% and 6.8%.
  - Users who come back do so fast: the median time to return is 4 days, and 78.3% of repeat sessions come within 7 days of the previous one.
- **Evidence:** Q03, Q03b, Q19, Q21, chart 03.
- **Interpretation:** A user who has not returned within about a week is unlikely to return at all.
- **Implication:** Re-engagement effort is most valuable in days 1–7.
- **Action:** Build a first-week programme for new users (welcome, recently viewed, cart reminder), triggered by inactivity rather than by calendar date.

### 8. Email, direct, registered and loyalty users return far more, but the direction is unclear

- **Finding:** 28-day return rates by group:

  | Group | 28-day return | Overall |
  |---|---:|---:|
  | Email-acquired users | 71.7% | 43.2% |
  | Direct-acquired users | 61.8% | 43.2% |
  | Registered users | 74.2% | 43.2% |
  | Loyalty members | 88.5% | 43.2% |

  City and device differ by no more than 2.3 pp.
- **Evidence:** Q23.
- **Interpretation:** Registration and loyalty status are recorded at extract date. Engaged users are more likely to register and join, so these associations may run in reverse.
- **Implication:** Pushing registration or loyalty sign-up will not necessarily raise retention.
- **Action:** Test registration and loyalty prompts with a randomised experiment before scaling them.

### 9. Black Friday doubled traffic, but its cohorts retained worse

- **Finding:**
  - Black Friday days averaged 864 sessions a day against 450 with no promotion, and 9.4% session conversion against 7.4%, but a lower average net order value (78,570 vs 82,554).
  - The two Black Friday cohorts were unusually large (1,395 and 2,166 users; most weekly cohorts had about 1,000), but their week-4 retention was 4.9–5.3%, against 9–13% for August–October cohorts.
- **Evidence:** Q18, Q22, charts 02 and 03.
- **Interpretation:** This fits deal-driven acquisition. However, these cohorts reach week 4 during the late-December slowdown, so the two effects cannot be separated.
- **Implication:** Promotion success should be judged on cohort behaviour after the event, not only on sales in promotion week.
- **Action:** Add a post-promotion nurture sequence for users acquired in promotions, and track promotion cohorts against non-promotion cohorts.

### 10. Repeat buyers carry half the orders

- **Finding:** 28.4% of buyers (1,324) ordered more than once and placed 51.7% of all orders. The median gap between orders is 10.1 days.
- **Evidence:** Q24.
- **Action:** Target the second purchase within about two weeks of the first.

### 11. Tracking and catalogue data need fixing

- **Finding:**
  - The event stream misses 3% of orders.
  - 12 products have implausible list prices; for example, a wireless mouse is listed at 241,000. These prices inflate Computing revenue to 33.8% of the total on 391 units.
- **Evidence:** DQ08, DQ18, Q07b, Q16.
- **Action:**
  - Fix purchase-event tracking, and add a daily reconciliation of events against orders (validation V11/V26 can be reused).
  - Audit catalogue prices.

## Recommendations by time horizon

| Horizon | Recommendation | Insight | Owner | Success measure |
|---|---|---|---|---|
| Immediate (0–4 weeks) | Fix purchase-event tracking; schedule the events-vs-orders reconciliation | 11 | Engineering / Data | 0 orders missing from events |
| Immediate | Audit the 12 implausible catalogue prices | 11 | Merchandising | DQ18 = 0 |
| Immediate | Audit mobile-web checkout and fix obvious friction | 3 | Product / Engineering | Web-mobile checkout abandonment |
| Immediate | Review the 19 high-traffic, low-conversion product pages | 5 | Merchandising | Product view-to-purchase rate |
| Medium (1–3 months) | A/B test the mobile-web checkout redesign | 3 | Product | Checkout → order rate on web mobile |
| Medium | A/B test persistent cart, save-for-later and cart-reminder email | 2 | Product / CRM | 7-day cart conversion |
| Medium | First-week re-engagement programme for new users | 7 | CRM | Week-1 and week-4 retention of new cohorts |
| Medium | Re-evaluate paid social on downstream conversion and retention | 4 | Growth | Orders and 28-day return per paid-social user |
| Medium | Shift placement toward hidden-gem products; replenishment reminders for consumables | 5, 6 | Merchandising / CRM | Units per view; repeat-buyer rate |
| Long term (3–12 months) | Randomised tests of registration and loyalty prompts | 8 | Product / Data | Incremental retention vs control |
| Long term | Cohort-value dashboard built on the SQL views (vw_cohort_retention, vw_weekly_kpis) | 7, 9 | Data | Adopted by the PM team |
| Long term | Cross-device identity and event data contracts | 2, 11 | Engineering / Data | Share of journeys stitched across devices |
| Long term | Add marketing cost data to measure channel return on spend | 4 | Growth / Finance | Cost per retained buyer by channel |
