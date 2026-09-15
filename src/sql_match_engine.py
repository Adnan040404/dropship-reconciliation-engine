"""
SQL-backed version of the reconciliation engine. Python's job here is
deliberately minimal: open the database, run the SQL files, export the
results. All matching/classification logic lives in sql/*.sql, not here.

Run:
    python db/setup_db.py           # build the database first
    python src/sql_match_engine.py  # then run this
"""

import os
import sqlite3
import csv

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "db", "reconcile.db")
SQL_DIR = os.path.join(os.path.dirname(__file__), "..", "sql")


def run_query_to_csv(conn, sql_filename, output_filename):
    with open(os.path.join(SQL_DIR, sql_filename)) as f:
        query = f.read()

    cursor = conn.execute(query)
    columns = [d[0] for d in cursor.description]
    rows = cursor.fetchall()

    with open(output_filename, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(columns)
        writer.writerows(rows)

    return columns, rows


def main():
    if not os.path.exists(DB_PATH):
        raise FileNotFoundError("Database not found — run `python db/setup_db.py` first.")

    conn = sqlite3.connect(DB_PATH)

    columns, rows = run_query_to_csv(
        conn, "reconciliation_query.sql", "sql_reconciliation_report.csv"
    )
    status_idx = columns.index("status")
    status_counts = {}
    for row in rows:
        status = row[status_idx]
        status_counts[status] = status_counts.get(status, 0) + 1

    print("=== SQL Reconciliation Summary ===")
    for status, count in sorted(status_counts.items()):
        print(f"{status:12s} {count}")

    _, unapplied_rows = run_query_to_csv(
        conn, "unapplied_payments.sql", "sql_unapplied_payments.csv"
    )
    print(f"\nUnapplied payments (no matching invoice): {len(unapplied_rows)}")

    print("\nsql_reconciliation_report.csv")
    print("sql_unapplied_payments.csv")

    conn.close()


if __name__ == "__main__":
    main()
