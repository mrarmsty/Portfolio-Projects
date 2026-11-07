/* =====================================================================================================
   E-COMMERCE PRODUCT ANALYTICS — USER ENGAGEMENT, CONVERSION FUNNEL, PRODUCT PERFORMANCE AND RETENTION
   -----------------------------------------------------------------------------------------------------
   Business question : how do users interact with the platform, where do they abandon their shopping
                       journeys, and which products and behaviours are associated with purchases?
   Dialect           : SQLite 3.35+ (window functions, CTEs, FILTER, math functions). Tested end to end with the
                       sqlite3 shell 3.45.1 and with SQLite 3.53 through Python's sqlite3 module.
   Run               : from the repository root
                           sqlite3 data/processed/ecommerce_analytics.db < sql/ecommerce_product_analytics.sql
                       or  python scripts/run_sql_project.py --fresh   (same SQL; also exports every result)
                       The raw database data/raw/ecommerce_clean.sqlite is attached READ-ONLY and never modified.
   Markers           : "-- @exec", "-- @query" and "-- @export" lines are ordinary SQL comments that label each
                       block for the runner, which writes @query results to outputs/results/<name>.csv and
                       @export tables to data/processed/<name>.csv (.csv.gz for the event-level table).
   Data              : 26 weeks of synthetic platform data (Mon 7 Jul 2025 - Sun 4 Jan 2026), 30,000 users,
                       89,557 sessions, 590,648 events, 6,896 orders. Prices are whole currency units; the
                       currency is not stated in the data (assumed Nigerian naira, NGN).

   CONTENTS
     Section 1  Database and schema setup ............ connection settings, read-only attach, drop/re-create
     Section 2  Table creation and data loading ...... DDL with PK / FK / CHECK, staging, indexes, load audit
     Section 3  Data-quality assessment ............... dq_register (DQ01-DQ19), completeness, outliers
     Section 4  Cleaning and transformation ........... events_enriched, session_summary, user_summary,
                                                        user_week_activity, cohort_retention, cart_add_outcomes,
                                                        product_performance, category_performance
     Section 5  Analytical queries Q01-Q25 ............ 5A engagement, 5B funnel, 5C abandonment, 5D products and
                                                        categories, 5E retention, 5F opportunities
     Section 6  Views and reusable outputs ............ 8 views, Q26-Q28, cleaned-table exports
     Section 7  Validation and reconciliation ......... validation_results (V01-V27)
   ===================================================================================================== */


/* =====================================================================================================
   SECTION 1. DATABASE AND SCHEMA SETUP
   ===================================================================================================== */

-- @exec 1.1 connection settings and read-only attachment of the raw database
PRAGMA foreign_keys = ON;
PRAGMA journal_mode = WAL;
PRAGMA synchronous = NORMAL;
PRAGMA temp_store = MEMORY;
ATTACH DATABASE 'file:data/raw/ecommerce_clean.sqlite?mode=ro' AS raw;

-- @exec 1.2 drop analysis objects so the script can be re-run from scratch
-- Names are schema-qualified with main. on purpose: an unqualified DROP would resolve to the attached raw
-- database when the table does not yet exist in main (the read-only attachment is the second safeguard).
DROP VIEW IF EXISTS main.vw_weekly_kpis;
DROP VIEW IF EXISTS main.vw_daily_kpis;
DROP VIEW IF EXISTS main.vw_user_funnel;
DROP VIEW IF EXISTS main.vw_session_funnel_by_segment;
DROP VIEW IF EXISTS main.vw_product_scorecard;
DROP VIEW IF EXISTS main.vw_category_scorecard;
DROP VIEW IF EXISTS main.vw_cohort_retention;
DROP VIEW IF EXISTS main.vw_segment_retention;
DROP TABLE IF EXISTS main.validation_results;
DROP TABLE IF EXISTS main.cohort_retention;
DROP TABLE IF EXISTS main.user_week_activity;
DROP TABLE IF EXISTS main.cart_add_outcomes;
DROP TABLE IF EXISTS main.user_product_purchases;
DROP TABLE IF EXISTS main.category_performance;
DROP TABLE IF EXISTS main.product_performance;
DROP TABLE IF EXISTS main.user_summary;
DROP TABLE IF EXISTS main.session_summary;
DROP TABLE IF EXISTS main.events_enriched;
DROP TABLE IF EXISTS main.dq_register;
DROP TABLE IF EXISTS main.load_audit;
DROP TABLE IF EXISTS main.events;
DROP TABLE IF EXISTS main.order_items;
DROP TABLE IF EXISTS main.orders;
DROP TABLE IF EXISTS main.sessions;
DROP TABLE IF EXISTS main.users;
DROP TABLE IF EXISTS main.calendar;
DROP TABLE IF EXISTS main.promotion_products;
DROP TABLE IF EXISTS main.promotions;
DROP TABLE IF EXISTS main.products;
DROP TABLE IF EXISTS main.categories;
DROP TABLE IF EXISTS temp.stg_events;
DROP TABLE IF EXISTS temp.stg_events_profile;


/* =====================================================================================================
   SECTION 2. TABLE CREATION AND DATA LOADING
   Each source table is recreated with explicit types, primary keys, foreign keys and CHECK constraints,
   then loaded with INSERT ... SELECT from the attached raw database. Loading through constraints is itself
   a validation step: any duplicate key, orphan reference or invalid value would stop the load.
   ===================================================================================================== */

-- @exec 2.1 reference tables
CREATE TABLE categories (
    category_id    INTEGER PRIMARY KEY,
    category_name  TEXT    NOT NULL UNIQUE,
    department     TEXT    NOT NULL
);

CREATE TABLE products (
    product_id         TEXT    PRIMARY KEY,
    product_name       TEXT    NOT NULL,
    category_id        INTEGER NOT NULL REFERENCES categories (category_id),
    brand              TEXT    NOT NULL,
    list_price         INTEGER NOT NULL CHECK (list_price > 0),
    launch_date        TEXT    NOT NULL CHECK (launch_date = date(launch_date)),
    avg_rating         REAL    CHECK (avg_rating BETWEEN 1 AND 5),
    review_count       INTEGER NOT NULL CHECK (review_count >= 0),
    is_active          INTEGER NOT NULL CHECK (is_active IN (0, 1)),
    discontinued_date  TEXT,
    last_updated       TEXT    NOT NULL,
    CHECK ((is_active = 1 AND discontinued_date IS NULL) OR (is_active = 0 AND discontinued_date IS NOT NULL))
);

CREATE TABLE promotions (
    promotion_id    INTEGER PRIMARY KEY,
    promotion_name  TEXT NOT NULL UNIQUE,
    promotion_type  TEXT NOT NULL CHECK (promotion_type IN ('seasonal', 'holiday', 'mega_sale', 'clearance')),
    start_date      TEXT NOT NULL,
    end_date        TEXT NOT NULL,
    scope           TEXT NOT NULL CHECK (scope IN ('sitewide', 'category')),
    CHECK (end_date >= start_date)
);

CREATE TABLE promotion_products (
    promotion_id  INTEGER NOT NULL REFERENCES promotions (promotion_id),
    product_id    TEXT    NOT NULL REFERENCES products (product_id),
    discount_pct  REAL    NOT NULL CHECK (discount_pct > 0 AND discount_pct < 1),
    PRIMARY KEY (promotion_id, product_id)
);

CREATE TABLE calendar (
    date               TEXT    PRIMARY KEY CHECK (date = date(date)),
    day_of_week        INTEGER NOT NULL CHECK (day_of_week BETWEEN 1 AND 7),
    day_name           TEXT    NOT NULL,
    is_weekend         INTEGER NOT NULL CHECK (is_weekend IN (0, 1)),
    week_start_date    TEXT    NOT NULL,
    week_index         INTEGER NOT NULL CHECK (week_index BETWEEN 1 AND 26),
    iso_year           INTEGER NOT NULL,
    iso_week           INTEGER NOT NULL,
    month_number       INTEGER NOT NULL,
    month_name         TEXT    NOT NULL,
    year_month         TEXT    NOT NULL,
    quarter            TEXT    NOT NULL,
    year               INTEGER NOT NULL,
    is_public_holiday  INTEGER NOT NULL CHECK (is_public_holiday IN (0, 1)),
    promotion_name     TEXT
);

INSERT INTO categories         SELECT * FROM raw.categories;
INSERT INTO products           SELECT * FROM raw.products;
INSERT INTO promotions         SELECT * FROM raw.promotions;
INSERT INTO promotion_products SELECT * FROM raw.promotion_products;
INSERT INTO calendar           SELECT * FROM raw.calendar;

-- @exec 2.2 behavioural and transactional tables
CREATE TABLE users (
    user_id              TEXT    PRIMARY KEY,
    signup_date          TEXT    CHECK (signup_date IS NULL OR signup_date = date(signup_date)),
    acquisition_channel  TEXT    NOT NULL,
    city                 TEXT    NOT NULL,
    primary_device       TEXT    NOT NULL CHECK (primary_device IN ('mobile', 'desktop', 'tablet')),
    is_loyalty_member    INTEGER NOT NULL CHECK (is_loyalty_member IN (0, 1)),
    account_type         TEXT    NOT NULL
);

CREATE TABLE sessions (
    session_id      TEXT PRIMARY KEY,
    user_id         TEXT NOT NULL REFERENCES users (user_id),
    session_start   TEXT NOT NULL,
    session_end     TEXT NOT NULL,
    device_type     TEXT NOT NULL CHECK (device_type IN ('mobile', 'desktop', 'tablet')),
    platform        TEXT NOT NULL CHECK (platform IN ('web', 'android_app', 'ios_app')),
    traffic_source  TEXT NOT NULL,
    user_agent      TEXT NOT NULL,
    CHECK (session_end >= session_start)
);

CREATE TABLE orders (
    order_id         TEXT    PRIMARY KEY,
    user_id          TEXT    NOT NULL REFERENCES users (user_id),
    session_id       TEXT    NOT NULL REFERENCES sessions (session_id),
    order_timestamp  TEXT    NOT NULL,
    order_status     TEXT    NOT NULL CHECK (order_status IN ('delivered', 'shipped', 'processing', 'cancelled', 'returned')),
    payment_method   TEXT    NOT NULL,
    shipping_city    TEXT    NOT NULL,
    items_subtotal   INTEGER NOT NULL CHECK (items_subtotal > 0),
    discount_total   INTEGER NOT NULL CHECK (discount_total >= 0),
    shipping_fee     INTEGER NOT NULL CHECK (shipping_fee >= 0),
    order_total      INTEGER NOT NULL,
    CHECK (order_total = items_subtotal + shipping_fee)
);

CREATE TABLE order_items (
    order_item_id    INTEGER PRIMARY KEY,
    order_id         TEXT    NOT NULL REFERENCES orders (order_id),
    product_id       TEXT    NOT NULL REFERENCES products (product_id),
    quantity         INTEGER NOT NULL CHECK (quantity > 0),
    unit_list_price  INTEGER NOT NULL CHECK (unit_list_price > 0),
    unit_sale_price  INTEGER NOT NULL CHECK (unit_sale_price > 0 AND unit_sale_price <= unit_list_price),
    line_discount    INTEGER NOT NULL CHECK (line_discount >= 0),
    line_total       INTEGER NOT NULL,
    CHECK (line_total = quantity * unit_sale_price),
    CHECK (line_discount = quantity * (unit_list_price - unit_sale_price)),
    UNIQUE (order_id, product_id)
);

CREATE TABLE events (
    event_id         INTEGER PRIMARY KEY,
    session_id       TEXT    NOT NULL REFERENCES sessions (session_id),
    user_id          TEXT    NOT NULL REFERENCES users (user_id),
    event_timestamp  TEXT    NOT NULL,
    event_type       TEXT    NOT NULL CHECK (event_type IN
                      ('page_view', 'search', 'product_view', 'add_to_cart', 'remove_from_cart', 'begin_checkout', 'purchase')),
    product_id       TEXT    REFERENCES products (product_id),
    quantity         INTEGER CHECK (quantity IS NULL OR quantity > 0),
    unit_price       INTEGER CHECK (unit_price IS NULL OR unit_price > 0),
    order_id         TEXT    REFERENCES orders (order_id),
    CHECK (event_type = 'purchase' OR order_id IS NULL)
);

INSERT INTO users       SELECT * FROM raw.users;
INSERT INTO sessions    SELECT * FROM raw.sessions;
INSERT INTO orders      SELECT * FROM raw.orders;
INSERT INTO order_items SELECT * FROM raw.order_items;

-- Events (590k rows, the table every metric depends on) go through a staging step.
-- stg_events is a TEMP table: it lives only for this connection and is never written to the analysis file.
-- It holds the source rows exactly as supplied. Their format is profiled there (the profile feeds DQ19 in
-- Section 3), and the typed load then applies explicit conversions: CAST for numbers, strftime for timestamps,
-- LOWER/TRIM for the event type and NULLIF(TRIM(...), '') so that blank strings become NULL. A value that cannot be
-- converted becomes NULL and is rejected by the NOT NULL / CHECK constraints instead of being coerced silently.
CREATE TEMP TABLE stg_events AS SELECT * FROM raw.events;

CREATE TEMP TABLE stg_events_profile AS
SELECT COUNT(*)                                                                         AS staged_rows,
       SUM(typeof(event_id) <> 'integer')                                               AS non_integer_ids,
       SUM(event_timestamp IS NOT strftime('%Y-%m-%d %H:%M:%S', event_timestamp))       AS non_iso_timestamps,
       SUM(event_type <> LOWER(TRIM(event_type)))                                       AS untidy_event_types,
       SUM(TRIM(product_id) = '' OR TRIM(order_id) = '')                                AS blank_ids,
       SUM(typeof(quantity) NOT IN ('integer', 'null') OR typeof(unit_price) NOT IN ('integer', 'null')) AS non_integer_amounts
FROM stg_events;

INSERT INTO events (event_id, session_id, user_id, event_timestamp, event_type, product_id, quantity, unit_price, order_id)
SELECT CAST(event_id AS INTEGER),
       TRIM(session_id),
       TRIM(user_id),
       strftime('%Y-%m-%d %H:%M:%S', event_timestamp),
       LOWER(TRIM(event_type)),
       NULLIF(TRIM(product_id), ''),
       CAST(quantity AS INTEGER),
       CAST(unit_price AS INTEGER),
       NULLIF(TRIM(order_id), '')
FROM stg_events;

DROP TABLE temp.stg_events;

-- @exec 2.3 indexes for the join and window patterns used below
CREATE INDEX ix_products_category   ON products (category_id);
CREATE INDEX ix_promo_products_prod ON promotion_products (product_id);
CREATE INDEX ix_sessions_user       ON sessions (user_id, session_start);
CREATE INDEX ix_orders_user         ON orders (user_id, order_timestamp);
CREATE INDEX ix_orders_session      ON orders (session_id);
CREATE INDEX ix_order_items_product ON order_items (product_id);
CREATE INDEX ix_events_session      ON events (session_id, event_timestamp, event_id);
CREATE INDEX ix_events_user         ON events (user_id, event_timestamp);
CREATE INDEX ix_events_type_product ON events (event_type, product_id);
CREATE INDEX ix_events_order        ON events (order_id, product_id);

-- @exec 2.4 load audit: source rows vs loaded rows for every table
CREATE TABLE load_audit (
    table_name   TEXT PRIMARY KEY,
    source_rows  INTEGER NOT NULL,
    loaded_rows  INTEGER NOT NULL,
    status       TEXT    NOT NULL
);

INSERT INTO load_audit (table_name, source_rows, loaded_rows, status)
SELECT t, s, l, CASE WHEN s = l THEN 'PASS' ELSE 'FAIL' END
FROM (
    SELECT 'categories' AS t, (SELECT COUNT(*) FROM raw.categories) AS s, (SELECT COUNT(*) FROM main.categories) AS l
    UNION ALL SELECT 'products',           (SELECT COUNT(*) FROM raw.products),           (SELECT COUNT(*) FROM main.products)
    UNION ALL SELECT 'promotions',         (SELECT COUNT(*) FROM raw.promotions),         (SELECT COUNT(*) FROM main.promotions)
    UNION ALL SELECT 'promotion_products', (SELECT COUNT(*) FROM raw.promotion_products), (SELECT COUNT(*) FROM main.promotion_products)
    UNION ALL SELECT 'calendar',           (SELECT COUNT(*) FROM raw.calendar),           (SELECT COUNT(*) FROM main.calendar)
    UNION ALL SELECT 'users',              (SELECT COUNT(*) FROM raw.users),              (SELECT COUNT(*) FROM main.users)
    UNION ALL SELECT 'sessions',           (SELECT COUNT(*) FROM raw.sessions),           (SELECT COUNT(*) FROM main.sessions)
    UNION ALL SELECT 'orders',             (SELECT COUNT(*) FROM raw.orders),             (SELECT COUNT(*) FROM main.orders)
    UNION ALL SELECT 'order_items',        (SELECT COUNT(*) FROM raw.order_items),        (SELECT COUNT(*) FROM main.order_items)
    UNION ALL SELECT 'events',             (SELECT COUNT(*) FROM raw.events),             (SELECT COUNT(*) FROM main.events)
);

-- @query Q00_load_audit
SELECT * FROM load_audit ORDER BY source_rows DESC;

-- @exec 2.5 detach the raw database: everything after this point reads only the analysis copy
DETACH DATABASE raw;


/* =====================================================================================================
   SECTION 3. DATA-QUALITY ASSESSMENT
   Every check writes one row to dq_register: the dimension tested, how many rows are affected, and the
   action taken in Section 4. Nothing is deleted: rows are kept and flagged, and each metric documents
   which flagged rows it excludes.
   ===================================================================================================== */

-- @exec 3.1 data-quality register
CREATE TABLE dq_register (
    check_id        TEXT PRIMARY KEY,
    dimension       TEXT NOT NULL,     -- completeness, uniqueness, validity, consistency, integrity, timeliness
    table_name      TEXT NOT NULL,
    check_desc      TEXT NOT NULL,
    affected_rows   INTEGER NOT NULL,
    total_rows      INTEGER NOT NULL,
    action          TEXT NOT NULL
);

-- Completeness: NULL product context on product-level events (conditional aggregation in one pass)
WITH product_events AS (
    SELECT
        COUNT(*)                                                                 AS n_product_events,
        SUM(CASE WHEN event_type = 'product_view' AND product_id IS NULL THEN 1 ELSE 0 END) AS view_no_product,
        SUM(CASE WHEN event_type = 'product_view' THEN 1 ELSE 0 END)                        AS n_views,
        SUM(CASE WHEN event_type = 'product_view' AND product_id IS NOT NULL AND unit_price IS NULL THEN 1 ELSE 0 END) AS view_no_price,
        SUM(CASE WHEN event_type = 'add_to_cart' AND product_id IS NULL THEN 1 ELSE 0 END)  AS cart_no_product,
        SUM(CASE WHEN event_type = 'add_to_cart' THEN 1 ELSE 0 END)                         AS n_carts
    FROM events
    WHERE event_type IN ('product_view', 'add_to_cart', 'remove_from_cart', 'purchase')
)
INSERT INTO dq_register
SELECT 'DQ01', 'completeness', 'events', 'product_view events with no product_id (untraceable product)', view_no_product, n_views,
       'Kept and flagged (product_traceable = 0). Counted in engagement totals; excluded from product-level metrics.' FROM product_events
UNION ALL
SELECT 'DQ02', 'completeness', 'events', 'add_to_cart events with no product_id', cart_no_product, n_carts,
       'Kept and flagged. Counted in the user and session funnels; excluded from product cart-abandonment metrics.' FROM product_events
UNION ALL
SELECT 'DQ03', 'completeness', 'events', 'traceable product_view events with no displayed price', view_no_price, n_views,
       'Kept. Price is not used for view metrics; promotion status is taken from the promotions tables instead.' FROM product_events;

-- Completeness: guests without a signup date
INSERT INTO dq_register
SELECT 'DQ04', 'completeness', 'users', 'users with no signup_date (guest visitors who never registered)',
       SUM(signup_date IS NULL), COUNT(*),
       'Expected by design. Recoded to is_registered = 0 and analysed as a user segment.' FROM users;

-- Uniqueness: duplicate events (same session, timestamp, type and product)
INSERT INTO dq_register
SELECT 'DQ05', 'uniqueness', 'events', 'duplicate events (same session, timestamp, event type and product)',
       COALESCE(SUM(n - 1), 0), (SELECT COUNT(*) FROM events),
       'None found; no de-duplication needed.'
FROM (SELECT COUNT(*) AS n FROM events GROUP BY session_id, event_timestamp, event_type, IFNULL(product_id, '') HAVING COUNT(*) > 1);

-- Integrity: foreign keys (pragma table-valued function) plus explicit anti-joins
INSERT INTO dq_register
SELECT 'DQ06', 'integrity', 'all tables', 'foreign-key violations reported by PRAGMA foreign_key_check',
       (SELECT COUNT(*) FROM pragma_foreign_key_check), (SELECT COUNT(*) FROM events) + (SELECT COUNT(*) FROM orders) + (SELECT COUNT(*) FROM order_items),
       'None found.';

INSERT INTO dq_register
SELECT 'DQ07', 'consistency', 'events / sessions', 'events whose user differs from the session user, or that fall outside the session window',
       COUNT(*), (SELECT COUNT(*) FROM events), 'None found.'
FROM events e
JOIN sessions s ON s.session_id = e.session_id
WHERE e.user_id <> s.user_id OR e.event_timestamp < s.session_start OR e.event_timestamp > s.session_end;

-- Consistency: tracking gaps between the event stream and the order system
INSERT INTO dq_register
SELECT 'DQ08', 'consistency', 'orders / events', 'orders with no purchase event in the event stream (tracking loss)',
       COUNT(*), (SELECT COUNT(*) FROM orders),
       'Orders table treated as the system of record for purchases; event-tracked purchases reported only for reconciliation.'
FROM orders o
WHERE NOT EXISTS (SELECT 1 FROM events e WHERE e.order_id = o.order_id);

INSERT INTO dq_register
SELECT 'DQ09', 'consistency', 'order_items / events', 'order lines with no matching purchase event',
       COUNT(*), (SELECT COUNT(*) FROM order_items), 'As DQ08: product purchases are measured from order_items.'
FROM order_items oi
WHERE NOT EXISTS (SELECT 1 FROM events e WHERE e.event_type = 'purchase' AND e.order_id = oi.order_id AND e.product_id = oi.product_id);

INSERT INTO dq_register
SELECT 'DQ10', 'consistency', 'orders / order_items', 'orders whose subtotal or discount does not equal the sum of their lines',
       COUNT(*), (SELECT COUNT(*) FROM orders), 'None found.'
FROM orders o
JOIN (SELECT order_id, SUM(line_total) AS lines_total, SUM(line_discount) AS lines_discount FROM order_items GROUP BY order_id) i
  ON i.order_id = o.order_id
WHERE o.items_subtotal <> i.lines_total OR o.discount_total <> i.lines_discount;

-- (anti-join against a pre-aggregated CTE: a correlated NOT EXISTS on event_type made the planner scan the
--  event_type index for every order - 150 s instead of under 1 s)
WITH cart_sessions AS (
    SELECT DISTINCT session_id FROM events WHERE event_type = 'add_to_cart'
)
INSERT INTO dq_register
SELECT 'DQ11', 'consistency', 'orders / events', 'orders placed in a session with no add_to_cart event (cart filled in an earlier session)',
       COUNT(*), (SELECT COUNT(*) FROM orders),
       'Not an error: cross-session purchase journeys. The user-level funnel is the primary funnel; the session funnel is reported alongside.'
FROM orders o
LEFT JOIN cart_sessions c ON c.session_id = o.session_id
WHERE c.session_id IS NULL;

-- Validity: product events after the product was discontinued
INSERT INTO dq_register
SELECT 'DQ12', 'validity', 'events / products', 'product events dated after the product''s discontinued_date',
       COUNT(*), (SELECT COUNT(*) FROM events WHERE product_id IS NOT NULL),
       'Kept (plausibly stale catalogue pages); too few to affect results.'
FROM events e
JOIN products p ON p.product_id = e.product_id
WHERE p.discontinued_date IS NOT NULL AND date(e.event_timestamp) > p.discontinued_date;

-- Validity: displayed price differs from list price with no promotion running for that product
INSERT INTO dq_register
SELECT 'DQ13', 'validity', 'events / promotions', 'product views priced below list price with no promotion active for the product',
       COUNT(*), (SELECT COUNT(*) FROM events WHERE event_type = 'product_view' AND unit_price IS NOT NULL),
       'Kept; negligible.'
FROM events e
JOIN products p ON p.product_id = e.product_id
WHERE e.event_type = 'product_view' AND e.unit_price IS NOT NULL AND e.unit_price <> p.list_price
  AND NOT EXISTS (SELECT 1 FROM promotion_products pp JOIN promotions pr ON pr.promotion_id = pp.promotion_id
                  WHERE pp.product_id = e.product_id AND date(e.event_timestamp) BETWEEN pr.start_date AND pr.end_date);

-- Timeliness / validity: zero-length sessions and the extract window
INSERT INTO dq_register
SELECT 'DQ14', 'validity', 'sessions', 'sessions with session_end = session_start (single-event sessions)',
       SUM(session_end = session_start), COUNT(*), 'Kept; duration recorded as 0 seconds.' FROM sessions;

INSERT INTO dq_register
SELECT 'DQ15', 'timeliness', 'users / sessions', 'registered users whose signup_date is after their first observed session',
       COUNT(*), (SELECT COUNT(*) FROM users WHERE signup_date IS NOT NULL),
       'Expected (guests who registered later). Registration is analysed as status at extract date, not at first visit.'
FROM users u
JOIN (SELECT user_id, MIN(session_start) AS first_session FROM sessions GROUP BY user_id) f ON f.user_id = u.user_id
WHERE u.signup_date > date(f.first_session);

INSERT INTO dq_register
SELECT 'DQ16', 'timeliness', 'sessions', 'sessions ending after the last calendar date (crossing midnight on 4 Jan 2026)',
       COUNT(*), (SELECT COUNT(*) FROM sessions), 'Kept; sessions are dated by session_start.'
FROM sessions WHERE date(session_end) > (SELECT MAX(date) FROM calendar);

-- Outliers: very heavy users (top 0.1% by sessions) checked for bot signatures
INSERT INTO dq_register
SELECT 'DQ17', 'validity', 'sessions', 'sessions with a bot-like user agent (bot, spider, crawl, headless, curl, python)',
       COUNT(*), (SELECT COUNT(*) FROM sessions), 'None found; heavy users (up to 81 sessions) kept as genuine.'
FROM sessions
WHERE lower(user_agent) LIKE '%bot%' OR lower(user_agent) LIKE '%spider%' OR lower(user_agent) LIKE '%crawl%'
   OR lower(user_agent) LIKE '%headless%' OR lower(user_agent) LIKE '%curl%' OR lower(user_agent) LIKE '%python%';

-- Validity: price plausibility. Prices are compared with the category median (window functions); products
-- priced at 4x or more, or a quarter or less, of their category median are flagged for review.
WITH ranked AS (
    SELECT p.product_id, p.category_id, p.list_price,
           ROW_NUMBER() OVER (PARTITION BY p.category_id ORDER BY p.list_price) AS rn,
           COUNT(*)     OVER (PARTITION BY p.category_id)                       AS n
    FROM products p
), medians AS (
    SELECT category_id, MAX(CASE WHEN rn = (n + 1) / 2 THEN list_price END) AS median_price FROM ranked GROUP BY category_id
)
INSERT INTO dq_register
SELECT 'DQ18', 'validity', 'products', 'products priced at >= 4x or <= 0.25x their category median list price',
       COUNT(*), (SELECT COUNT(*) FROM products),
       'Kept (no reference prices to correct against). Several product types carry implausible prices for their kind '
       || '(e.g. wireless mice above some laptops), so revenue rankings are treated as indicative; product analysis relies on counts and conversion.'
FROM ranked r JOIN medians m ON m.category_id = r.category_id
WHERE 1.0 * r.list_price / m.median_price >= 4 OR 1.0 * r.list_price / m.median_price <= 0.25;

-- DQ19: format conformance of the staged events (profile computed in 2.2 before the typed load).
INSERT INTO dq_register
SELECT 'DQ19', 'validity', 'events (staging)',
       'staged event values needing conversion: non-integer ids or amounts, non-ISO timestamps, untidy event types, blank ids',
       non_integer_ids + non_iso_timestamps + untidy_event_types + blank_ids + non_integer_amounts, staged_rows,
       'None found. The typed load still applies CAST / strftime / TRIM / NULLIF so a future extract with format drift fails loudly.'
FROM temp.stg_events_profile;

DROP TABLE temp.stg_events_profile;

-- @query Q00_dq_register
SELECT check_id, dimension, table_name, check_desc, affected_rows, total_rows,
       ROUND(100.0 * affected_rows / NULLIF(total_rows, 0), 2) AS pct_affected, action
FROM dq_register
ORDER BY check_id;

-- @query Q00_column_completeness
-- Column-level NULL profile of the event table (completeness by event type).
SELECT event_type,
       COUNT(*)                                       AS events,
       ROUND(100.0 * AVG(product_id IS NULL), 2)      AS pct_null_product,
       ROUND(100.0 * AVG(quantity IS NULL), 2)        AS pct_null_quantity,
       ROUND(100.0 * AVG(unit_price IS NULL), 2)      AS pct_null_price,
       ROUND(100.0 * AVG(order_id IS NULL), 2)        AS pct_null_order
FROM events
GROUP BY event_type
ORDER BY events DESC;

-- @query Q00_outlier_profile
-- Distribution of sessions per user and events per session: percentiles from ROW_NUMBER (SQLite has no PERCENTILE_CONT).
WITH per_user AS (
    SELECT user_id, COUNT(*) AS n FROM sessions GROUP BY user_id
), per_session AS (
    SELECT session_id, COUNT(*) AS n FROM events GROUP BY session_id
), ranked AS (
    SELECT 'sessions per user' AS metric, n, ROW_NUMBER() OVER (ORDER BY n) AS rn, COUNT(*) OVER () AS cnt FROM per_user
    UNION ALL
    SELECT 'events per session', n, ROW_NUMBER() OVER (ORDER BY n), COUNT(*) OVER () FROM per_session
)
SELECT metric,
       MIN(n)                                                     AS min_value,
       MAX(CASE WHEN rn = CAST(0.25 * cnt AS INTEGER) THEN n END) AS p25,
       MAX(CASE WHEN rn = CAST(0.50 * cnt AS INTEGER) THEN n END) AS median,
       MAX(CASE WHEN rn = CAST(0.75 * cnt AS INTEGER) THEN n END) AS p75,
       MAX(CASE WHEN rn = CAST(0.99 * cnt AS INTEGER) THEN n END) AS p99,
       MAX(n)                                                     AS max_value,
       ROUND(AVG(n), 2)                                           AS mean
FROM ranked
GROUP BY metric;


/* =====================================================================================================
   SECTION 4. DATA CLEANING AND TRANSFORMATION
   No rows are deleted. Flagged rows (DQ register) are carried as 0/1 columns so every metric can state
   exactly what it includes. The derived tables below are the analysis-ready layer used by Sections 5-7.

   Definitions used throughout
     * Product interaction  = product_view, add_to_cart, remove_from_cart or purchase event.
     * Purchase / order     = a row in orders (system of record; 3% of orders are missing from the event stream).
     * Net order            = order whose status is not 'cancelled' or 'returned'. Net revenue = their items_subtotal.
     * Returning user       = user with a session on a later calendar day than their first observed session.
     * Observation window   = 2025-07-07 to 2026-01-04 (26 Monday-start weeks, calendar.week_index 1-26).
   ===================================================================================================== */

-- @exec 4.0 drop derived tables (allows Section 4 to be re-run on its own)
DROP TABLE IF EXISTS main.category_performance;
DROP TABLE IF EXISTS main.product_performance;
DROP TABLE IF EXISTS main.cart_add_outcomes;
DROP TABLE IF EXISTS main.user_product_purchases;
DROP TABLE IF EXISTS main.cohort_retention;
DROP TABLE IF EXISTS main.user_week_activity;
DROP TABLE IF EXISTS main.user_summary;
DROP TABLE IF EXISTS main.session_summary;
DROP TABLE IF EXISTS main.events_enriched;

-- @exec 4.1 events_enriched: every event with calendar, product and sequence attributes
CREATE TABLE events_enriched AS
SELECT
    e.event_id,
    e.session_id,
    e.user_id,
    e.event_timestamp,
    date(e.event_timestamp)                                             AS event_date,
    CAST(strftime('%H', e.event_timestamp) AS INTEGER)                  AS event_hour,
    c.week_index,
    c.week_start_date,
    c.is_weekend,
    CASE WHEN c.promotion_name IS NOT NULL THEN 1 ELSE 0 END            AS promo_period,
    e.event_type,
    CASE WHEN e.event_type IN ('product_view', 'add_to_cart', 'remove_from_cart', 'purchase')
         THEN 1 ELSE 0 END                                              AS is_product_event,
    CASE WHEN e.product_id IS NOT NULL THEN 1 ELSE 0 END                AS product_traceable,
    e.product_id,
    p.category_id,
    cat.category_name,
    e.quantity,
    e.unit_price,
    p.list_price,
    CASE WHEN e.unit_price < p.list_price THEN 1 ELSE 0 END             AS shown_discounted,
    e.order_id,
    ROW_NUMBER() OVER (PARTITION BY e.session_id
                       ORDER BY e.event_timestamp, e.event_id)          AS session_event_seq
FROM events e
LEFT JOIN calendar   c   ON c.date = date(e.event_timestamp)
LEFT JOIN products   p   ON p.product_id = e.product_id
LEFT JOIN categories cat ON cat.category_id = p.category_id;

CREATE UNIQUE INDEX ux_ee_event   ON events_enriched (event_id);
CREATE INDEX ix_ee_session        ON events_enriched (session_id, session_event_seq);
CREATE INDEX ix_ee_type_product   ON events_enriched (event_type, product_id, user_id);
CREATE INDEX ix_ee_user           ON events_enriched (user_id, event_timestamp);

-- @exec 4.2 session_summary: one row per session with engagement counts, funnel flags and the order outcome
CREATE TABLE session_summary (
    session_id                  TEXT    PRIMARY KEY REFERENCES sessions (session_id),
    user_id                     TEXT    NOT NULL REFERENCES users (user_id),
    session_start               TEXT    NOT NULL,
    session_end                 TEXT    NOT NULL,
    session_date                TEXT    NOT NULL,
    week_index                  INTEGER NOT NULL,
    is_weekend                  INTEGER NOT NULL,
    promo_period                INTEGER NOT NULL,
    duration_sec                INTEGER NOT NULL CHECK (duration_sec >= 0),
    device_type                 TEXT    NOT NULL,
    platform                    TEXT    NOT NULL,
    traffic_source              TEXT    NOT NULL,
    user_session_seq            INTEGER NOT NULL,          -- 1 = user's first observed session
    is_first_session            INTEGER NOT NULL,
    days_since_prev_session     REAL,                      -- NULL for the first session
    n_events                    INTEGER NOT NULL,
    n_page_views                INTEGER NOT NULL,
    n_searches                  INTEGER NOT NULL,
    n_product_views             INTEGER NOT NULL,
    n_traceable_product_views   INTEGER NOT NULL,
    n_distinct_products_viewed  INTEGER NOT NULL,
    n_add_to_cart               INTEGER NOT NULL,
    n_remove_from_cart          INTEGER NOT NULL,
    n_begin_checkout            INTEGER NOT NULL,
    n_purchase_events           INTEGER NOT NULL,
    n_product_interactions      INTEGER NOT NULL,
    has_product_view            INTEGER NOT NULL,
    has_add_to_cart             INTEGER NOT NULL,
    has_begin_checkout          INTEGER NOT NULL,
    has_order                   INTEGER NOT NULL,
    order_id                    TEXT    REFERENCES orders (order_id),
    order_status                TEXT,
    order_items_subtotal        INTEGER,
    is_net_order                INTEGER NOT NULL,
    funnel_stage                TEXT    NOT NULL,
    funnel_stage_rank           INTEGER NOT NULL
);

INSERT INTO session_summary
WITH ev AS (
    SELECT
        session_id,
        COUNT(*)                                                               AS n_events,
        SUM(event_type = 'page_view')                                          AS n_page_views,
        SUM(event_type = 'search')                                             AS n_searches,
        SUM(event_type = 'product_view')                                       AS n_product_views,
        SUM(event_type = 'product_view' AND product_id IS NOT NULL)            AS n_traceable_product_views,
        COUNT(DISTINCT CASE WHEN event_type = 'product_view' THEN product_id END) AS n_distinct_products_viewed,
        SUM(event_type = 'add_to_cart')                                        AS n_add_to_cart,
        SUM(event_type = 'remove_from_cart')                                   AS n_remove_from_cart,
        SUM(event_type = 'begin_checkout')                                     AS n_begin_checkout,
        SUM(event_type = 'purchase')                                           AS n_purchase_events,
        SUM(is_product_event)                                                  AS n_product_interactions,
        MAX(promo_period)                                                      AS promo_period
    FROM events_enriched
    GROUP BY session_id
), seq AS (
    SELECT
        s.*,
        ROW_NUMBER() OVER w                                                    AS user_session_seq,
        LAG(s.session_start) OVER w                                            AS prev_session_start
    FROM sessions s
    WINDOW w AS (PARTITION BY s.user_id ORDER BY s.session_start, s.session_id)
)
SELECT
    q.session_id,
    q.user_id,
    q.session_start,
    q.session_end,
    date(q.session_start)                                                      AS session_date,
    c.week_index,
    c.is_weekend,
    COALESCE(ev.promo_period, CASE WHEN c.promotion_name IS NOT NULL THEN 1 ELSE 0 END),
    CAST(ROUND((julianday(q.session_end) - julianday(q.session_start)) * 86400) AS INTEGER),
    q.device_type,
    q.platform,
    q.traffic_source,
    q.user_session_seq,
    CASE WHEN q.user_session_seq = 1 THEN 1 ELSE 0 END,
    ROUND(julianday(q.session_start) - julianday(q.prev_session_start), 3),
    ev.n_events, ev.n_page_views, ev.n_searches, ev.n_product_views, ev.n_traceable_product_views,
    ev.n_distinct_products_viewed, ev.n_add_to_cart, ev.n_remove_from_cart, ev.n_begin_checkout,
    ev.n_purchase_events, ev.n_product_interactions,
    CASE WHEN ev.n_product_views  > 0 THEN 1 ELSE 0 END,
    CASE WHEN ev.n_add_to_cart    > 0 THEN 1 ELSE 0 END,
    CASE WHEN ev.n_begin_checkout > 0 THEN 1 ELSE 0 END,
    CASE WHEN o.order_id IS NOT NULL THEN 1 ELSE 0 END,
    o.order_id,
    o.order_status,
    o.items_subtotal,
    CASE WHEN o.order_id IS NOT NULL AND o.order_status NOT IN ('cancelled', 'returned') THEN 1 ELSE 0 END,
    CASE
        WHEN o.order_id IS NOT NULL      THEN '4 Ordered'
        WHEN ev.n_begin_checkout > 0     THEN '3 Began checkout'
        WHEN ev.n_add_to_cart > 0        THEN '2 Added to cart'
        WHEN ev.n_product_views > 0      THEN '1 Viewed a product'
        ELSE '0 Browsed only'
    END,
    CASE
        WHEN o.order_id IS NOT NULL      THEN 4
        WHEN ev.n_begin_checkout > 0     THEN 3
        WHEN ev.n_add_to_cart > 0        THEN 2
        WHEN ev.n_product_views > 0      THEN 1
        ELSE 0
    END
FROM seq q
JOIN ev            ON ev.session_id = q.session_id
JOIN calendar c    ON c.date = date(q.session_start)
LEFT JOIN orders o ON o.session_id = q.session_id;

CREATE INDEX ix_ss_user     ON session_summary (user_id, session_start);
CREATE INDEX ix_ss_week     ON session_summary (week_index);
CREATE INDEX ix_ss_date     ON session_summary (session_date);

-- @exec 4.3 user_summary: one row per user with lifecycle, engagement, funnel and return flags
CREATE TABLE user_summary (
    user_id                     TEXT    PRIMARY KEY REFERENCES users (user_id),
    is_registered               INTEGER NOT NULL,
    is_known_existing_customer  INTEGER NOT NULL,      -- signed up before the observation window started
    signup_date                 TEXT,
    acquisition_channel         TEXT    NOT NULL,
    city                        TEXT    NOT NULL,
    primary_device              TEXT    NOT NULL,
    is_loyalty_member           INTEGER NOT NULL,      -- status at extract date
    first_seen_ts               TEXT    NOT NULL,
    last_seen_ts                TEXT    NOT NULL,
    first_seen_date             TEXT    NOT NULL,
    cohort_week                 INTEGER NOT NULL,      -- week_index of the first observed session
    cohort_week_start           TEXT    NOT NULL,
    followup_days               INTEGER NOT NULL,      -- days from first_seen_date to the end of the data
    first_session_platform      TEXT    NOT NULL,
    first_session_device        TEXT    NOT NULL,
    first_session_source        TEXT    NOT NULL,
    first_session_stage_rank    INTEGER NOT NULL,
    n_sessions                  INTEGER NOT NULL,
    n_active_days               INTEGER NOT NULL,
    n_active_weeks              INTEGER NOT NULL,
    n_product_views             INTEGER NOT NULL,
    n_add_to_cart               INTEGER NOT NULL,
    n_begin_checkout            INTEGER NOT NULL,
    n_orders                    INTEGER NOT NULL,
    n_net_orders                INTEGER NOT NULL,
    net_revenue                 INTEGER NOT NULL,
    first_order_ts              TEXT,
    days_to_first_order         REAL,
    ever_viewed_product         INTEGER NOT NULL,
    ever_added_to_cart          INTEGER NOT NULL,
    ever_began_checkout         INTEGER NOT NULL,
    ever_ordered                INTEGER NOT NULL,
    ever_purchase_event         INTEGER NOT NULL,
    returned_later_day          INTEGER NOT NULL,
    days_to_return              INTEGER,               -- days from first_seen_date to the next active day
    returned_within_7d          INTEGER,               -- NULL when fewer than 7 days of follow-up (censored)
    returned_within_14d         INTEGER,
    returned_within_28d         INTEGER,
    is_repeat_buyer             INTEGER NOT NULL,
    engagement_segment          TEXT    NOT NULL
);

INSERT INTO user_summary
WITH bounds AS (
    SELECT MIN(date) AS start_date, MAX(date) AS end_date FROM calendar
), sess AS (
    SELECT
        user_id,
        MIN(session_start)                          AS first_seen_ts,
        MAX(session_start)                          AS last_seen_ts,
        MIN(session_date)                           AS first_seen_date,
        MIN(week_index)                             AS cohort_week,
        COUNT(*)                                    AS n_sessions,
        COUNT(DISTINCT session_date)                AS n_active_days,
        COUNT(DISTINCT week_index)                  AS n_active_weeks,
        SUM(n_product_views)                        AS n_product_views,
        SUM(n_add_to_cart)                          AS n_add_to_cart,
        SUM(n_begin_checkout)                       AS n_begin_checkout,
        SUM(has_order)                              AS n_orders,
        SUM(is_net_order)                           AS n_net_orders,
        SUM(CASE WHEN is_net_order = 1 THEN order_items_subtotal ELSE 0 END) AS net_revenue,
        MIN(CASE WHEN has_order = 1 THEN session_start END)                  AS first_order_session_ts,
        MAX(has_product_view)                       AS ever_viewed_product,
        MAX(has_add_to_cart)                        AS ever_added_to_cart,
        MAX(has_begin_checkout)                     AS ever_began_checkout,
        MAX(has_order)                              AS ever_ordered,
        MAX(n_purchase_events > 0)                  AS ever_purchase_event
    FROM session_summary
    GROUP BY user_id
), first_session AS (
    SELECT user_id, platform, device_type, traffic_source, funnel_stage_rank
    FROM session_summary
    WHERE user_session_seq = 1
), next_day AS (            -- first active day after the first-seen day
    SELECT ss.user_id, MIN(ss.session_date) AS next_active_date
    FROM session_summary ss
    JOIN sess s ON s.user_id = ss.user_id
    WHERE ss.session_date > s.first_seen_date
    GROUP BY ss.user_id
), first_order AS (
    SELECT user_id, MIN(order_timestamp) AS first_order_ts FROM orders GROUP BY user_id
)
SELECT
    u.user_id,
    CASE WHEN u.signup_date IS NOT NULL THEN 1 ELSE 0 END,
    CASE WHEN u.signup_date < b.start_date THEN 1 ELSE 0 END,
    u.signup_date,
    u.acquisition_channel,
    u.city,
    u.primary_device,
    u.is_loyalty_member,
    s.first_seen_ts,
    s.last_seen_ts,
    s.first_seen_date,
    s.cohort_week,
    (SELECT week_start_date FROM calendar WHERE week_index = s.cohort_week LIMIT 1),
    CAST(julianday(b.end_date) - julianday(s.first_seen_date) AS INTEGER),
    fs.platform,
    fs.device_type,
    fs.traffic_source,
    fs.funnel_stage_rank,
    s.n_sessions, s.n_active_days, s.n_active_weeks, s.n_product_views, s.n_add_to_cart, s.n_begin_checkout,
    s.n_orders, s.n_net_orders, s.net_revenue,
    fo.first_order_ts,
    ROUND(julianday(fo.first_order_ts) - julianday(s.first_seen_ts), 2),
    s.ever_viewed_product, s.ever_added_to_cart, s.ever_began_checkout, s.ever_ordered, s.ever_purchase_event,
    CASE WHEN nd.next_active_date IS NOT NULL THEN 1 ELSE 0 END,
    CAST(julianday(nd.next_active_date) - julianday(s.first_seen_date) AS INTEGER),
    -- right-censoring: only users observed for at least N days after their first day get a 0/1 value
    CASE WHEN julianday(b.end_date) - julianday(s.first_seen_date) < 7  THEN NULL
         WHEN julianday(nd.next_active_date) - julianday(s.first_seen_date) <= 7  THEN 1 ELSE 0 END,
    CASE WHEN julianday(b.end_date) - julianday(s.first_seen_date) < 14 THEN NULL
         WHEN julianday(nd.next_active_date) - julianday(s.first_seen_date) <= 14 THEN 1 ELSE 0 END,
    CASE WHEN julianday(b.end_date) - julianday(s.first_seen_date) < 28 THEN NULL
         WHEN julianday(nd.next_active_date) - julianday(s.first_seen_date) <= 28 THEN 1 ELSE 0 END,
    CASE WHEN s.n_orders >= 2 THEN 1 ELSE 0 END,
    CASE WHEN s.n_sessions = 1  THEN '1 One session'
         WHEN s.n_sessions <= 3 THEN '2 Occasional (2-3 sessions)'
         WHEN s.n_sessions <= 9 THEN '3 Regular (4-9 sessions)'
         ELSE '4 Heavy (10+ sessions)' END
FROM users u
CROSS JOIN bounds b
JOIN sess s                ON s.user_id = u.user_id
JOIN first_session fs      ON fs.user_id = u.user_id
LEFT JOIN next_day nd      ON nd.user_id = u.user_id
LEFT JOIN first_order fo   ON fo.user_id = u.user_id;

CREATE INDEX ix_us_cohort ON user_summary (cohort_week);

-- @exec 4.4 user_week_activity and cohort_retention (recursive CTE generates every week offset)
CREATE TABLE user_week_activity (
    user_id      TEXT    NOT NULL REFERENCES users (user_id),
    week_index   INTEGER NOT NULL,
    sessions     INTEGER NOT NULL,
    orders       INTEGER NOT NULL,
    PRIMARY KEY (user_id, week_index)
);

INSERT INTO user_week_activity
SELECT user_id, week_index, COUNT(*), SUM(has_order)
FROM session_summary
GROUP BY user_id, week_index;

CREATE TABLE cohort_retention (
    cohort_week      INTEGER NOT NULL,
    cohort_start     TEXT    NOT NULL,
    week_offset      INTEGER NOT NULL,
    cohort_users     INTEGER NOT NULL,
    active_users     INTEGER NOT NULL,
    retention_rate   REAL    NOT NULL,
    PRIMARY KEY (cohort_week, week_offset)
);

INSERT INTO cohort_retention
WITH RECURSIVE offsets(week_offset) AS (
    SELECT 0
    UNION ALL
    SELECT week_offset + 1 FROM offsets WHERE week_offset < 25
), cohort_size AS (
    SELECT cohort_week, MIN(cohort_week_start) AS cohort_start, COUNT(*) AS cohort_users
    FROM user_summary
    GROUP BY cohort_week
), activity AS (
    SELECT us.cohort_week, w.week_index - us.cohort_week AS week_offset, COUNT(*) AS active_users
    FROM user_week_activity w
    JOIN user_summary us ON us.user_id = w.user_id
    GROUP BY us.cohort_week, w.week_index - us.cohort_week
)
SELECT cs.cohort_week, cs.cohort_start, o.week_offset, cs.cohort_users,
       COALESCE(a.active_users, 0),
       ROUND(1.0 * COALESCE(a.active_users, 0) / cs.cohort_users, 4)
FROM cohort_size cs
CROSS JOIN offsets o
LEFT JOIN activity a ON a.cohort_week = cs.cohort_week AND a.week_offset = o.week_offset
WHERE cs.cohort_week + o.week_offset <= 26;          -- only weeks that have actually been observed

-- @exec 4.5 user_product_purchases and cart_add_outcomes (product-level purchase and abandonment base)
CREATE TABLE user_product_purchases AS
SELECT o.user_id, oi.product_id, p.category_id, o.order_id, o.session_id, o.order_timestamp, o.order_status,
       oi.quantity, oi.line_total,
       CASE WHEN o.order_status NOT IN ('cancelled', 'returned') THEN 1 ELSE 0 END AS is_net
FROM orders o
JOIN order_items oi ON oi.order_id = o.order_id
JOIN products p     ON p.product_id = oi.product_id;

CREATE INDEX ix_upp_user_product ON user_product_purchases (user_id, product_id, order_timestamp);
CREATE INDEX ix_upp_product      ON user_product_purchases (product_id);
CREATE INDEX ix_upp_user_category ON user_product_purchases (user_id, category_id);

-- One row per traceable add-to-cart. A cart addition counts as abandoned when the same user does not
-- order that product within 7 days. Additions in the last 7 days of data are censored (outcome unknown).
CREATE TABLE cart_add_outcomes AS
WITH adds AS (
    SELECT event_id, session_id, user_id, product_id, category_id, event_timestamp AS added_ts
    FROM events_enriched
    WHERE event_type = 'add_to_cart' AND product_id IS NOT NULL
), last_ts AS (
    SELECT MAX(event_timestamp) AS end_ts FROM events
)
SELECT
    a.event_id, a.session_id, a.user_id, a.product_id, a.category_id, a.added_ts,
    CASE WHEN julianday(l.end_ts) - julianday(a.added_ts) < 7 THEN 1 ELSE 0 END AS is_censored,
    EXISTS (SELECT 1 FROM user_product_purchases p
            WHERE p.user_id = a.user_id AND p.product_id = a.product_id AND p.session_id = a.session_id) AS purchased_same_session,
    EXISTS (SELECT 1 FROM user_product_purchases p
            WHERE p.user_id = a.user_id AND p.product_id = a.product_id
              AND p.order_timestamp >= a.added_ts
              AND julianday(p.order_timestamp) - julianday(a.added_ts) <= 7)                     AS purchased_within_7d,
    EXISTS (SELECT 1 FROM events_enriched r
            WHERE r.session_id = a.session_id AND r.event_type = 'remove_from_cart'
              AND r.product_id = a.product_id AND r.event_timestamp >= a.added_ts)               AS removed_in_session
FROM adds a
CROSS JOIN last_ts l;

CREATE INDEX ix_cao_product ON cart_add_outcomes (product_id);

-- @exec 4.6 product_performance: one row per product with views, carts, purchases, conversion and ranks
CREATE TABLE product_performance (
    product_id              TEXT    PRIMARY KEY REFERENCES products (product_id),
    product_name            TEXT    NOT NULL,
    category_name           TEXT    NOT NULL,
    brand                   TEXT    NOT NULL,
    list_price              INTEGER NOT NULL,
    avg_rating              REAL,
    is_active               INTEGER NOT NULL,
    views                   INTEGER NOT NULL,
    viewers                 INTEGER NOT NULL,
    cart_adds               INTEGER NOT NULL,
    cart_users              INTEGER NOT NULL,
    orders                  INTEGER NOT NULL,
    units                   INTEGER NOT NULL,
    buyers                  INTEGER NOT NULL,
    viewer_buyers           INTEGER NOT NULL,      -- users who viewed the product and also bought it
    net_revenue             INTEGER NOT NULL,
    view_to_cart_rate       REAL,                  -- cart_users / viewers
    view_to_purchase_rate   REAL,                  -- viewer_buyers / viewers
    vtp_wilson_lower        REAL,                  -- 95% Wilson lower bound of view_to_purchase_rate
    cart_adds_observed      INTEGER NOT NULL,      -- cart additions with 7 days of follow-up
    cart_adds_abandoned     INTEGER NOT NULL,
    cart_abandonment_rate   REAL,
    view_rank               INTEGER NOT NULL,
    units_rank              INTEGER NOT NULL,
    revenue_rank            INTEGER NOT NULL,
    units_rank_in_category  INTEGER NOT NULL
);

INSERT INTO product_performance
WITH v AS (
    SELECT product_id, COUNT(*) AS views, COUNT(DISTINCT user_id) AS viewers
    FROM events_enriched WHERE event_type = 'product_view' AND product_id IS NOT NULL GROUP BY product_id
), c AS (
    SELECT product_id, COUNT(*) AS cart_adds, COUNT(DISTINCT user_id) AS cart_users
    FROM events_enriched WHERE event_type = 'add_to_cart' AND product_id IS NOT NULL GROUP BY product_id
), b AS (
    SELECT product_id, COUNT(DISTINCT order_id) AS orders, SUM(quantity) AS units, COUNT(DISTINCT user_id) AS buyers,
           SUM(CASE WHEN is_net = 1 THEN line_total ELSE 0 END) AS net_revenue
    FROM user_product_purchases GROUP BY product_id
), vb AS (            -- EXISTS uses ix_upp_user_product; joining two DISTINCT subqueries forced a nested scan
    SELECT v.product_id, COUNT(*) AS viewer_buyers
    FROM (SELECT DISTINCT user_id, product_id FROM events_enriched WHERE event_type = 'product_view' AND product_id IS NOT NULL) v
    WHERE EXISTS (SELECT 1 FROM user_product_purchases p WHERE p.user_id = v.user_id AND p.product_id = v.product_id)
    GROUP BY v.product_id
), ab AS (
    SELECT product_id, SUM(1 - is_censored) AS observed,
           SUM(CASE WHEN is_censored = 0 AND purchased_within_7d = 0 THEN 1 ELSE 0 END) AS abandoned
    FROM cart_add_outcomes GROUP BY product_id
), base AS (
    SELECT p.product_id, p.product_name, cat.category_name, p.brand, p.list_price, p.avg_rating, p.is_active,
           COALESCE(v.views, 0) AS views, COALESCE(v.viewers, 0) AS viewers,
           COALESCE(c.cart_adds, 0) AS cart_adds, COALESCE(c.cart_users, 0) AS cart_users,
           COALESCE(b.orders, 0) AS orders, COALESCE(b.units, 0) AS units, COALESCE(b.buyers, 0) AS buyers,
           COALESCE(vb.viewer_buyers, 0) AS viewer_buyers, COALESCE(b.net_revenue, 0) AS net_revenue,
           COALESCE(ab.observed, 0) AS observed, COALESCE(ab.abandoned, 0) AS abandoned
    FROM products p
    JOIN categories cat ON cat.category_id = p.category_id
    LEFT JOIN v  ON v.product_id  = p.product_id
    LEFT JOIN c  ON c.product_id  = p.product_id
    LEFT JOIN b  ON b.product_id  = p.product_id
    LEFT JOIN vb ON vb.product_id = p.product_id
    LEFT JOIN ab ON ab.product_id = p.product_id
)
SELECT
    product_id, product_name, category_name, brand, list_price, avg_rating, is_active,
    views, viewers, cart_adds, cart_users, orders, units, buyers, viewer_buyers, net_revenue,
    ROUND(1.0 * cart_users / NULLIF(viewers, 0), 4),
    ROUND(1.0 * viewer_buyers / NULLIF(viewers, 0), 4),
    -- Wilson score lower bound (z = 1.96): ranks conversion without rewarding tiny samples
    CASE WHEN viewers > 0 THEN ROUND(
        ( (1.0 * viewer_buyers / viewers) + 1.9208 / viewers
          - 1.96 * sqrt( (1.0 * viewer_buyers / viewers) * (1 - 1.0 * viewer_buyers / viewers) / viewers + 0.9604 / (1.0 * viewers * viewers) ) )
        / (1 + 3.8416 / viewers), 4) END,
    observed, abandoned,
    ROUND(1.0 * abandoned / NULLIF(observed, 0), 4),
    RANK() OVER (ORDER BY views DESC),
    RANK() OVER (ORDER BY units DESC),
    RANK() OVER (ORDER BY net_revenue DESC),
    DENSE_RANK() OVER (PARTITION BY category_name ORDER BY units DESC)
FROM base;

-- @exec 4.7 category_performance: category-level funnel and purchase activity (distinct users counted at category level)
CREATE TABLE category_performance AS
WITH v AS (
    SELECT category_name, COUNT(*) AS views, COUNT(DISTINCT user_id) AS viewers
    FROM events_enriched WHERE event_type = 'product_view' AND product_id IS NOT NULL GROUP BY category_name
), c AS (
    SELECT category_name, COUNT(*) AS cart_adds, COUNT(DISTINCT user_id) AS cart_users
    FROM events_enriched WHERE event_type = 'add_to_cart' AND product_id IS NOT NULL GROUP BY category_name
), b AS (
    SELECT cat.category_name, COUNT(DISTINCT p.order_id) AS orders, SUM(p.quantity) AS units,
           COUNT(DISTINCT p.user_id) AS buyers, SUM(CASE WHEN p.is_net = 1 THEN p.line_total ELSE 0 END) AS net_revenue
    FROM user_product_purchases p JOIN categories cat ON cat.category_id = p.category_id
    GROUP BY cat.category_name
), vb AS (
    SELECT v.category_name, COUNT(*) AS viewer_buyers
    FROM (SELECT DISTINCT user_id, category_id, category_name FROM events_enriched
          WHERE event_type = 'product_view' AND product_id IS NOT NULL) v
    WHERE EXISTS (SELECT 1 FROM user_product_purchases p WHERE p.user_id = v.user_id AND p.category_id = v.category_id)
    GROUP BY v.category_name
)
SELECT cat.category_name, cat.department,
       (SELECT COUNT(*) FROM products p WHERE p.category_id = cat.category_id) AS products,
       v.views, v.viewers, c.cart_adds, c.cart_users, b.orders, b.units, b.buyers, vb.viewer_buyers, b.net_revenue,
       ROUND(1.0 * c.cart_users / v.viewers, 4)     AS view_to_cart_rate,
       ROUND(1.0 * vb.viewer_buyers / v.viewers, 4) AS view_to_purchase_rate,
       ROUND(1.0 * v.views / SUM(v.views) OVER (), 4)              AS share_of_views,
       ROUND(1.0 * b.orders / SUM(b.orders) OVER (), 4)            AS share_of_orders,
       ROUND(1.0 * b.net_revenue / SUM(b.net_revenue) OVER (), 4)  AS share_of_net_revenue
FROM categories cat
JOIN v  ON v.category_name  = cat.category_name
JOIN c  ON c.category_name  = cat.category_name
JOIN b  ON b.category_name  = cat.category_name
JOIN vb ON vb.category_name = cat.category_name;

-- @query Q00_derived_table_sizes
SELECT 'events_enriched' AS table_name, COUNT(*) AS rows FROM events_enriched
UNION ALL SELECT 'session_summary',        COUNT(*) FROM session_summary
UNION ALL SELECT 'user_summary',           COUNT(*) FROM user_summary
UNION ALL SELECT 'user_week_activity',     COUNT(*) FROM user_week_activity
UNION ALL SELECT 'cohort_retention',       COUNT(*) FROM cohort_retention
UNION ALL SELECT 'user_product_purchases', COUNT(*) FROM user_product_purchases
UNION ALL SELECT 'cart_add_outcomes',      COUNT(*) FROM cart_add_outcomes
UNION ALL SELECT 'product_performance',    COUNT(*) FROM product_performance
UNION ALL SELECT 'category_performance',   COUNT(*) FROM category_performance;


/* =====================================================================================================
   SECTION 5. ANALYTICAL QUERIES
   Each query answers one of the Product Manager's questions. The comment above each query states the
   question, the technique and how to read the output.
   ===================================================================================================== */

/* -----------------------------------------------------------------------------------------------------
   5A. USER ENGAGEMENT  (Objective 1)
   ----------------------------------------------------------------------------------------------------- */

-- @query Q01_platform_overview
-- How many unique users interacted with the platform, and how many product views were recorded?
-- Technique: scalar subqueries over the cleaned and derived tables, one headline row.
-- Finding (tested run): 30,000 unique users (10,586 registered, 19,414 guests) generated 89,557 sessions, 590,648 events and
--          311,955 product views (310,541 traceable to a product). 4,655 buyers placed 6,896 orders; 6,235 net
--          orders produced 512.2m net revenue (average 82,149 per net order).
SELECT
    (SELECT COUNT(*) FROM user_summary)                                        AS unique_users,
    (SELECT SUM(is_registered) FROM user_summary)                              AS registered_users,
    (SELECT COUNT(*) - SUM(is_registered) FROM user_summary)                   AS guest_users,
    (SELECT COUNT(*) FROM session_summary)                                     AS sessions,
    (SELECT COUNT(*) FROM events)                                              AS events,
    (SELECT COUNT(*) FROM events WHERE event_type = 'product_view')            AS product_views,
    (SELECT COUNT(*) FROM events WHERE event_type = 'product_view' AND product_id IS NOT NULL) AS traceable_product_views,
    (SELECT COUNT(DISTINCT product_id) FROM events WHERE event_type = 'product_view') AS products_viewed,
    (SELECT SUM(n_product_interactions) FROM session_summary)                  AS product_interactions,
    (SELECT COUNT(*) FROM orders)                                              AS orders,
    (SELECT COUNT(DISTINCT user_id) FROM orders)                               AS buyers,
    (SELECT SUM(is_net_order) FROM session_summary)                            AS net_orders,
    (SELECT SUM(net_revenue) FROM user_summary)                                AS net_revenue,
    (SELECT ROUND(1.0 * SUM(net_revenue) / SUM(n_net_orders), 0) FROM user_summary) AS avg_net_order_value,
    (SELECT ROUND(AVG(n_sessions), 2) FROM user_summary)                       AS sessions_per_user;

-- @query Q02_session_engagement
-- What is the average number of product interactions per session?
-- Technique: conditional aggregation plus a median from ROW_NUMBER (no PERCENTILE function in SQLite).
-- Finding (tested run): A session averages 6.6 events and 3.99 product interactions (median 3; 4.77 when the session has
--          any). 16.3% of sessions have no product interaction and 22.7% contain a single event. Average
--          session length is 4.4 minutes.
WITH ranked AS (
    SELECT n_product_interactions,
           ROW_NUMBER() OVER (ORDER BY n_product_interactions) AS rn,
           COUNT(*) OVER ()                                    AS n
    FROM session_summary
)
SELECT
    (SELECT COUNT(*) FROM session_summary)                                                     AS sessions,
    (SELECT ROUND(AVG(n_events), 2) FROM session_summary)                                      AS avg_events_per_session,
    (SELECT ROUND(AVG(n_product_interactions), 2) FROM session_summary)                        AS avg_product_interactions_per_session,
    (SELECT MAX(n_product_interactions) FROM ranked WHERE rn = (n + 1) / 2)                    AS median_product_interactions,
    (SELECT ROUND(AVG(n_product_interactions), 2) FROM session_summary WHERE n_product_interactions > 0) AS avg_interactions_when_any,
    (SELECT ROUND(AVG(n_product_views), 2) FROM session_summary)                               AS avg_product_views_per_session,
    (SELECT ROUND(AVG(n_distinct_products_viewed), 2) FROM session_summary WHERE has_product_view = 1) AS avg_distinct_products_when_viewing,
    (SELECT ROUND(100.0 * AVG(n_product_interactions = 0), 2) FROM session_summary)            AS pct_sessions_without_product_interaction,
    (SELECT ROUND(100.0 * AVG(n_events = 1), 2) FROM session_summary)                          AS pct_single_event_sessions,
    (SELECT ROUND(AVG(n_searches > 0) * 100, 2) FROM session_summary)                          AS pct_sessions_with_search,
    (SELECT ROUND(AVG(duration_sec) / 60.0, 2) FROM session_summary)                           AS avg_session_minutes;

-- @query Q03_return_frequency
-- How frequently do users return? Distribution of users by number of sessions, with running cumulative share.
-- Technique: CASE bucketing, window SUM for share and running total.
-- Finding (tested run): 55.7% of users were seen in only one session; 6.0% (1,789) had 10 or more. The share who ordered
--          rises from 2.5% of one-session users to 75.6% of 10+ session users. This is an association: buying
--          itself generates sessions.
WITH buckets AS (
    SELECT CASE WHEN n_sessions = 1 THEN '1'
                WHEN n_sessions = 2 THEN '2'
                WHEN n_sessions = 3 THEN '3'
                WHEN n_sessions <= 5 THEN '4-5'
                WHEN n_sessions <= 9 THEN '6-9'
                ELSE '10+' END                        AS sessions_bucket,
           MIN(n_sessions)                            AS sort_key,
           COUNT(*)                                   AS users,
           ROUND(AVG(n_active_weeks), 2)              AS avg_active_weeks,
           ROUND(AVG(ever_ordered) * 100, 1)          AS pct_ordered
    FROM user_summary
    GROUP BY 1
)
SELECT sessions_bucket, users,
       ROUND(100.0 * users / SUM(users) OVER (), 2)                                           AS pct_users,
       ROUND(100.0 * SUM(users) OVER (ORDER BY sort_key ROWS UNBOUNDED PRECEDING) / SUM(users) OVER (), 2) AS cumulative_pct,
       avg_active_weeks, pct_ordered
FROM buckets
ORDER BY sort_key;

-- @query Q03b_time_between_sessions
-- When users come back, how soon? Gaps between consecutive sessions (LAG, already stored as days_since_prev_session).
-- Finding (tested run): Users who come back do so quickly: across 59,557 repeat sessions the median gap is 2.7 days and
--          78.3% come within 7 days of the previous session.
WITH gaps AS (
    SELECT days_since_prev_session AS gap,
           ROW_NUMBER() OVER (ORDER BY days_since_prev_session) AS rn,
           COUNT(*) OVER () AS n
    FROM session_summary
    WHERE days_since_prev_session IS NOT NULL
)
SELECT
    COUNT(*)                                                    AS repeat_sessions,
    ROUND(AVG(gap), 2)                                          AS mean_gap_days,
    ROUND(MAX(CASE WHEN rn = (n + 1) / 2 THEN gap END), 2)      AS median_gap_days,
    ROUND(100.0 * AVG(gap < 1), 1)                              AS pct_within_1_day,
    ROUND(100.0 * AVG(gap <= 7), 1)                             AS pct_within_7_days,
    ROUND(100.0 * AVG(gap <= 30), 1)                            AS pct_within_30_days,
    ROUND(100.0 * AVG(gap > 30), 1)                             AS pct_after_30_days
FROM gaps;

-- @query Q04_weekly_engagement_trend
-- How does engagement move week by week? WAU, new vs returning users, week-over-week change (LAG),
-- 4-week moving average (window AVG) and the running total of users reached (cumulative SUM).
-- Finding (tested run): Weekly active users were flat at about 2,000-2,300 from July to mid-November. They rose to 3,441 in
--          Black Friday week (24 Nov, +33.3% week on week) and fell to 1,857 in the final week. Session
--          conversion peaked at 9.5% in the two Black Friday weeks against 7-8% in normal weeks.
WITH weekly AS (
    SELECT ss.week_index,
           MIN(c.week_start_date)                       AS week_start,
           COUNT(DISTINCT ss.user_id)                   AS active_users,
           COUNT(DISTINCT CASE WHEN us.cohort_week = ss.week_index THEN ss.user_id END) AS new_users,
           COUNT(*)                                     AS sessions,
           SUM(ss.n_product_views)                      AS product_views,
           SUM(ss.has_order)                            AS orders,
           MAX(ss.promo_period)                         AS promo_week
    FROM session_summary ss
    JOIN user_summary us ON us.user_id = ss.user_id
    JOIN calendar c      ON c.date = ss.session_date
    GROUP BY ss.week_index
)
SELECT week_index, week_start, promo_week, active_users, new_users,
       active_users - new_users                                                      AS returning_users,
       ROUND(100.0 * (active_users - new_users) / active_users, 1)                   AS pct_returning,
       sessions, product_views, orders,
       ROUND(100.0 * orders / sessions, 2)                                           AS session_conversion_pct,
       ROUND(100.0 * (active_users - LAG(active_users) OVER w) / LAG(active_users) OVER w, 1) AS wau_wow_change_pct,
       ROUND(AVG(active_users) OVER (ORDER BY week_index ROWS BETWEEN 3 PRECEDING AND CURRENT ROW), 0) AS wau_4wk_moving_avg,
       SUM(new_users) OVER (ORDER BY week_index ROWS UNBOUNDED PRECEDING)            AS cumulative_users_reached
FROM weekly
WINDOW w AS (ORDER BY week_index)
ORDER BY week_index;

-- @query Q05_engagement_by_platform
-- Does engagement differ by platform and device? Share of sessions, interactions and conversion per segment,
-- compared with the overall rate (window over the whole result).
-- Finding (tested run): Web on mobile is the largest segment (38.6% of sessions) and converts worst (5.6% of sessions, -2.1
--          pp vs overall). Web on desktop converts at 11.7% (+4.0 pp).
WITH seg AS (
    SELECT platform, device_type,
           COUNT(*)                                        AS sessions,
           ROUND(AVG(n_product_interactions), 2)           AS avg_product_interactions,
           ROUND(AVG(duration_sec) / 60.0, 2)              AS avg_minutes,
           SUM(has_product_view)                           AS view_sessions,
           SUM(has_product_view * has_add_to_cart)         AS view_cart_sessions,
           SUM(has_order)                                  AS order_sessions
    FROM session_summary
    GROUP BY platform, device_type
)
SELECT platform, device_type, sessions,
       ROUND(100.0 * sessions / SUM(sessions) OVER (), 1)                         AS pct_sessions,
       avg_product_interactions, avg_minutes,
       ROUND(100.0 * view_cart_sessions / view_sessions, 2)                       AS view_to_cart_pct,
       ROUND(100.0 * order_sessions / sessions, 2)                                AS session_conversion_pct,
       ROUND(100.0 * order_sessions / sessions
             - 100.0 * SUM(order_sessions) OVER () / SUM(sessions) OVER (), 2)    AS conversion_vs_overall_pp
FROM seg
ORDER BY sessions DESC;

-- @query Q06_top_viewed_products
-- Which products receive the most views? Top 15 with share of all traceable views and running cumulative share.
-- Finding (tested run): Voltix Tablet K45 is the most-viewed product (12,399 views, 4.0% of all views). Six of the top 15
--          viewed products are not in the top 25 by units sold (units_rank 26-87).
SELECT view_rank, product_id, product_name, category_name, views, viewers,
       ROUND(100.0 * views / SUM(views) OVER (), 2)                                                   AS pct_of_views,
       ROUND(100.0 * SUM(views) OVER (ORDER BY views DESC, product_id ROWS UNBOUNDED PRECEDING)
             / SUM(views) OVER (), 2)                                                                 AS cumulative_pct,
       units_rank,
       ROUND(100.0 * view_to_purchase_rate, 2)                                                        AS view_to_purchase_pct
FROM product_performance
ORDER BY views DESC, product_id
LIMIT 15;

-- @query Q06b_view_concentration
-- How concentrated is attention? Share of views captured by the top 10, 25 and 50 products (Pareto check).
-- Finding (tested run): Attention is concentrated: the top 10 products (4% of the catalogue) get 22.6% of views and the top
--          50 (20%) get 56.7%.
WITH ranked AS (
    SELECT views, ROW_NUMBER() OVER (ORDER BY views DESC, product_id) AS rn,
           SUM(views) OVER () AS total_views, COUNT(*) OVER () AS n_products
    FROM product_performance
)
SELECT 'Top 10 products' AS product_group, ROUND(100.0 * SUM(views) / MAX(total_views), 1) AS pct_of_views, ROUND(100.0 * 10 / MAX(n_products), 1) AS pct_of_catalogue FROM ranked WHERE rn <= 10
UNION ALL SELECT 'Top 25 products', ROUND(100.0 * SUM(views) / MAX(total_views), 1), ROUND(100.0 * 25 / MAX(n_products), 1) FROM ranked WHERE rn <= 25
UNION ALL SELECT 'Top 50 products', ROUND(100.0 * SUM(views) / MAX(total_views), 1), ROUND(100.0 * 50 / MAX(n_products), 1) FROM ranked WHERE rn <= 50;


/* -----------------------------------------------------------------------------------------------------
   5B. CONVERSION FUNNEL AND ABANDONMENT  (Objectives 2 and 3)
   ----------------------------------------------------------------------------------------------------- */

-- @query Q07_user_funnel
-- How many users viewed products, added to cart, began checkout and purchased? Where is the largest drop?
-- Closed funnel: each stage counts users who also reached every earlier stage. Purchases come from orders.
-- Technique: UNION ALL of stage counts, LAG for step conversion, RANK to identify the largest drop-off.
-- Finding (tested run): Of 26,810 product viewers, 43.2% added to cart, 22.0% began checkout and 17.4% ordered. The largest
--          drop-off is view -> cart (15,240 users, 56.8%), followed by cart -> checkout (5,686 users, 49.1%).
--          Checkout -> order loses 20.9%.
WITH stages AS (
    SELECT 1 AS stage_no, 'Visited the platform' AS stage, COUNT(*) AS users FROM user_summary
    UNION ALL SELECT 2, 'Viewed a product',  SUM(ever_viewed_product) FROM user_summary
    UNION ALL SELECT 3, 'Added to cart',     SUM(ever_viewed_product * ever_added_to_cart) FROM user_summary
    UNION ALL SELECT 4, 'Began checkout',    SUM(ever_viewed_product * ever_added_to_cart * ever_began_checkout) FROM user_summary
    UNION ALL SELECT 5, 'Placed an order',   SUM(ever_viewed_product * ever_added_to_cart * ever_began_checkout * ever_ordered) FROM user_summary
), steps AS (
    SELECT stage_no, stage, users,
           LAG(users) OVER (ORDER BY stage_no)                                         AS prev_users
    FROM stages
)
SELECT stage_no, stage, users,
       ROUND(100.0 * users / prev_users, 2)                                            AS step_conversion_pct,
       prev_users - users                                                              AS users_lost,
       ROUND(100.0 * (prev_users - users) / prev_users, 2)                             AS step_dropoff_pct,
       CASE WHEN stage_no >= 2 THEN ROUND(100.0 * users / (SELECT users FROM stages WHERE stage_no = 2), 2) END AS pct_of_product_viewers,
       CASE WHEN stage_no > 2 THEN RANK() OVER (ORDER BY CASE WHEN stage_no > 2 THEN 1.0 * (prev_users - users) / prev_users END DESC) END AS dropoff_rank
FROM steps
ORDER BY stage_no;

-- @query Q07b_purchase_reconciliation
-- Reconciles the order-based purchase stage with the event stream (tracking-loss check from DQ08).
-- Finding (tested run): The event stream misses 206 of 6,896 orders (3.0%), so event-based purchase counts would understate
--          buyers (4,556 vs 4,655). Orders are therefore the system of record for purchases.
SELECT
    (SELECT COUNT(DISTINCT user_id) FROM orders)                                     AS buyers_from_orders,
    (SELECT COUNT(DISTINCT user_id) FROM events WHERE event_type = 'purchase')       AS buyers_from_purchase_events,
    (SELECT COUNT(*) FROM orders)                                                    AS orders,
    (SELECT COUNT(DISTINCT order_id) FROM events WHERE event_type = 'purchase')      AS orders_with_purchase_event,
    ROUND(100.0 * (1 - 1.0 * (SELECT COUNT(DISTINCT order_id) FROM events WHERE event_type = 'purchase')
                         / (SELECT COUNT(*) FROM orders)), 2)                        AS pct_orders_missing_from_events;

-- @query Q08_session_funnel
-- Session-level funnel (all stages within the same session). Shows how much of the drop-off is "not yet":
-- 28% of orders happen in a session without an add-to-cart, because the cart was filled earlier.
-- Finding (tested run): Within a single session, 83.7% view a product, 28.5% of those add to cart, 32.7% of carting sessions
--          begin checkout and 71.1% of those order. Only 4,962 sessions (5.5%) complete the whole journey in
--          one visit, while 6,896 (7.7%) contain an order: 28% of orders finish a journey started in an earlier
--          session.
WITH stages AS (
    SELECT 1 AS stage_no, 'All sessions' AS stage, COUNT(*) AS sessions FROM session_summary
    UNION ALL SELECT 2, 'Viewed a product', SUM(has_product_view) FROM session_summary
    UNION ALL SELECT 3, 'Added to cart',    SUM(has_product_view * has_add_to_cart) FROM session_summary
    UNION ALL SELECT 4, 'Began checkout',   SUM(has_product_view * has_add_to_cart * has_begin_checkout) FROM session_summary
    UNION ALL SELECT 5, 'Placed an order',  SUM(has_product_view * has_add_to_cart * has_begin_checkout * has_order) FROM session_summary
)
SELECT stage_no, stage, sessions,
       ROUND(100.0 * sessions / LAG(sessions) OVER (ORDER BY stage_no), 2)              AS step_conversion_pct,
       LAG(sessions) OVER (ORDER BY stage_no) - sessions                                AS sessions_lost,
       ROUND(100.0 * sessions / FIRST_VALUE(sessions) OVER (ORDER BY stage_no), 2)      AS pct_of_all_sessions,
       (SELECT SUM(has_order) FROM session_summary)                                     AS all_order_sessions
FROM stages
ORDER BY stage_no;

-- @query Q09_funnel_by_segment
-- Where does the drop-off differ? Session step rates by platform/device and by traffic source, with the
-- difference from the overall rate in percentage points. Technique: GROUPING via UNION ALL + window totals.
-- Finding (tested run): Paid social sessions add to cart far less often (18.0%, -10.5 pp) and convert at 3.6% (-4.2 pp);
--          email converts best (11.2%, +3.5 pp). Web mobile loses buyers at checkout: 62.8% of its checkouts
--          become orders vs 78.7% on web desktop.
WITH base AS (
    SELECT 'platform / device' AS dimension, platform || ' / ' || device_type AS segment,
           has_product_view AS v, has_product_view * has_add_to_cart AS c,
           has_add_to_cart * has_begin_checkout AS co, has_begin_checkout * has_order AS o, has_order AS ord
    FROM session_summary
    UNION ALL
    SELECT 'traffic source', traffic_source,
           has_product_view, has_product_view * has_add_to_cart, has_add_to_cart * has_begin_checkout,
           has_begin_checkout * has_order, has_order
    FROM session_summary
), seg AS (
    SELECT dimension, segment, COUNT(*) AS sessions, SUM(v) AS v, SUM(c) AS c, SUM(o) AS o, SUM(ord) AS ord
    FROM base GROUP BY dimension, segment
), overall AS (
    SELECT 1.0 * SUM(has_product_view * has_add_to_cart) / SUM(has_product_view) AS view_to_cart,
           1.0 * SUM(has_begin_checkout * has_order) / SUM(has_begin_checkout)   AS checkout_to_order,
           1.0 * SUM(has_order) / COUNT(*)                                       AS conversion
    FROM session_summary
), checkout AS (
    SELECT 'platform / device' AS dimension, platform || ' / ' || device_type AS segment,
           SUM(has_begin_checkout) AS checkouts, SUM(has_add_to_cart) AS carts FROM session_summary GROUP BY 1, 2
    UNION ALL
    SELECT 'traffic source', traffic_source, SUM(has_begin_checkout), SUM(has_add_to_cart) FROM session_summary GROUP BY 1, 2
)
SELECT s.dimension, s.segment, s.sessions,
       ROUND(100.0 * s.c / s.v, 2)                                       AS view_to_cart_pct,
       ROUND(100.0 * (1.0 * s.c / s.v - ov.view_to_cart), 2)             AS view_to_cart_vs_overall_pp,
       ROUND(100.0 * s.o / k.checkouts, 2)                               AS checkout_to_order_pct,
       ROUND(100.0 * (1.0 * s.o / k.checkouts - ov.checkout_to_order), 2) AS checkout_vs_overall_pp,
       ROUND(100.0 * s.ord / s.sessions, 2)                              AS session_conversion_pct,
       ROUND(100.0 * (1.0 * s.ord / s.sessions - ov.conversion), 2)      AS conversion_vs_overall_pp
FROM seg s
JOIN checkout k ON k.dimension = s.dimension AND k.segment = s.segment
CROSS JOIN overall ov
ORDER BY s.dimension, s.sessions DESC;

-- @query Q10_cart_to_order_timing
-- How long do purchase journeys take? For each order, the time since the user's most recent add-to-cart.
-- Technique: one user timeline (UNION ALL of cart and order events), then a running MAX over a frame that
-- stops one row before the order (ROWS BETWEEN UNBOUNDED PRECEDING AND 1 PRECEDING).
-- Finding (tested run): 71.9% of orders are placed in the same session as the last add-to-cart and 90.5% within 7 days. The
--          9.3% placed later than 7 days mean the 7-day abandonment window (Q12b, Q17) counts some eventual
--          purchases as abandoned.
WITH timeline AS (
    SELECT user_id, event_timestamp AS ts, session_id, 'cart' AS kind FROM events WHERE event_type = 'add_to_cart'
    UNION ALL
    SELECT user_id, order_timestamp, session_id, 'order' FROM orders
), framed AS (
    SELECT user_id, ts, session_id, kind,
           MAX(CASE WHEN kind = 'cart' THEN ts END)
               OVER (PARTITION BY user_id ORDER BY ts, kind ROWS BETWEEN UNBOUNDED PRECEDING AND 1 PRECEDING) AS last_cart_ts,
           MAX(CASE WHEN kind = 'cart' THEN ts || '|' || session_id END)
               OVER (PARTITION BY user_id ORDER BY ts, kind ROWS BETWEEN UNBOUNDED PRECEDING AND 1 PRECEDING) AS last_cart_key
    FROM timeline
), orders_timed AS (
    SELECT CASE WHEN last_cart_ts IS NULL THEN '6 No earlier add-to-cart'
                WHEN substr(last_cart_key, instr(last_cart_key, '|') + 1) = session_id THEN '1 Same session'
                WHEN (julianday(ts) - julianday(last_cart_ts)) * 24 < 24  THEN '2 Earlier session, < 1 day'
                WHEN (julianday(ts) - julianday(last_cart_ts)) * 24 < 72  THEN '3 1-3 days'
                WHEN (julianday(ts) - julianday(last_cart_ts)) * 24 < 168 THEN '4 3-7 days'
                ELSE '5 More than 7 days' END AS bucket
    FROM framed
    WHERE kind = 'order'
), counted AS (
    SELECT bucket, COUNT(*) AS orders FROM orders_timed GROUP BY bucket
)
SELECT bucket                                                             AS time_from_last_add_to_order,
       orders,
       ROUND(100.0 * orders / SUM(orders) OVER (), 1)                     AS pct_orders,
       ROUND(100.0 * SUM(orders) OVER (ORDER BY bucket ROWS UNBOUNDED PRECEDING) / SUM(orders) OVER (), 1) AS cumulative_pct
FROM counted
ORDER BY bucket;

-- @query Q11_after_add_to_cart
-- What do users do immediately after adding to cart? Next event in the same session (LEAD).
-- Finding (tested run): After adding to cart, 38.6% of users next view another product and 17.0% search: the cart is often
--          used as a shortlist. Only 6.6% go straight to checkout, and 11.5% end the session.
WITH seq AS (
    SELECT event_type,
           LEAD(event_type) OVER (PARTITION BY session_id ORDER BY session_event_seq) AS next_event
    FROM events_enriched
)
SELECT COALESCE(next_event, '(session ended)')                    AS next_event_after_add_to_cart,
       COUNT(*)                                                    AS add_to_cart_events,
       ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 2)          AS pct
FROM seq
WHERE event_type = 'add_to_cart'
GROUP BY 1
ORDER BY 2 DESC;

-- @query Q12_checkout_abandonment
-- Of sessions that reach checkout, how many end without an order, and does it differ by platform and device?
-- Finding (tested run): 29.7% of checkout sessions end without an order. Web mobile has the most abandoned checkouts (1,154)
--          and the highest rate (37.2%), against 21.3% on web desktop.
SELECT platform, device_type,
       SUM(has_begin_checkout)                                                        AS checkout_sessions,
       SUM(has_begin_checkout * (1 - has_order))                                      AS abandoned_checkouts,
       ROUND(100.0 * SUM(has_begin_checkout * (1 - has_order)) / SUM(has_begin_checkout), 2) AS checkout_abandonment_pct,
       RANK() OVER (ORDER BY 1.0 * SUM(has_begin_checkout * (1 - has_order)) / SUM(has_begin_checkout) DESC) AS abandonment_rank
FROM session_summary
GROUP BY platform, device_type
UNION ALL
SELECT 'ALL', 'ALL', SUM(has_begin_checkout), SUM(has_begin_checkout * (1 - has_order)),
       ROUND(100.0 * SUM(has_begin_checkout * (1 - has_order)) / SUM(has_begin_checkout), 2), NULL
FROM session_summary
ORDER BY checkout_sessions DESC;

-- @query Q12b_cart_abandonment_overall
-- Cart abandonment at the level of individual cart additions (traceable products, 7-day outcome window).
-- Finding (tested run): 67.9% of the 28,001 cart additions with a full 7-day outcome were not bought within 7 days. 23.1%
--          were bought in the same session and 12.7% were removed in the same session.
SELECT COUNT(*)                                                               AS cart_additions,
       SUM(is_censored)                                                       AS censored_last_7_days,
       SUM(1 - is_censored)                                                   AS additions_with_outcome,
       ROUND(100.0 * SUM(CASE WHEN is_censored = 0 THEN purchased_same_session END) / SUM(1 - is_censored), 2) AS pct_bought_same_session,
       ROUND(100.0 * SUM(CASE WHEN is_censored = 0 THEN purchased_within_7d END) / SUM(1 - is_censored), 2)    AS pct_bought_within_7_days,
       ROUND(100.0 * SUM(CASE WHEN is_censored = 0 AND purchased_within_7d = 0 THEN 1 ELSE 0 END) / SUM(1 - is_censored), 2) AS cart_abandonment_pct,
       ROUND(100.0 * SUM(CASE WHEN is_censored = 0 THEN removed_in_session END) / SUM(1 - is_censored), 2)     AS pct_removed_in_session
FROM cart_add_outcomes;


/* -----------------------------------------------------------------------------------------------------
   5C. PRODUCT AND CATEGORY PERFORMANCE  (Objective 4)
   ----------------------------------------------------------------------------------------------------- */

-- @query Q13_popularity_vs_purchases
-- Do popular products necessarily generate the most purchases? Spearman rank correlation between views and
-- units sold (and between views and conversion) across all 250 products, computed in SQL.
-- Technique: average ranks for ties = RANK() + (count of ties - 1) / 2; Pearson correlation of the ranks.
-- Finding (tested run): Popularity and sales are moderately related (Spearman rho: views vs units 0.52, views vs net revenue
--          0.60), but views and conversion are weakly negative (-0.18). Popular products sell more in absolute
--          terms without converting better.
WITH r AS (
    SELECT product_id,
           RANK() OVER (ORDER BY views) + (COUNT(*) OVER (PARTITION BY views) - 1) / 2.0                    AS r_views,
           RANK() OVER (ORDER BY units) + (COUNT(*) OVER (PARTITION BY units) - 1) / 2.0                    AS r_units,
           RANK() OVER (ORDER BY net_revenue) + (COUNT(*) OVER (PARTITION BY net_revenue) - 1) / 2.0        AS r_revenue,
           RANK() OVER (ORDER BY view_to_purchase_rate) + (COUNT(*) OVER (PARTITION BY view_to_purchase_rate) - 1) / 2.0 AS r_conv
    FROM product_performance
), pairs AS (
    SELECT 'views vs units sold' AS pair, r_views AS x, r_units AS y FROM r
    UNION ALL SELECT 'views vs net revenue', r_views, r_revenue FROM r
    UNION ALL SELECT 'views vs view-to-purchase rate', r_views, r_conv FROM r
)
SELECT pair, COUNT(*) AS products,
       ROUND((COUNT(*) * SUM(x * y) - SUM(x) * SUM(y))
             / sqrt((COUNT(*) * SUM(x * x) - SUM(x) * SUM(x)) * (COUNT(*) * SUM(y * y) - SUM(y) * SUM(y))), 3) AS spearman_rho
FROM pairs
GROUP BY pair;

-- @query Q13b_top_viewed_vs_top_sellers
-- The overlap between the 20 most viewed and the 20 best-selling products (by units).
-- Finding (tested run): Only 8 of the 20 most-viewed products are among the 20 best sellers by units; the top-20 viewed take
--          35.2% of views but 31.3% of units.
WITH top_viewed AS (SELECT product_id FROM product_performance WHERE view_rank <= 20),
     top_sold   AS (SELECT product_id FROM product_performance WHERE units_rank <= 20)
SELECT (SELECT COUNT(*) FROM top_viewed)                                                     AS top_viewed,
       (SELECT COUNT(*) FROM top_sold)                                                       AS top_sold,
       (SELECT COUNT(*) FROM top_viewed WHERE product_id IN (SELECT product_id FROM top_sold)) AS in_both,
       (SELECT ROUND(100.0 * SUM(units) / (SELECT SUM(units) FROM product_performance), 1)
          FROM product_performance WHERE view_rank <= 20)                                    AS pct_units_from_top_viewed,
       (SELECT ROUND(100.0 * SUM(views) / (SELECT SUM(views) FROM product_performance), 1)
          FROM product_performance WHERE view_rank <= 20)                                    AS pct_views_on_top_viewed;

-- @query Q14_top_conversion_products
-- Which products have the highest view-to-purchase conversion? Products with at least 500 viewers, ranked by
-- the 95% Wilson lower bound so that a high rate on a small sample does not outrank a reliable one.
-- Finding (tested run): Everyday consumables convert best: Daily Basket Instant Noodles (17.5% of viewers bought; Wilson
--          lower bound 14.6%) and Naturelle Vitamin C Serum (13.9% of 4,229 viewers). Several high converters,
--          such as Playmore Baby Wipes F67 (view rank 113), get little traffic.
SELECT RANK() OVER (ORDER BY vtp_wilson_lower DESC)        AS conversion_rank,
       product_id, product_name, category_name, list_price, viewers, viewer_buyers,
       ROUND(100.0 * view_to_purchase_rate, 2)             AS view_to_purchase_pct,
       ROUND(100.0 * vtp_wilson_lower, 2)                  AS wilson_lower_pct,
       view_rank, units_rank
FROM product_performance
WHERE viewers >= 500
ORDER BY vtp_wilson_lower DESC
LIMIT 15;

-- @query Q15_high_interest_low_conversion
-- Opportunity list: products in the top quartile for views but the bottom quartile for conversion (NTILE).
-- Benchmark = the pooled product-level rate of the product's category (viewer-buyers / viewers summed over the
-- category's products, a windowed SUM). The category-level user rate in category_performance is not used here:
-- it counts a viewer of any product who bought any product in the category, so it is not like-for-like.
-- "Buyers gap" = additional buyers if the product converted at that benchmark. It sizes the gap; it is not a forecast.
-- Finding (tested run): 19 products sit in the top view quartile and the bottom conversion quartile. The largest gap is
--          Stride Chinos F33: 9,337 views, 2.5% conversion against 4.1% for Fashion, and 86.6% cart
--          abandonment. Converting the 19 at their category rate would add about 656 product purchases (buyer-
--          product pairs). This sizes the gap; it is not a forecast.
WITH q AS (
    SELECT pp.*,
           NTILE(4) OVER (ORDER BY pp.views DESC)                 AS view_quartile,          -- 1 = most viewed
           NTILE(4) OVER (ORDER BY pp.view_to_purchase_rate)      AS conversion_quartile,    -- 1 = lowest conversion
           1.0 * SUM(pp.viewer_buyers) OVER (PARTITION BY pp.category_name)
               / SUM(pp.viewers)       OVER (PARTITION BY pp.category_name) AS category_rate
    FROM product_performance pp
)
SELECT product_id, product_name, category_name, list_price, views, viewers,
       ROUND(100.0 * view_to_purchase_rate, 2)                                AS view_to_purchase_pct,
       ROUND(100.0 * category_rate, 2)                                        AS category_rate_pct,
       ROUND(100.0 * cart_abandonment_rate, 1)                                AS cart_abandonment_pct,
       CAST(ROUND(MAX(0, viewers * (category_rate - view_to_purchase_rate))) AS INTEGER) AS buyers_gap_vs_category
FROM q
WHERE view_quartile = 1 AND conversion_quartile = 1
ORDER BY buyers_gap_vs_category DESC;

-- @query Q16_category_performance
-- Which categories have the highest purchase activity? Orders, buyers, units and net revenue with ranks.
-- Finding (tested run): Health & Beauty (1,699 orders) and Groceries (1,505) have the most purchase activity and the highest
--          viewer conversion (15.5%, 15.9%). Phones & Tablets and Computing lead net revenue (35.4%, 33.8%) on
--          few units. Computing revenue is inflated by implausible list prices (DQ18), so the revenue ranking
--          is indicative only.
SELECT DENSE_RANK() OVER (ORDER BY orders DESC)            AS orders_rank,
       category_name, department, products, views, viewers, buyers, orders, units, net_revenue,
       ROUND(1.0 * net_revenue / NULLIF(units, 0), 0)      AS net_revenue_per_unit,
       ROUND(100.0 * view_to_cart_rate, 2)                 AS view_to_cart_pct,
       ROUND(100.0 * view_to_purchase_rate, 2)             AS view_to_purchase_pct,
       ROUND(100.0 * share_of_views, 1)                    AS pct_of_views,
       ROUND(100.0 * share_of_orders, 1)                   AS pct_of_orders,
       ROUND(100.0 * share_of_net_revenue, 1)              AS pct_of_net_revenue,
       DENSE_RANK() OVER (ORDER BY net_revenue DESC)       AS revenue_rank
FROM category_performance
ORDER BY orders DESC;

-- @query Q17_cart_abandonment_products
-- Which products experience relatively high cart abandonment? Products with at least 100 cart additions that
-- have a 7-day outcome, compared with the abandonment rate of their category (window over the category).
-- Finding (tested run): Among products with 100+ observed cart additions, the highest abandonment is Lekki Thread Kaftan Set
--          (93.4% vs 73.3% for Fashion). In volume terms, Stride Chinos F33 (86.6% of 881 additions) and
--          Kitchenix Air Fryer U17 (87.4% of 428) lose the most carts.
WITH cat AS (
    SELECT category_name,
           1.0 * SUM(cart_adds_abandoned) / SUM(cart_adds_observed) AS category_abandonment
    FROM product_performance GROUP BY category_name
), overall AS (
    SELECT 1.0 * SUM(cart_adds_abandoned) / SUM(cart_adds_observed) AS overall_abandonment FROM product_performance
)
SELECT RANK() OVER (ORDER BY pp.cart_abandonment_rate DESC)                   AS abandonment_rank,
       pp.product_id, pp.product_name, pp.category_name, pp.list_price,
       pp.cart_adds_observed, pp.cart_adds_abandoned,
       ROUND(100.0 * pp.cart_abandonment_rate, 1)                             AS abandonment_pct,
       ROUND(100.0 * c.category_abandonment, 1)                               AS category_abandonment_pct,
       ROUND(100.0 * (pp.cart_abandonment_rate - c.category_abandonment), 1)  AS vs_category_pp,
       ROUND(100.0 * (pp.cart_abandonment_rate - o.overall_abandonment), 1)   AS vs_overall_pp
FROM product_performance pp
JOIN cat c ON c.category_name = pp.category_name
CROSS JOIN overall o
WHERE pp.cart_adds_observed >= 100
ORDER BY pp.cart_abandonment_rate DESC
LIMIT 15;

-- @query Q17b_abandonment_by_category_and_price
-- Is abandonment linked to price? Cart abandonment by category and by list-price band (NTILE price quintiles).
-- Finding (tested run): Abandonment is highest in Home & Kitchen (74.5%) and Fashion (73.3%) and lowest in Health & Beauty
--          (62.9%) and Groceries (63.9%). By price it rises from 64.7% (cheapest quintile) to 73.1% (fourth
--          quintile) and dips to 66.9% in the most expensive, so it is not a simple price effect.
WITH priced AS (
    SELECT c.*, p.list_price, cat.category_name,
           NTILE(5) OVER (ORDER BY p.list_price) AS price_quintile
    FROM cart_add_outcomes c
    JOIN products p     ON p.product_id = c.product_id
    JOIN categories cat ON cat.category_id = p.category_id
    WHERE c.is_censored = 0
)
SELECT 'price quintile' AS dimension,
       'Q' || price_quintile || ' (' || MIN(list_price) || '-' || MAX(list_price) || ')' AS segment,
       COUNT(*) AS cart_additions,
       ROUND(100.0 * AVG(1 - purchased_within_7d), 1) AS abandonment_pct
FROM priced GROUP BY price_quintile
UNION ALL
SELECT 'category', category_name, COUNT(*), ROUND(100.0 * AVG(1 - purchased_within_7d), 1)
FROM priced GROUP BY category_name
ORDER BY dimension DESC, abandonment_pct DESC;

-- @query Q18_promotion_periods
-- How do sessions behave during promotion periods? Descriptive comparison of promotion days with other days
-- (not a causal estimate: promotion timing coincides with seasonal demand).
-- Finding (tested run): Black Friday days averaged 864 sessions a day (450 with no promotion) and 9.4% session conversion
--          (7.4%), with a lower average net order value (78,570 vs 82,554). Other promotions changed conversion
--          by under 1 pp.
SELECT COALESCE(c.promotion_name, 'No promotion')                             AS period,
       COUNT(DISTINCT ss.session_date)                                        AS days,
       COUNT(*)                                                               AS sessions,
       ROUND(1.0 * COUNT(*) / COUNT(DISTINCT ss.session_date), 0)             AS sessions_per_day,
       ROUND(100.0 * SUM(ss.has_product_view * ss.has_add_to_cart) / SUM(ss.has_product_view), 2) AS view_to_cart_pct,
       ROUND(100.0 * SUM(ss.has_order) / COUNT(*), 2)                         AS session_conversion_pct,
       ROUND(1.0 * SUM(CASE WHEN ss.is_net_order = 1 THEN ss.order_items_subtotal END) / NULLIF(SUM(ss.is_net_order), 0), 0) AS avg_net_order_value
FROM session_summary ss
JOIN calendar c ON c.date = ss.session_date
GROUP BY 1
ORDER BY MIN(ss.session_date);


/* -----------------------------------------------------------------------------------------------------
   5D. RETURNING USERS AND RETENTION  (Objective 5)
   ----------------------------------------------------------------------------------------------------- */

-- @query Q19_returning_users
-- How many users returned after their first observed interaction? Return within 7/14/28 days uses only
-- users with enough follow-up (right-censoring); the denominators therefore differ.
-- Finding (tested run): 42.2% of users came back on a later day after their first observed session (median 4 days). Among
--          users with enough follow-up, 31.4% returned within 7 days, 39.4% within 14 and 43.2% within 28.
WITH d AS (
    SELECT returned_later_day, returned_within_7d, returned_within_14d, returned_within_28d, days_to_return,
           -- NULLs sort first in SQLite, so rank returners separately from non-returners
           ROW_NUMBER() OVER (PARTITION BY days_to_return IS NULL ORDER BY days_to_return) AS rn,
           COUNT(days_to_return) OVER ()             AS n_ret
    FROM user_summary
)
SELECT COUNT(*)                                                         AS users,
       SUM(returned_later_day)                                          AS returned_on_a_later_day,
       ROUND(100.0 * AVG(returned_later_day), 2)                        AS pct_returned_any_time,
       COUNT(returned_within_7d)                                        AS eligible_7d,
       ROUND(100.0 * AVG(returned_within_7d), 2)                        AS pct_returned_within_7d,
       COUNT(returned_within_14d)                                       AS eligible_14d,
       ROUND(100.0 * AVG(returned_within_14d), 2)                       AS pct_returned_within_14d,
       COUNT(returned_within_28d)                                       AS eligible_28d,
       ROUND(100.0 * AVG(returned_within_28d), 2)                       AS pct_returned_within_28d,
       MAX(CASE WHEN days_to_return IS NOT NULL AND rn = (n_ret + 1) / 2 THEN days_to_return END) AS median_days_to_return
FROM d;

-- @query Q20_cohort_retention_matrix
-- How does activity change across weekly cohorts? Share of each first-seen weekly cohort active in each later
-- week (pivot by conditional aggregation; blank = week not yet observed).
-- Finding (tested run): Week-1 retention is 38.0% for the first cohort, which is inflated by existing customers. From cohort
--          4 to cohort 19 it is steady at about 24-29%. Week-4 retention is 9-13% for the August-October
--          cohorts and 4.9-6.9% for the cohorts from mid-November to early December.
SELECT cohort_week, cohort_start, MAX(cohort_users) AS cohort_users,
       MAX(CASE WHEN week_offset = 1  THEN ROUND(100 * retention_rate, 1) END) AS w1,
       MAX(CASE WHEN week_offset = 2  THEN ROUND(100 * retention_rate, 1) END) AS w2,
       MAX(CASE WHEN week_offset = 3  THEN ROUND(100 * retention_rate, 1) END) AS w3,
       MAX(CASE WHEN week_offset = 4  THEN ROUND(100 * retention_rate, 1) END) AS w4,
       MAX(CASE WHEN week_offset = 6  THEN ROUND(100 * retention_rate, 1) END) AS w6,
       MAX(CASE WHEN week_offset = 8  THEN ROUND(100 * retention_rate, 1) END) AS w8,
       MAX(CASE WHEN week_offset = 12 THEN ROUND(100 * retention_rate, 1) END) AS w12,
       MAX(CASE WHEN week_offset = 16 THEN ROUND(100 * retention_rate, 1) END) AS w16
FROM cohort_retention
GROUP BY cohort_week, cohort_start
ORDER BY cohort_week;

-- @query Q21_retention_week_1_2_4
-- What proportion of users return after one, two or four weeks? Week-N retention = active in calendar week
-- (cohort week + N), pooled over every cohort observed for N weeks (weighted by cohort size).
-- Shown for all users and excluding cohort weeks 1-2, which mix new users with existing customers first seen
-- when the data begins (left-censoring), and for users with no signup before the window.
-- Finding (tested run): Across all users, 26.5% were active in the week after their first week, 19.3% two weeks after and
--          11.0% four weeks after. For users not registered before the window (the cleanest view of new users)
--          the figures are 20.0%, 13.8% and 6.8%.
WITH base AS (
    SELECT cr.week_offset, cr.cohort_week, cr.cohort_users, cr.active_users
    FROM cohort_retention cr WHERE cr.week_offset IN (1, 2, 4)
), new_only AS (            -- recompute for users who were not registered before the window began
    SELECT us.cohort_week, w.week_index - us.cohort_week AS week_offset, COUNT(*) AS active_users
    FROM user_week_activity w JOIN user_summary us ON us.user_id = w.user_id
    WHERE us.is_known_existing_customer = 0
    GROUP BY 1, 2
), new_sizes AS (
    SELECT cohort_week, COUNT(*) AS cohort_users FROM user_summary WHERE is_known_existing_customer = 0 GROUP BY 1
)
SELECT 'All users' AS population, week_offset, COUNT(*) AS cohorts, SUM(cohort_users) AS users,
       ROUND(100.0 * SUM(active_users) / SUM(cohort_users), 2) AS retention_pct
FROM base GROUP BY week_offset
UNION ALL
SELECT 'Cohort weeks 3-26 only', week_offset, COUNT(*), SUM(cohort_users), ROUND(100.0 * SUM(active_users) / SUM(cohort_users), 2)
FROM base WHERE cohort_week >= 3 GROUP BY week_offset
UNION ALL
SELECT 'Users not registered before the window', o.week_offset, COUNT(*), SUM(s.cohort_users),
       ROUND(100.0 * SUM(COALESCE(n.active_users, 0)) / SUM(s.cohort_users), 2)
FROM (SELECT 1 AS week_offset UNION ALL SELECT 2 UNION ALL SELECT 4) o
JOIN new_sizes s ON s.cohort_week + o.week_offset <= 26
LEFT JOIN new_only n ON n.cohort_week = s.cohort_week AND n.week_offset = o.week_offset
GROUP BY o.week_offset
ORDER BY 1, 2;

-- @query Q22_cohort_quality_trend
-- Are later cohorts as engaged as earlier ones? Per cohort: size, week-1 and week-4 retention, orders per user
-- in the first 4 weeks, and the change from the previous cohort (LAG). Promotion-heavy cohorts are flagged.
-- Finding (tested run): The Black Friday cohorts were the largest (1,395 and 2,166 users) but retained worse: week 1 was
--          25.9% and 21.5%, and week 4 was 4.9% and 5.3%. This fits deal-driven acquisition, but their week 4
--          falls in the late-December slowdown, so the two effects cannot be separated here.
WITH first4 AS (
    SELECT us.cohort_week, COUNT(DISTINCT us.user_id) AS users,
           SUM(CASE WHEN w.week_index - us.cohort_week BETWEEN 0 AND 3 THEN w.orders ELSE 0 END) AS orders_first_4w
    FROM user_summary us
    LEFT JOIN user_week_activity w ON w.user_id = us.user_id
    GROUP BY us.cohort_week
), promo AS (
    SELECT week_index, SUM(promotion_name IS NOT NULL) AS promo_days FROM calendar GROUP BY week_index
)
SELECT cr.cohort_week, cr.cohort_start, cr.cohort_users, p.promo_days,
       MAX(CASE WHEN cr.week_offset = 1 THEN ROUND(100 * cr.retention_rate, 1) END)             AS w1_retention_pct,
       MAX(CASE WHEN cr.week_offset = 4 THEN ROUND(100 * cr.retention_rate, 1) END)             AS w4_retention_pct,
       CASE WHEN cr.cohort_week <= 23 THEN ROUND(1.0 * f.orders_first_4w / f.users, 3) END      AS orders_per_user_first_4w,
       ROUND(MAX(CASE WHEN cr.week_offset = 1 THEN 100 * cr.retention_rate END)
             - LAG(MAX(CASE WHEN cr.week_offset = 1 THEN 100 * cr.retention_rate END)) OVER (ORDER BY cr.cohort_week), 1) AS w1_change_vs_prev_pp
FROM cohort_retention cr
JOIN first4 f ON f.cohort_week = cr.cohort_week
JOIN promo p  ON p.week_index = cr.cohort_week
GROUP BY cr.cohort_week, cr.cohort_start, cr.cohort_users, p.promo_days, f.orders_first_4w, f.users
ORDER BY cr.cohort_week;

-- @query Q23_segment_repeat_engagement
-- Which user groups show stronger repeat engagement? For each grouping: users, 28-day return rate (users with
-- 28 days of follow-up), average active weeks and the repeat-purchase rate among buyers, against the overall
-- figure and ranked within the grouping.
-- Caution: registration and loyalty status are recorded at the extract date, after the behaviour measured,
-- so engaged users becoming members inflates these gaps (reverse causation). Acquisition channel, city,
-- device and first-session attributes are fixed before the behaviour and are the safer comparisons.
-- Finding (tested run): Email (71.7%) and direct (61.8%) acquisition have the highest 28-day return; paid social has the
--          lowest (25.0%, -18.2 pp). Loyalty members (88.5%) and registered users (74.2%) return far more, but
--          both statuses are measured at extract date, so these are associations that may run in reverse. City
--          and device differ by no more than 2.3 pp.
WITH long_form AS (
    SELECT 'acquisition channel' AS dimension, acquisition_channel AS segment, * FROM user_summary
    UNION ALL SELECT 'primary device', primary_device, * FROM user_summary
    UNION ALL SELECT 'registration', CASE WHEN is_registered = 1 THEN 'registered' ELSE 'guest' END, * FROM user_summary
    UNION ALL SELECT 'loyalty member', CASE WHEN is_loyalty_member = 1 THEN 'member' ELSE 'not a member' END, * FROM user_summary
    UNION ALL SELECT 'city', city, * FROM user_summary
    UNION ALL SELECT 'first-session platform', first_session_platform, * FROM user_summary
    UNION ALL SELECT 'first-session outcome',
              CASE first_session_stage_rank WHEN 4 THEN 'ordered' WHEN 3 THEN 'reached checkout' WHEN 2 THEN 'added to cart'
                                            WHEN 1 THEN 'viewed a product' ELSE 'browsed only' END, * FROM user_summary
), seg AS (
    SELECT dimension, segment, COUNT(*) AS users,
           COUNT(returned_within_28d)                                     AS eligible_28d,
           100.0 * AVG(returned_within_28d)                               AS return_28d_pct,
           AVG(n_active_weeks)                                            AS avg_active_weeks,
           SUM(ever_ordered)                                              AS buyers,
           100.0 * SUM(is_repeat_buyer) / NULLIF(SUM(ever_ordered), 0)    AS repeat_buyer_pct
    FROM long_form GROUP BY dimension, segment
), overall AS (
    SELECT 100.0 * AVG(returned_within_28d) AS return_28d_pct FROM user_summary
)
SELECT s.dimension, s.segment, s.users, s.eligible_28d,
       ROUND(s.return_28d_pct, 1)                                         AS return_28d_pct,
       ROUND(s.return_28d_pct - o.return_28d_pct, 1)                      AS vs_overall_pp,
       ROUND(s.avg_active_weeks, 2)                                       AS avg_active_weeks,
       s.buyers,
       ROUND(s.repeat_buyer_pct, 1)                                       AS repeat_buyer_pct,
       RANK() OVER (PARTITION BY s.dimension ORDER BY s.return_28d_pct DESC) AS rank_in_dimension
FROM seg s CROSS JOIN overall o
ORDER BY s.dimension, rank_in_dimension;

-- @query Q24_repeat_purchase
-- Repeat buying: buyers with 2+ orders and the time between consecutive orders (LAG over each buyer's orders).
-- Finding (tested run): 28.4% of buyers (1,324) ordered more than once and placed 51.7% of all orders; the median gap
--          between orders is 10.1 days.
WITH o AS (
    SELECT user_id, order_timestamp,
           julianday(order_timestamp) - julianday(LAG(order_timestamp) OVER (PARTITION BY user_id ORDER BY order_timestamp)) AS days_since_prev_order
    FROM orders
), gaps AS (
    SELECT days_since_prev_order AS g, ROW_NUMBER() OVER (ORDER BY days_since_prev_order) AS rn, COUNT(*) OVER () AS n
    FROM o WHERE days_since_prev_order IS NOT NULL
)
SELECT (SELECT COUNT(*) FROM user_summary WHERE ever_ordered = 1)                         AS buyers,
       (SELECT COUNT(*) FROM user_summary WHERE is_repeat_buyer = 1)                      AS repeat_buyers,
       (SELECT ROUND(100.0 * AVG(is_repeat_buyer), 1) FROM user_summary WHERE ever_ordered = 1) AS pct_repeat_buyers,
       (SELECT ROUND(AVG(n_orders), 2) FROM user_summary WHERE ever_ordered = 1)          AS orders_per_buyer,
       (SELECT ROUND(100.0 * SUM(n_orders) FILTER (WHERE is_repeat_buyer = 1) / SUM(n_orders), 1) FROM user_summary) AS pct_orders_from_repeat_buyers,
       (SELECT ROUND(AVG(g), 1) FROM gaps)                                                AS mean_days_between_orders,
       (SELECT ROUND(MAX(CASE WHEN rn = (n + 1) / 2 THEN g END), 1) FROM gaps)            AS median_days_between_orders;


/* -----------------------------------------------------------------------------------------------------
   5E. OPPORTUNITIES  (Objective 6)
   One table that sizes each opportunity from the results above, so the Product Manager can compare them.
   ----------------------------------------------------------------------------------------------------- */

-- @query Q25_opportunity_summary
-- Finding (tested run): The two largest leaks are at the top of the funnel: 15,240 viewers never add to cart, and 5,686 cart
--          users never reach checkout. See Section 5F of the report for the actions.
WITH uf AS (
    SELECT SUM(ever_viewed_product)                                                      AS viewers,
           SUM(ever_viewed_product * ever_added_to_cart)                                 AS carters,
           SUM(ever_viewed_product * ever_added_to_cart * ever_began_checkout)           AS checkouts,
           SUM(ever_viewed_product * ever_added_to_cart * ever_began_checkout * ever_ordered) AS buyers
    FROM user_summary
), co AS (
    SELECT SUM(has_begin_checkout) AS checkout_sessions, SUM(has_begin_checkout * (1 - has_order)) AS abandoned
    FROM session_summary
), hilo AS (
    SELECT COUNT(*) AS products, SUM(viewers) AS viewers
    FROM (SELECT viewers, NTILE(4) OVER (ORDER BY views DESC) AS vq, NTILE(4) OVER (ORDER BY view_to_purchase_rate) AS cq
          FROM product_performance) WHERE vq = 1 AND cq = 1
), ab AS (
    SELECT SUM(1 - is_censored) AS observed, SUM(CASE WHEN is_censored = 0 AND purchased_within_7d = 0 THEN 1 ELSE 0 END) AS abandoned
    FROM cart_add_outcomes
), one AS (
    SELECT COUNT(*) AS users, SUM(n_sessions = 1) AS one_session FROM user_summary
)
SELECT 1 AS priority_order, 'Viewers who never add to cart' AS opportunity, 'user funnel' AS evidence,
       uf.viewers - uf.carters AS users_or_events, ROUND(100.0 * (uf.viewers - uf.carters) / uf.viewers, 1) AS pct, 'of product viewers' AS base
FROM uf
UNION ALL SELECT 2, 'Cart users who never reach checkout', 'user funnel', uf.carters - uf.checkouts,
       ROUND(100.0 * (uf.carters - uf.checkouts) / uf.carters, 1), 'of cart users' FROM uf
UNION ALL SELECT 3, 'Checkout sessions that end without an order', 'session funnel', co.abandoned,
       ROUND(100.0 * co.abandoned / co.checkout_sessions, 1), 'of checkout sessions' FROM co
UNION ALL SELECT 4, 'Cart additions not bought within 7 days', 'cart outcomes', ab.abandoned,
       ROUND(100.0 * ab.abandoned / ab.observed, 1), 'of cart additions with an outcome' FROM ab
UNION ALL SELECT 5, 'High-traffic, low-converting products', 'product quartiles', hilo.products,
       ROUND(100.0 * hilo.products / 250, 1), 'of the catalogue (top view quartile, bottom conversion quartile)' FROM hilo
UNION ALL SELECT 6, 'Users seen in only one session', 'return frequency', one.one_session,
       ROUND(100.0 * one.one_session / one.users, 1), 'of all users' FROM one
ORDER BY priority_order;


/* =====================================================================================================
   SECTION 6. VIEWS AND REUSABLE OUTPUTS
   Views give the Product Manager's team stable, documented definitions to query or connect a BI tool to.
   ===================================================================================================== */

-- @exec 6.1 daily and weekly KPI views (moving averages, running totals, period-over-period change)
CREATE VIEW vw_daily_kpis AS
WITH daily AS (
    SELECT ss.session_date                                        AS date,
           c.day_name, c.is_weekend, c.week_index, c.promotion_name,
           COUNT(DISTINCT ss.user_id)                             AS active_users,
           COUNT(*)                                               AS sessions,
           SUM(ss.n_product_views)                                AS product_views,
           SUM(ss.has_add_to_cart)                                AS cart_sessions,
           SUM(ss.has_order)                                      AS orders,
           SUM(CASE WHEN ss.is_net_order = 1 THEN ss.order_items_subtotal ELSE 0 END) AS net_revenue
    FROM session_summary ss
    JOIN calendar c ON c.date = ss.session_date
    GROUP BY ss.session_date
)
SELECT date, day_name, is_weekend, week_index, promotion_name, active_users, sessions, product_views,
       cart_sessions, orders, net_revenue,
       ROUND(100.0 * orders / sessions, 2)                                                      AS session_conversion_pct,
       ROUND(AVG(active_users) OVER w7, 1)                                                      AS dau_7d_moving_avg,
       ROUND(100.0 * SUM(orders) OVER w7 / SUM(sessions) OVER w7, 2)                            AS conversion_7d_pct,
       SUM(orders)      OVER (ORDER BY date ROWS UNBOUNDED PRECEDING)                           AS running_orders,
       SUM(net_revenue) OVER (ORDER BY date ROWS UNBOUNDED PRECEDING)                           AS running_net_revenue,
       ROUND(100.0 * (active_users - LAG(active_users, 7) OVER (ORDER BY date))
             / LAG(active_users, 7) OVER (ORDER BY date), 1)                                    AS dau_vs_same_day_last_week_pct
FROM daily
WINDOW w7 AS (ORDER BY date ROWS BETWEEN 6 PRECEDING AND CURRENT ROW);

CREATE VIEW vw_weekly_kpis AS
WITH weekly AS (
    SELECT ss.week_index,
           MIN(c.week_start_date)                                                     AS week_start,
           COUNT(DISTINCT ss.user_id)                                                 AS active_users,
           COUNT(DISTINCT CASE WHEN us.cohort_week = ss.week_index THEN ss.user_id END) AS new_users,
           COUNT(*)                                                                   AS sessions,
           SUM(ss.has_order)                                                          AS orders,
           SUM(CASE WHEN ss.is_net_order = 1 THEN ss.order_items_subtotal ELSE 0 END) AS net_revenue
    FROM session_summary ss
    JOIN user_summary us ON us.user_id = ss.user_id
    JOIN calendar c      ON c.date = ss.session_date
    GROUP BY ss.week_index
)
SELECT week_index, week_start, active_users, new_users, active_users - new_users AS returning_users,
       sessions, orders, net_revenue,
       ROUND(100.0 * orders / sessions, 2)                                                       AS session_conversion_pct,
       ROUND(100.0 * (active_users - LAG(active_users) OVER w) / LAG(active_users) OVER w, 1)    AS wau_wow_pct,
       ROUND(100.0 * (orders - LAG(orders) OVER w) / LAG(orders) OVER w, 1)                      AS orders_wow_pct,
       ROUND(AVG(active_users) OVER (ORDER BY week_index ROWS BETWEEN 3 PRECEDING AND CURRENT ROW), 0) AS wau_4wk_moving_avg
FROM weekly
WINDOW w AS (ORDER BY week_index);

-- @exec 6.2 funnel views
CREATE VIEW vw_user_funnel AS
SELECT 1 AS stage_no, 'Visited the platform' AS stage, COUNT(*) AS users FROM user_summary
UNION ALL SELECT 2, 'Viewed a product', SUM(ever_viewed_product) FROM user_summary
UNION ALL SELECT 3, 'Added to cart',    SUM(ever_viewed_product * ever_added_to_cart) FROM user_summary
UNION ALL SELECT 4, 'Began checkout',   SUM(ever_viewed_product * ever_added_to_cart * ever_began_checkout) FROM user_summary
UNION ALL SELECT 5, 'Placed an order',  SUM(ever_viewed_product * ever_added_to_cart * ever_began_checkout * ever_ordered) FROM user_summary;

-- One row per segment combination with the counts needed to rebuild any funnel rate in a BI tool.
CREATE VIEW vw_session_funnel_by_segment AS
SELECT platform, device_type, traffic_source, promo_period, is_first_session,
       COUNT(*)                                             AS sessions,
       SUM(has_product_view)                                AS viewed_product,
       SUM(has_product_view * has_add_to_cart)              AS viewed_and_carted,
       SUM(has_begin_checkout)                              AS began_checkout,
       SUM(has_begin_checkout * has_order)                  AS checkout_and_ordered,
       SUM(has_order)                                       AS ordered,
       SUM(is_net_order)                                    AS net_orders
FROM session_summary
GROUP BY platform, device_type, traffic_source, promo_period, is_first_session;

-- @exec 6.3 product and category scorecards
-- Each product is placed in a popularity / conversion quadrant using the catalogue medians
-- (medians computed with ROW_NUMBER because SQLite has no MEDIAN function).
CREATE VIEW vw_product_scorecard AS
WITH ordered_views AS (
    SELECT views, ROW_NUMBER() OVER (ORDER BY views) AS rn, COUNT(*) OVER () AS n FROM product_performance
), ordered_conv AS (
    SELECT view_to_purchase_rate AS r, ROW_NUMBER() OVER (ORDER BY view_to_purchase_rate) AS rn, COUNT(*) OVER () AS n
    FROM product_performance
), med AS (
    SELECT (SELECT views FROM ordered_views WHERE rn = (n + 1) / 2) AS median_views,
           (SELECT r     FROM ordered_conv  WHERE rn = (n + 1) / 2) AS median_conversion
)
SELECT pp.*,
       CASE WHEN pp.views >= med.median_views AND pp.view_to_purchase_rate >= med.median_conversion THEN 'Star: high traffic, high conversion'
            WHEN pp.views >= med.median_views                                                       THEN 'Traffic without sales: high traffic, low conversion'
            WHEN pp.view_to_purchase_rate >= med.median_conversion                                  THEN 'Hidden gem: low traffic, high conversion'
            ELSE 'Low priority: low traffic, low conversion' END                                   AS quadrant,
       med.median_views, med.median_conversion
FROM product_performance pp
CROSS JOIN med;

CREATE VIEW vw_category_scorecard AS
SELECT cp.*,
       DENSE_RANK() OVER (ORDER BY orders DESC)                 AS orders_rank,
       DENSE_RANK() OVER (ORDER BY view_to_purchase_rate DESC)  AS conversion_rank,
       DENSE_RANK() OVER (ORDER BY net_revenue DESC)            AS revenue_rank
FROM category_performance cp;

-- @exec 6.4 retention views
CREATE VIEW vw_cohort_retention AS
SELECT cohort_week, cohort_start, week_offset, cohort_users, active_users,
       ROUND(100 * retention_rate, 2) AS retention_pct,
       CASE WHEN cohort_week <= 2 THEN 1 ELSE 0 END AS includes_pre_window_customers
FROM cohort_retention;

CREATE VIEW vw_segment_retention AS
SELECT 'acquisition channel' AS dimension, acquisition_channel AS segment, COUNT(*) AS users,
       COUNT(returned_within_28d) AS eligible_28d, ROUND(100.0 * AVG(returned_within_28d), 2) AS return_28d_pct,
       ROUND(AVG(n_active_weeks), 2) AS avg_active_weeks, SUM(ever_ordered) AS buyers,
       ROUND(100.0 * SUM(is_repeat_buyer) / NULLIF(SUM(ever_ordered), 0), 2) AS repeat_buyer_pct
FROM user_summary GROUP BY acquisition_channel
UNION ALL
SELECT 'primary device', primary_device, COUNT(*), COUNT(returned_within_28d), ROUND(100.0 * AVG(returned_within_28d), 2),
       ROUND(AVG(n_active_weeks), 2), SUM(ever_ordered), ROUND(100.0 * SUM(is_repeat_buyer) / NULLIF(SUM(ever_ordered), 0), 2)
FROM user_summary GROUP BY primary_device
UNION ALL
SELECT 'city', city, COUNT(*), COUNT(returned_within_28d), ROUND(100.0 * AVG(returned_within_28d), 2),
       ROUND(AVG(n_active_weeks), 2), SUM(ever_ordered), ROUND(100.0 * SUM(is_repeat_buyer) / NULLIF(SUM(ever_ordered), 0), 2)
FROM user_summary GROUP BY city;

-- @query Q26_product_quadrants
-- Do popular products necessarily generate the most purchases? Products and views by quadrant.
-- Finding (tested run): The 51 'star' products take 33.7% of views and 53.4% of units sold. The 75 'traffic without sales'
--          products take 47.4% of views but only 20.6% of units (pooled conversion 2.5% vs 7.4%).
SELECT quadrant,
       COUNT(*)                                                        AS products,
       SUM(views)                                                      AS views,
       ROUND(100.0 * SUM(views) / SUM(SUM(views)) OVER (), 1)          AS pct_of_views,
       SUM(units)                                                      AS units,
       ROUND(100.0 * SUM(units) / SUM(SUM(units)) OVER (), 1)          AS pct_of_units,
       ROUND(100.0 * SUM(viewer_buyers) / SUM(viewers), 2)             AS pooled_view_to_purchase_pct
FROM vw_product_scorecard
GROUP BY quadrant
ORDER BY views DESC;

-- @query Q27_daily_kpis
SELECT * FROM vw_daily_kpis ORDER BY date;

-- @query Q28_weekly_kpis
SELECT * FROM vw_weekly_kpis ORDER BY week_index;

-- @export events_enriched.gz
SELECT * FROM events_enriched ORDER BY event_id;

-- @export session_summary
SELECT * FROM session_summary ORDER BY session_id;

-- @export user_summary
SELECT * FROM user_summary ORDER BY user_id;

-- @export product_scorecard
SELECT * FROM vw_product_scorecard ORDER BY view_rank, product_id;

-- @export category_scorecard
SELECT * FROM vw_category_scorecard ORDER BY orders_rank;

-- @export cohort_retention
SELECT * FROM vw_cohort_retention ORDER BY cohort_week, week_offset;

-- @export cart_add_outcomes
SELECT * FROM cart_add_outcomes ORDER BY event_id;

-- @export session_funnel_by_segment
SELECT * FROM vw_session_funnel_by_segment ORDER BY platform, device_type, traffic_source, promo_period, is_first_session;


/* =====================================================================================================
   SECTION 7. VALIDATION AND RECONCILIATION
   Every check returns expected vs actual and PASS/FAIL. A FAIL means a derived table no longer reconciles
   with the source data and the analysis outputs should not be used until it is resolved.
   ===================================================================================================== */

-- @exec 7.1 validation checks
CREATE TABLE validation_results (
    check_id     TEXT PRIMARY KEY,
    category     TEXT NOT NULL,
    check_name   TEXT NOT NULL,
    expected     REAL,
    actual       REAL,
    status       TEXT NOT NULL CHECK (status IN ('PASS', 'FAIL'))
);

WITH checks (check_id, category, check_name, expected, actual) AS (
    -- record counts
    SELECT 'V01', 'record counts', 'source tables loaded with no row loss (tables failing)', 0,
           (SELECT COUNT(*) FROM load_audit WHERE status <> 'PASS')
    UNION ALL SELECT 'V02', 'record counts', 'events_enriched rows = events rows',
           (SELECT COUNT(*) FROM events), (SELECT COUNT(*) FROM events_enriched)
    UNION ALL SELECT 'V03', 'record counts', 'every event mapped to a calendar week (unmapped events)', 0,
           (SELECT COUNT(*) FROM events_enriched WHERE week_index IS NULL)
    UNION ALL SELECT 'V04', 'record counts', 'session_summary rows = sessions rows',
           (SELECT COUNT(*) FROM sessions), (SELECT COUNT(*) FROM session_summary)
    UNION ALL SELECT 'V05', 'record counts', 'user_summary rows = users rows',
           (SELECT COUNT(*) FROM users), (SELECT COUNT(*) FROM user_summary)
    -- duplicates and keys
    UNION ALL SELECT 'V06', 'duplicates', 'duplicate event_id in events_enriched', 0,
           (SELECT COUNT(*) - COUNT(DISTINCT event_id) FROM events_enriched)
    UNION ALL SELECT 'V07', 'duplicates', 'duplicate cart additions in cart_add_outcomes', 0,
           (SELECT COUNT(*) - COUNT(DISTINCT event_id) FROM cart_add_outcomes)
    UNION ALL SELECT 'V08', 'join integrity', 'foreign-key violations (PRAGMA foreign_key_check)', 0,
           (SELECT COUNT(*) FROM pragma_foreign_key_check)
    -- aggregation consistency
    UNION ALL SELECT 'V09', 'aggregation', 'sum of session event counts = events',
           (SELECT COUNT(*) FROM events), (SELECT SUM(n_events) FROM session_summary)
    UNION ALL SELECT 'V10', 'aggregation', 'sum of user session counts = sessions',
           (SELECT COUNT(*) FROM sessions), (SELECT SUM(n_sessions) FROM user_summary)
    UNION ALL SELECT 'V11', 'aggregation', 'orders in session_summary = orders',
           (SELECT COUNT(*) FROM orders), (SELECT SUM(has_order) FROM session_summary)
    UNION ALL SELECT 'V12', 'aggregation', 'product views in product_performance = traceable product_view events',
           (SELECT COUNT(*) FROM events WHERE event_type = 'product_view' AND product_id IS NOT NULL),
           (SELECT SUM(views) FROM product_performance)
    UNION ALL SELECT 'V13', 'aggregation', 'units in product_performance = units in order_items',
           (SELECT SUM(quantity) FROM order_items), (SELECT SUM(units) FROM product_performance)
    UNION ALL SELECT 'V14', 'aggregation', 'weekly cohort sizes sum to all users',
           (SELECT COUNT(*) FROM users), (SELECT SUM(cohort_users) FROM cohort_retention WHERE week_offset = 0)
    -- reconciliation of key metrics
    UNION ALL SELECT 'V15', 'reconciliation', 'net revenue: user_summary = orders table',
           (SELECT SUM(items_subtotal) FROM orders WHERE order_status NOT IN ('cancelled', 'returned')),
           (SELECT SUM(net_revenue) FROM user_summary)
    UNION ALL SELECT 'V16', 'reconciliation', 'net revenue: product_performance = order_items of net orders',
           (SELECT SUM(oi.line_total) FROM order_items oi JOIN orders o ON o.order_id = oi.order_id
             WHERE o.order_status NOT IN ('cancelled', 'returned')),
           (SELECT SUM(net_revenue) FROM product_performance)
    UNION ALL SELECT 'V17', 'reconciliation', 'net revenue: category_performance = product_performance',
           (SELECT SUM(net_revenue) FROM product_performance), (SELECT SUM(net_revenue) FROM category_performance)
    UNION ALL SELECT 'V18', 'reconciliation', 'closed user funnel final stage = all buyers (every buyer passed every stage)',
           (SELECT COUNT(DISTINCT user_id) FROM orders), (SELECT users FROM vw_user_funnel WHERE stage_no = 5)
    UNION ALL SELECT 'V19', 'reconciliation', 'weekly orders in vw_weekly_kpis = orders',
           (SELECT COUNT(*) FROM orders), (SELECT SUM(orders) FROM vw_weekly_kpis)
    UNION ALL SELECT 'V20', 'reconciliation', 'daily net revenue in vw_daily_kpis = user_summary net revenue',
           (SELECT SUM(net_revenue) FROM user_summary), (SELECT SUM(net_revenue) FROM vw_daily_kpis)
    -- business rules
    UNION ALL SELECT 'V21', 'business rule', 'user funnel never increases from one stage to the next (violations)', 0,
           (SELECT COUNT(*) FROM (SELECT users, LAG(users) OVER (ORDER BY stage_no) AS prev FROM vw_user_funnel) WHERE users > prev)
    UNION ALL SELECT 'V22', 'business rule', 'week-0 retention is 100% for every cohort (violations)', 0,
           (SELECT COUNT(*) FROM cohort_retention WHERE week_offset = 0 AND retention_rate <> 1)
    UNION ALL SELECT 'V23', 'business rule', 'retention and conversion rates within [0, 1] (violations)', 0,
           (SELECT COUNT(*) FROM cohort_retention WHERE retention_rate < 0 OR retention_rate > 1)
         + (SELECT COUNT(*) FROM product_performance WHERE view_to_purchase_rate > 1 OR cart_abandonment_rate > 1 OR view_to_cart_rate > 1)
    UNION ALL SELECT 'V24', 'business rule', 'every order session contains a begin_checkout event (orders without)', 0,
           (SELECT COUNT(*) FROM session_summary WHERE has_order = 1 AND has_begin_checkout = 0)
    UNION ALL SELECT 'V25', 'business rule', 'a same-session purchase is also a purchase within 7 days (violations)', 0,
           (SELECT COUNT(*) FROM cart_add_outcomes WHERE purchased_same_session = 1 AND purchased_within_7d = 0)
    UNION ALL SELECT 'V26', 'business rule', 'event-tracked buyers do not exceed order-based buyers (excess)', 0,
           MAX(0, (SELECT COUNT(DISTINCT user_id) FROM events WHERE event_type = 'purchase') - (SELECT COUNT(DISTINCT user_id) FROM orders))
    UNION ALL SELECT 'V27', 'business rule', 'censored return flags only for users with too little follow-up (violations)', 0,
           (SELECT COUNT(*) FROM user_summary WHERE (returned_within_28d IS NULL) <> (followup_days < 28))
)
INSERT INTO validation_results
SELECT check_id, category, check_name, expected, actual,
       CASE WHEN abs(expected - actual) < 0.5 THEN 'PASS' ELSE 'FAIL' END
FROM checks;

-- @query Q99_validation_results
SELECT * FROM validation_results ORDER BY check_id;

-- @query Q99_validation_summary
SELECT COUNT(*) AS checks, SUM(status = 'PASS') AS passed, SUM(status = 'FAIL') AS failed FROM validation_results;
