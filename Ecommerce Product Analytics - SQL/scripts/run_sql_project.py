"""Runs the SQL project block by block and exports every analytical result.

The SQL file is plain SQLite SQL and runs unchanged in the sqlite3 shell. This runner adds three things:
  * it executes each "-- @exec" block and each "-- @query" block separately, with timings;
  * it writes the result of every "-- @query <name>" block to outputs/results/<name>.csv;
  * it writes every "-- @export <name>" block (cleaned / derived tables) to data/processed/<name>.csv
    (or <name>.csv.gz when the label ends in .gz);
  * it stops at the first error and reports the block that failed.
No analysis is done in Python: every number in the exported files is computed by the SQL.

Usage (from the repository root):
    python scripts/run_sql_project.py                       # builds data/processed/ecommerce_analytics.db
    python scripts/run_sql_project.py --sql sql/ecommerce_product_analytics.sql --db data/processed/ecommerce_analytics.db
"""
import argparse
import csv
import gzip
import re
import sqlite3
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MARKER = re.compile(r"^-- @(exec|query|export)\s+(.+?)\s*$", re.M)


def blocks(sql_text):
    marks = list(MARKER.finditer(sql_text))
    for i, m in enumerate(marks):
        end = marks[i + 1].start() if i + 1 < len(marks) else len(sql_text)
        body = sql_text[m.end():end]
        yield m.group(1), m.group(2), body


def strip_trailing_comments(sql):
    """Remove comment-only lines and section banners that follow the last statement of a query block."""
    sql = re.sub(r"/\*.*?\*/", "", sql, flags=re.S)
    return sql.strip()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sql", nargs="+", default=["sql/ecommerce_product_analytics.sql"])
    ap.add_argument("--db", default="data/processed/ecommerce_analytics.db")
    ap.add_argument("--results", default="outputs/results")
    ap.add_argument("--exports", default="data/processed")
    ap.add_argument("--fresh", action="store_true", help="delete the analysis database first")
    a = ap.parse_args()

    import os
    os.chdir(ROOT)
    db = Path(a.db)
    if a.fresh:
        for suffix in ("", "-wal", "-shm"):
            Path(str(db) + suffix).unlink(missing_ok=True)
    db.parent.mkdir(parents=True, exist_ok=True)
    out = Path(a.results)
    out.mkdir(parents=True, exist_ok=True)
    exp = Path(a.exports)
    exp.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(f"file:{db}?mode=rwc", uri=True, isolation_level=None)
    log = []
    t_all = time.time()
    for sql_file in a.sql:
        text = Path(sql_file).read_text(encoding="utf-8")
        for kind, label, body in blocks(text):
            t0 = time.time()
            try:
                if kind == "exec":
                    conn.executescript(body)
                    rows = ""
                else:
                    stmt = strip_trailing_comments(body).rstrip().rstrip(";")
                    cur = conn.execute(stmt)
                    cols = [d[0] for d in cur.description]
                    data = cur.fetchall()
                    if kind == "export" and label.endswith(".gz"):   # large tables are written gzip-compressed
                        target, opener = exp / f"{label[:-3]}.csv.gz", gzip.open
                    else:
                        target, opener = (exp if kind == "export" else out) / f"{label}.csv", open
                    with opener(target, "wt", newline="", encoding="utf-8") as fh:
                        w = csv.writer(fh)
                        w.writerow(cols)
                        w.writerows(data)
                    rows = len(data)
            except sqlite3.Error as ex:
                print(f"ERROR in {sql_file} block '{label}': {ex}")
                sys.exit(1)
            dt = time.time() - t0
            log.append((sql_file, kind, label, round(dt, 2), rows))
            print(f"{kind:5s} {dt:7.2f}s  {label}" + (f"  -> {rows} rows" if rows != "" else ""))
    with open(out / "_run_log.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["sql_file", "kind", "block", "seconds", "rows"])
        w.writerows(log)
    conn.close()
    print(f"Completed {len(log)} blocks in {time.time() - t_all:.1f}s; "
          f"{sum(1 for x in log if x[1] == 'query')} result files in {out}/, "
          f"{sum(1 for x in log if x[1] == 'export')} table exports in {exp}/")


if __name__ == "__main__":
    main()
