# Quality-assurance checklist

Every item marked ✅ was tested, and the evidence column says how. Nothing is marked as tested on the basis of inspection alone unless the evidence says so.

## Data validation

| Check | Status | Evidence |
|---|---|---|
| Source record counts | ✅ | `load_audit`: source rows = loaded rows for all 10 tables (Q00_load_audit) |
| Cleaned record counts | ✅ | V02, V04, V05: derived tables match source counts. No rows were deleted |
| Removed records and reasons | ✅ | None removed. Metric-level exclusions are listed in the cleaning log |
| Duplicate handling | ✅ | DQ05: 0 duplicate events. V06, V07: 0 duplicate keys in derived tables. PK/UNIQUE constraints enforced at load |
| Missing-value treatment | ✅ | DQ01–DQ04 and Q00_column_completeness. Each NULL type has a documented treatment |
| Data-type consistency | ✅ | Typed DDL with CHECK constraints. Events staged and profiled: DQ19 = 0 values needing conversion |
| Reconciliation of important totals | ✅ | V09–V20: events, sessions, orders, units and net revenue reconcile across the raw, derived, product, category and view layers |
| Calculated metrics | ✅ | V21–V25: funnel never increases between stages; week-0 retention is 100%; rates within [0, 1]; same-session purchase implies a 7-day purchase |
| Relationship integrity | ✅ | DQ06 / V08: `PRAGMA foreign_key_check` returns 0 violations. FKs declared on every relationship |
| Correctness of derived variables | ✅ | V27: censored return flags match follow-up. V18: the final funnel stage equals the distinct buyers in orders. V26: event buyers do not exceed order buyers |
| Raw data preserved | ✅ | Attached `mode=ro`. MD5 `451c337ac01d6286b2a1575b246ed178` before and after every run |

## Analysis validation

| Check | Status | Evidence |
|---|---|---|
| Methods address the stated objectives | ✅ | Objective-to-query mapping in `project_brief.md`; objective completion table in the report (Section 7.7) |
| Calculations correct | ✅ | 27/27 validation checks pass. Funnel, revenue and units reconcile independently |
| Statistical methods appropriate | ✅ | Wilson bound for ranking proportions; Spearman (rank-based, robust to the skewed view counts); medians for skewed distributions; minimum sample sizes; censoring handled. No significance tests are claimed |
| Findings match the actual outputs | ✅ | Findings are written from the result CSVs. The report is generated programmatically from those CSVs. A script checked every percentage in the README, KPI definitions and insights against the result files: 0 unmatched |
| Conclusions supported | ✅ | Associations are labelled as such. Confounding (Black Friday vs December) and reverse causation (registration, loyalty) are stated |
| Recommendations follow from evidence | ✅ | Each recommendation cites its query or finding |

## Deliverable validation

| Check | Status | Evidence |
|---|---|---|
| SQL executable in the stated dialect | ✅ | `sqlite3 -bail` (shell 3.45.1) on a fresh database: exit code 0, no errors, about 33 s |
| SQL logically complete | ✅ | Sections 1–7 run in order from an empty database. Re-runnable (drops are schema-qualified) |
| Two execution paths agree | ✅ | Shell build and runner build (SQLite 3.53): all 30 tables and views have identical contents (MD5 of every object) |
| Validation can detect errors | ✅ | Seeded-error test on a copy (one ordered session deleted, one product's units changed): V04, V09, V11, V13, V19 and V20 failed as expected |
| Exported files contain the expected data | ✅ | Row counts in `_run_log.csv` match the derived-table sizes (for example, events_enriched 590,648 and user_summary 30,000) |
| Charts are genuine outputs | ✅ | All 9 charts are drawn from result CSVs by `make_charts.py`. Each was rendered and inspected. Chart 9 is real sqlite3 shell output |
| Report opens | ✅ | DOCX converted to PDF with LibreOffice. Pages rendered to images and reviewed |
| Filenames meaningful | ✅ | Query outputs named `Qnn_<question>.csv`; charts numbered and named by content |
| Documentation consistent | ✅ | README, docs and report figures come from the same CSVs (cross-checked by script, see above). Counts quoted in docs (34 analytical queries, 8 views, 19 DQ checks, 27 validation checks) were counted from the SQL file |

## Not tested / outstanding

- The SQL uses SQLite-specific features (`julianday`, `strftime`, `ATTACH … mode=ro`, `pragma_foreign_key_check`). It has not been run on another engine, and porting would need these replaced.
- The SQL has not been run on SQLite versions older than 3.45. Window functions need 3.25, FILTER needs 3.30, math functions need 3.35 (with the math extension compiled in, which is the default in the official shell).
- The implausible catalogue prices (DQ18) remain uncorrected because there is no reference price list.
- The causal claims that would follow from the recommendations (for example, that a checkout redesign raises conversion) are untested. They require experiments.
