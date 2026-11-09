# KPI and metric definitions

| KPI / metric | Definition | Used for |
|---|---|---|
| Units sold | Sum of `units_sold` | Demand volume |
| Naira sales | Sum of `sales_value_ngn` (after promotional discounts) | Revenue |
| Average selling price | Naira sales / units sold | Price trend (inflation) |
| Units per trading day | Units / number of distinct trading days for the store | Fair store comparison (S08 opened Sep 2024; S03 closed 3 weeks) |
| Sales per sqm per day | Naira sales / trading days / sales area (sqm) | Space productivity by store and format |
| Like-for-like growth | Change for stores open throughout 2023-2025 (S01-S07) | Underlying growth without store openings |
| Day-of-week index | Store-day units / the store's centred 28-day mean, averaged by weekday (non-festive, non-holiday days) | Weekly pattern |
| Payday effect | Mean index in the payday window (last 6 + first 3 days of the month) / mean index mid-month (days 10-20) - 1 | Within-month pattern |
| Monthly seasonal index | Family units per trading day in the month / the family's annual mean (like-for-like stores, averaged over years) | Seasonal profile |
| Seasonal strength (STL) | 1 - Var(remainder) / Var(seasonal + remainder) on weekly units | Seasonality vs noise |
| Peak-to-trough | Max - min of the monthly seasonal index | Seasonal classification (<0.20 weak, 0.20-0.35 moderate, >=0.35 strong) |
| Baseline CV (volatility) | Standard deviation of units / (centred 28-day mean x weekday factor) on ordinary days | Stable (<0.25), moderate (0.25-0.40), volatile (>0.40) |
| Promotion uplift (model) | exp(b) - 1 for `on_promotion` in the per-family log-linear model | Average promotion effect, controlled for calendar drivers |
| Post-promotion effect | exp(b) - 1 for the 14-day post-promotion window | Pull-forward / stock-up |
| Event uplift | Actual units during a promotion at a store / the model's no-promotion baseline for the same days | Promotion-store performance |
| Before/after ratio | Units per day during the promotion / per day in the 28 non-promotion days before | Raw comparison (seasonally confounded) |
| Achieved price change | Average price during the promotion / average price in the 28 days before - 1 | Execution check |
| WAPE | Sum of absolute error / sum of actual units | Forecast accuracy (share of volume mis-forecast) |
| Bias | Sum of (forecast - actual) / sum of actual | Systematic over- or under-forecasting |
| Weekly WAPE | WAPE on series x week totals | Accuracy for weekly ordering |
| Protection period P | Supplier lead time + review period (days) | Replenishment horizon |
| sigma_P | Standard deviation of the cumulative forecast error over P days (from the back-test) | Safety stock input |
| Safety stock | z(97%) = 1.88 x sigma_P | Buffer for forecast error |
| Safety stock days | Safety stock / average daily forecast | Comparison with the current 2-day rule |
| Order-up-to level | Forecast demand over P + safety stock, rounded up to full cases | Order quantity = order-up-to level - inventory position |
| Stock-out rate | Share of trading days with `stockout_flag` = 1 | Availability |
