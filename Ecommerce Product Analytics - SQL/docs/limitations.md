# Limitations

## Observed data limitations (seen in the data itself)

- **Synthetic data.** The data simulates a Nigerian marketplace ("OjaLoop", fictional brands). The patterns are internally consistent, but they are not evidence about any real business.
- **Tracking loss.** 206 orders (3.0%) and 311 order lines have no purchase event (DQ08, DQ09). Purchases are measured from the orders table. Any event-only metric would understate purchases.
- **Untraceable product events.** 1,414 product views and 127 cart additions carry no product_id (DQ01, DQ02). They are counted in engagement and funnel totals but not in product metrics.
- **Implausible prices.** 12 products are priced ≥ 4× or ≤ 0.25× their category median (DQ18). Revenue by product and category, and the dominance of Computing revenue in particular, should be treated as indicative only.
- **Status attributes measured at extract date.** `signup_date`, `is_loyalty_member` and `acquisition_channel` describe the user at the end of the period, not at the time of each session. 1,959 registered users signed up after their first session (DQ15).
- **Currency not stated.** NGN is assumed. All monetary values are in whole currency units.
- **No cost, margin, inventory or marketing-spend data.** Profitability and channel return on spend cannot be assessed.

## Methodological limitations (arising from the choices made)

- **Associations, not causes.** There are no experiments in the data. Segment differences (channel, device, registration, loyalty, promotion) describe association only. Registration and loyalty differences may run in reverse (engaged users register).
- **Left-censoring.** The data starts on 7 Jul 2025, so users active before then appear "new" in weeks 1–2. Cohort 1 (and to a lesser extent cohort 2) mixes existing and new customers, which inflates its retention. Q21 therefore also reports cohorts 3–26 and users not registered before the window.
- **Right-censoring.** Later cohorts and users have less follow-up. Return-within-N-days excludes users with fewer than N days of follow-up. Cohort cells exist only for observed weeks. Cart additions in the final 7 days have no abandonment outcome.
- **Abandonment window.** A cart addition counts as abandoned if the same product is not ordered within 7 days. 9.3% of orders come more than 7 days after the last add-to-cart (Q10), so some eventual purchases are counted as abandoned.
- **Funnel definition.** The closed user funnel requires each earlier stage. The session funnel misses the 28% of orders that finish a journey started in an earlier session; it is shown as a complement, not as the main funnel.
- **Product attribution.** "Viewer-buyers" are viewers of a product who ordered that same product at any time in the window. This does not prove that the view led to the order.
- **Confounding in time.** Black Friday cohorts reach week 4 during the late-December slowdown, so acquisition quality and seasonality cannot be separated.
- **Small samples.** Conversion rankings use a Wilson lower bound and a minimum of 500 viewers. Abandonment rankings require 100 observed additions. Products below these thresholds are not ranked.
- **Opportunity sizing.** Figures such as "about 490 more orders" or "about 656 product purchases" apply a benchmark rate to a segment. They show the scale of a gap, not a forecast of what a change would deliver.

## Contextual limitations (what the data cannot tell us)

- **Six months of data.** The window covers 26 weeks, including one Black Friday and one festive season. Seasonality across years cannot be estimated.
- **No page-level detail.** There are no page names, search terms, error logs, page-speed data or checkout-step events. The analysis can say *where* users drop off, not *why*.
- **No information on users outside the platform.** There are no competitor prices, marketing calendar details beyond promotion dates, or customer-service contacts.
- **Identity is per user ID.** If one person uses several IDs or devices without logging in, cross-device journeys are split.

## Assumptions

1. Orders are the authoritative record of purchases.
2. A net order is one not cancelled or returned. Revenue is `items_subtotal`, excluding shipping.
3. A returning user is a user active on a later calendar day.
4. Weeks run Monday to Sunday, as defined by the calendar table.
5. Prices are in NGN.
6. Users with no signup date are guests. Users who signed up before the window are known existing customers.
7. The analysis covers all sessions: no bot traffic was detected, and heavy users are genuine.
