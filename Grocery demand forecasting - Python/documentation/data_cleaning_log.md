# Data cleaning and transformation log

**Source:** `raw_sales_daily` (104,833 rows). The raw file is never modified.
**Output:** `data/processed/basketline_sales_daily_clean.csv` (104,118 rows).
**Implementation:** notebook sections 3-5.

## Cleaning

| # | Issue | Variable / table | Action taken | Reason | Effect on data |
|---|---|---|---|---|---|
| 1 | Dates stored as text DD/MM/YYYY | `sale_date` | Parsed day-first into true dates | Mixed types break grouping and time indexing | 6,344 rows converted |
| 2 | Store code variants (case, hyphen, spaces, store names) | `store_code` | Trimmed, upper-cased, hyphens removed, names mapped to ids | The same store was keyed several ways | 4,192 rows standardised |
| 3 | Unknown store `S99` (3 days, 1-5 units per row) | `store_code` | Excluded | A training / test till, not a trading store | 39 rows removed |
| 4 | Family label variants and legacy names | `product_family` | Normalised text, then exact, fuzzy or reviewed alias mapping to the 13 master families; mapping table saved | Spelling and legacy-name variants | 5,203 rows relabelled; 0 unmapped |
| 5 | Exact duplicate rows | all | Removed | Re-uploads double count | 520 rows removed |
| 6 | Same date-store-family loaded twice with different values | `units_sold`, `sales_value` | Kept the latest `load_timestamp` | Later loads correct earlier extracts | 156 superseded rows removed |
| 7 | Negative units with positive value | `units_sold` | Absolute value | Sign error (value is positive in all 22 cases) | 22 rows corrected |
| 8 | Unit values about 100x the family's chain median | `sales_value` | Divided by 100 for the whole store-month S06 March 2024 | Recorded in kobo; 99% of that month's rows affected | 401 rows rescaled |
| 9 | Missing units (value present) | `units_sold` | Imputed as value / local unit price (centred 15-day median) | Avoids false zero-demand gaps | 260 rows imputed, flagged |
| 10 | Missing value (units present) | `sales_value` | Imputed as units x local unit price | Keeps revenue complete | 624 rows imputed, flagged |
| 11 | Promotion flag in nine formats | `promo_flag` | Mapped to 0/1 (blank = 0) | One consistent indicator | 7,520 rows standardised |
| 12 | Promotion rows missing the code | `promo_code` | Filled from the promotion calendar (store, family, date) | Needed to link sales to promotion attributes | 489 rows filled; flag vs calendar mismatches: 0 |

**Reconciliation:** the result matches the provider's `sales_daily` on 100% of keys, units, values, promotion flags and stock-out flags.

## Transformation

| # | Transformation | Detail | Purpose |
|---|---|---|---|
| T1 | Complete daily panel | 103 series x 1,096 days with a `day_status` for each missing day. Missing days: store not yet open 8,112, chain closed 296, refurbishment 273, POS outage 89. Unexplained gaps: 0 | Time-series integrity; missing is not zero |
| T2 | Calendar and festival features | Weekday, payday window, holidays, Ramadan, back-to-school; days to Christmas, Easter and Eid; December, January, Easter and Eid windows | Seasonality analysis and forecasting |
| T3 | Promotion features | Type, headline discount, promotion day number, days since the last promotion ended, 14-day post-promotion window | Promotion modelling and forecasting |
| T4 | Bulk-order flag | Two tiers: more than 4x the centred 29-day median outside festive windows and promotions, or more than 8x on any day. 52 days, 0.9% of units: all 45 provider-flagged days plus 7 extreme days (6 inside festive windows) that the provider's rule missed | Separates B2B orders from shelf demand |
| T5 | `units_adj` | Bulk days replaced by the local median | Modelling target |
| T6 | Forecast panel | Adds 1 Jan - 31 Mar 2026 with calendar and planned promotions; leak-free lag features (28-day and 91-day minimum lags, last-year values) | Back-test and Q1 2026 forecast |
| T7 | Exclusions for modelling (not deleted) | Stock-out days (censored) and bulk days are left out of model training and accuracy scoring | Unbiased estimates of demand |
