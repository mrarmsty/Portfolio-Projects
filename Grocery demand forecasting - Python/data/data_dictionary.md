# Data dictionary

The data is **synthetic**. Basketline Supermarkets is a fictional company.

## Source file - `data/raw/basketline_grocery_demand_data.xlsx`

| Sheet | Rows | Grain / content | How it is used in this project |
|---|---|---|---|
| `raw_sales_daily` | 104,833 | POS sales feed as received: one row per load of a date x store x family | **Primary source.** Cleaned in the notebook |
| `sales_daily` | 104,118 | Provider's cleaned version of the feed | Used only to reconcile my own cleaning (100% match) |
| `stores` | 8 | Store id, name, city, state, region, format, sales area (sqm), opening date, families ranged | Store comparisons, normalisation, model features |
| `product_families` | 13 | Family id, name, category, storage type, shelf life, perishable flag | Category analysis, shelf-life checks |
| `promotions` | 135 | Promotion id, name, family, type, headline discount, start/end, duration, number of stores, status (127 completed, 8 planned for Q1 2026) | Promotion analysis; planned ones are known future inputs |
| `promotion_stores` | 817 | Which stores took part in each promotion | Promotion calendar by store |
| `calendar` | 1,186 | Daily, 1 Jan 2023 - 31 Mar 2026: weekday, ISO week, month, public holidays, Ramadan, payday window, back-to-school, season, chain closure | Seasonality, festival windows, forecasting features |
| `store_events` | 10 | Store opening, refurbishment closure, competitor opening, POS outages | Explaining missing days and level shifts |
| `replenishment_params` | 103 | Per store x family: supplier lead time, review period, case pack, minimum order, shelf life, current safety stock (2 days), target service level (97%) | Safety stock and order-up-to policy |
| `cleaning_log`, `data_dictionary`, `README` | - | Provider documentation | Read for context |

### `raw_sales_daily` columns

| Variable | Type (as received) | Description | Example / range | Data-quality observations |
|---|---|---|---|---|
| `raw_row_id` | integer | Row number in the received file | 1 - 104,833 | Unique |
| `load_timestamp` | text | When the row was loaded | `2023-01-02 02:00:21` | Used to resolve repeated loads (keep the latest) |
| `sale_date` | date or text | Trading day | `2023-01-01` / `01/01/2023` | 6,344 rows are text DD/MM/YYYY |
| `store_code` | text | Store as keyed | `S01`, `s01`, `S-01`, `Basketline Lekki` | 4,231 non-standard values, including 39 rows for an unknown store `S99` (test till) |
| `product_family` | text | Family as keyed | `Rice & Grains`, `Rice/Grains` | 5,203 non-standard labels, including legacy names such as `Frozen Foods` |
| `units_sold` | number | Units sold | -1,406 to 19,440 | 261 missing; 22 negative (sign errors) |
| `sales_value` | number (NGN) | Sales value | | 628 missing; S06 March 2024 recorded in kobo (x100) |
| `promo_flag` | text | Promotion indicator | Y, N, Yes, 1, TRUE, blank ... | 7,520 non-standard values |
| `promo_code` | text | Promotion id | `PR24-011` | 491 blank on promotion rows |
| `stockout` | text | Stock-out indicator | `Y` or blank | 1.6% of rows flagged |

## Processed file - `data/processed/basketline_sales_daily_clean.csv`

There is one row per trading day x store x product family: 104,118 rows covering 1 Jan 2023 to 31 Dec 2025. The key is (`sale_date`, `store_id`, `family_id`).

| Variable | Type | Description | Example / range | Notes |
|---|---|---|---|---|
| `sale_date` | date | Trading day | 2023-01-01 to 2025-12-31 | No rows on 25 Dec, before a store opened, during the S03 refurbishment or on POS-outage days (see `store_events`) |
| `store_id` | text | Store | S01 - S08 | FK to `stores` |
| `family_id` | text | Product family | F01 - F13 | FK to `product_families`; S07 does not stock F10 |
| `family_name` | text | Family name | `Noodles & Pasta` | |
| `category` | text | Category | Fresh Food, Pantry Staples, Beverages, Snacks & Confectionery, Household & Personal Care | |
| `units_sold` | integer | Units sold (actual) | 3 - 19,440 (the largest values are bulk orders) | Includes bulk orders; understated on stock-out days |
| `sales_value_ngn` | integer | Sales value in naira after discounts | | |
| `avg_unit_price_ngn` | decimal | `sales_value_ngn / units_sold` | | Blank only if units = 0 |
| `on_promotion` | 0/1 | Family on promotion at this store that day | | Matches the promotion calendar on every row |
| `promotion_id` | text | Active promotion | `PR25-002` | Blank when not on promotion (92% of rows) |
| `promo_type` | text | Mechanic | price_discount, multibuy, display_feature, none | Derived from `promotions` |
| `discount_pct` | decimal | Headline discount (fraction) | 0 - 0.33 | 0 when not on promotion or display-only |
| `stockout_flag` | 0/1 | Shelf gap during the day | | 1.6% of rows |
| `bulk_flag` | 0/1 | Bulk / B2B order day (derived) | | More than 4x the series' centred 29-day median outside festive windows and promotions, or more than 8x on any day; 52 rows |
| `units_adj` | integer | Units for modelling | | Equals `units_sold`, except on bulk days, where it is the local median |
| `data_quality_note` | text | Cleaning action on this row | units_imputed, value_imputed, value_rescaled_from_kobo, units_sign_corrected | Blank = no correction (98.8%) |

## Other processed files
- `data/processed/cleaning_log.csv`: issue, variable, action, reason and rows affected for every cleaning step.
- `data/processed/family_label_mapping.csv`: every raw family label, the master family it maps to, the matching method and the row count.
