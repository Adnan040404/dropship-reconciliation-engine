"""
Phase A/B: builds a real SQLite database from schema/schema.sql and loads
the synthetic CSVs (data/accounts.csv, invoices.csv, payments.csv) into it.

Python's role here is deliberately thin: create the DB, run the schema,
load rows. All the actual reconciliation LOGIC lives in SQL (sql/*.sql),
not here.

Run:
    python db/setup_db.py
"""

import csv
import os
import sqlite3

DB_PATH = os.path.join(os.path.dirname(__file__), "reconcile.db")
SCHEMA_PATH = os.path.join(os.path.dirname(__file__), "..", "schema", "schema.sql")
DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")


def build_database():
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)  # always rebuild fresh, so this script is safely re-runnable

    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON;")

    with open(SCHEMA_PATH) as f:
        schema_sql = f.read()
    conn.executescript(schema_sql)

    load_csv(conn, "accounts.csv", "accounts",
             ["account_code", "account_name", "channel"])
    load_csv(conn, "invoices.csv", "invoices",
             ["invoice_id", "account_code", "po_number", "invoice_amount", "invoice_date"])
    load_csv(conn, "payments.csv", "payments",
             ["payment_id", "account_code", "po_number", "payment_amount", "payment_date", "payment_ref"])

    conn.commit()

    # Sanity check counts so a silent load failure (e.g. 0 rows) is loud, not hidden.
    for table in ("accounts", "invoices", "payments"):
        count = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        print(f"{table}: {count} rows loaded")

    conn.close()
    print(f"\nDatabase built at {DB_PATH}")


def load_csv(conn, filename, table, columns):
    path = os.path.join(DATA_DIR, filename)
    if not os.path.exists(path):
        raise FileNotFoundError(
            f"{path} not found — run `python data/generate_sample_data.py` first."
        )

    placeholders = ", ".join("?" for _ in columns)
    col_list = ", ".join(columns)
    insert_sql = f"INSERT INTO {table} ({col_list}) VALUES ({placeholders})"

    with open(path, newline="") as f:
        reader = csv.DictReader(f)
        rows = [tuple(row[c] for c in columns) for row in reader]

    if not rows:
        raise ValueError(f"{filename} loaded 0 rows — check the file isn't empty/malformed.")

    conn.executemany(insert_sql, rows)


if __name__ == "__main__":
    build_database()
