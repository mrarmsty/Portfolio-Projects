# Data-quality assessment and cleaning log

All of the checks below are SQL in Section 3 of `sql/ecommerce_product_analytics.sql`. Each one writes a row to the `dq_register` table, and the full register is exported to `outputs/results/Q00_dq_register.csv`. Cleaning and transformation happen in Section 4.

**Guiding rule:** no row is deleted. Problem rows are kept and flagged, and every metric states which flagged rows it excludes. The raw file is attached read-only, and its MD5 is identical before and after every run.

## 1. Loading checks

| Check | Result |
|---|---|
| Source rows vs loaded rows, all 10 tables (`load_audit`) | 10/10 PASS; no rows lost |
| Load through PRIMARY KEY, FOREIGN KEY, UNIQUE, NOT NULL and CHECK constraints | Loaded without a single rejection. The constraints include, for example, `order_total = items_subtotal + shipping_fee`, `line_total = quantity × unit_sale_price`, `unit_sale_price ≤ unit_list_price`, a valid set of event types, and `order_id` only on purchase events |
| Events staged in a TEMP table and type-converted (CAST, strftime, TRIM, NULLIF) | 0 values needed conversion (DQ19) |
| `PRAGMA foreign_key_check` | 0 violations |

## 2. Data-quality register

| ID | Dimension | Check | Affected | % | Action |
|---|---|---|---:|---:|---|
| DQ01 | completeness | product_view events with no product_id | 1,414 | 0.45 | Kept and flagged (`product_traceable = 0`). Counted in engagement totals, excluded from product-level metrics |
| DQ02 | completeness | add_to_cart events with no product_id | 127 | 0.44 | Kept and flagged. Counted in the user and session funnels, excluded from product abandonment |
| DQ03 | completeness | traceable product views with no displayed price | 901 | 0.29 | Kept. Price is not used for view metrics |
| DQ04 | completeness | users with no signup_date (guests) | 19,414 | 64.71 | Expected. Recoded as `is_registered = 0` and analysed as a segment |
| DQ05 | uniqueness | duplicate events (same session, time, type, product) | 0 | 0.00 | None found |
| DQ06 | integrity | foreign-key violations | 0 | 0.00 | None found |
| DQ07 | consistency | events whose user differs from the session's user, or that fall outside the session window | 0 | 0.00 | None found |
| DQ08 | consistency | orders with no purchase event (tracking loss) | 206 | 2.99 | **Orders table used as the system of record for purchases** |
| DQ09 | consistency | order lines with no matching purchase event | 311 | 2.88 | Product purchases measured from order_items |
| DQ10 | consistency | order subtotal or discount ≠ sum of its lines | 0 | 0.00 | None found |
| DQ11 | consistency | orders in a session with no add_to_cart (cart filled in an earlier session) | 1,934 | 28.05 | Not an error: these are cross-session journeys. **The user-level funnel is primary**, and the session funnel is shown alongside it |
| DQ12 | validity | product events after the product's discontinued date | 10 | 0.00 | Kept; negligible |
| DQ13 | validity | discounted price shown with no promotion active | 2 | 0.00 | Kept; negligible |
| DQ14 | validity | single-event sessions (end = start) | 392 | 0.44 | Kept; duration recorded as 0 seconds |
| DQ15 | timeliness | registered users who signed up after their first observed session | 1,959 | 18.51 | Expected (guests who registered later). Registration is treated as status at extract date |
| DQ16 | timeliness | sessions running past the last calendar date | 1 | 0.00 | Kept; sessions are dated by their start |
| DQ17 | validity | bot-like user agents | 0 | 0.00 | None found. Heavy users (up to 81 sessions) kept as genuine |
| DQ18 | validity | products priced ≥ 4× or ≤ 0.25× their category median | 12 | 4.80 | Kept (no reference prices to correct against). **Revenue rankings treated as indicative**; product analysis relies on counts and conversion |
| DQ19 | validity | staged event values needing type or format conversion | 0 | 0.00 | None found. The typed load keeps its conversions so that format drift in a future extract fails loudly |

**Outliers** (Q00_outlier_profile): events per session have a median of 5, a p99 of 29 and a maximum of 82. Sessions per user have a median of 1, a p99 of 19 and a maximum of 81. These are long tails, not errors, so they are kept. Medians are reported alongside means wherever the tail matters.

## 3. Cleaning and transformation log (Section 4)

| Step | Object | What was done | Why |
|---|---|---|---|
| 1 | events (staging) | Staged in `temp.stg_events`, profiled, then loaded with CAST / strftime / LOWER(TRIM) / NULLIF(TRIM, '') | Typed, constrained load; blank strings become NULL |
| 2 | events_enriched | Joined the calendar (week, weekend, promotion), product and category. Added `is_product_event`, `product_traceable`, `shown_discounted` and `session_event_seq` (ROW_NUMBER) | One analysis-ready event table; keeps the DQ01 flag explicit |
| 3 | session_summary | Aggregated events per session with conditional SUMs. Joined the session's order. Added funnel stage (CASE), session order per user and gap since the previous session (ROW_NUMBER, LAG). Computed duration with julianday | Session-level funnel and engagement |
| 4 | user_summary | Recoded registration (NULL signup → guest). Flagged known existing customers. Added cohort week, follow-up days, funnel flags and return flags, with NULL where the outcome is censored. Added an engagement segment (CASE) | User-level funnel and retention without censoring bias |
| 5 | user_week_activity, cohort_retention | One row per user-week. A recursive CTE generates offsets 0–25, keeping only observed weeks (`cohort_week + offset ≤ 26`) | Unbiased retention matrix |
| 6 | cart_add_outcomes | For each traceable add_to_cart: bought in the same session, bought within 7 days, or removed. Additions in the last 7 days are flagged `is_censored` | Abandonment that does not penalise late additions |
| 7 | product_performance, category_performance | Funnel and purchase metrics per product and per category. Viewer-buyers come from EXISTS on indexed tables. Also computed: Wilson lower bound, RANK / DENSE_RANK, and window shares | Product and category questions |
| 8 | Views (Section 6) | 8 reusable views | Stable definitions for BI tools |

## 4. Definitions that resolve data issues

- **Purchase** = a row in `orders`, because the event stream misses 3% of orders.
- **Net order** = status not `cancelled` and not `returned`. **Net revenue** = `items_subtotal` of net orders.
- **Product interaction** = a product_view, add_to_cart, remove_from_cart or purchase event.
- **Returning user** = a session on a later calendar day than the first observed day.
- **Censoring:**
  - return-within-N-days is NULL when a user has fewer than N days of follow-up;
  - cohort cells exist only for observed weeks;
  - cart additions in the last 7 days have no abandonment outcome.
