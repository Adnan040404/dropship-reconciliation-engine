"""The pandas engine, the CTE query and the window-function query must agree, invoice by invoice."""

import os
import sqlite3
import subprocess
import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "db"))

import match_engine  # noqa: E402
import setup_db  # noqa: E402


@pytest.fixture(scope="module")
def db(tmp_path_factory):
    subprocess.run([sys.executable, str(ROOT / "data" / "generate_sample_data.py")], check=True,
                   capture_output=True)
    path = tmp_path_factory.mktemp("db") / "reconcile.db"
    setup_db.build_database(str(path))
    return path


def query(db, sql_file):
    conn = sqlite3.connect(db)
    try:
        return pd.read_sql_query((ROOT / "sql" / sql_file).read_text(encoding="utf-8"), conn)
    finally:
        conn.close()


def test_window_version_matches_the_cte_version_exactly(db):
    cte = query(db, "reconciliation_query.sql")
    win = query(db, "reconciliation_window.sql")
    assert len(cte) == len(win) == 100
    pd.testing.assert_frame_equal(cte.reset_index(drop=True), win.reset_index(drop=True))


def test_sql_matches_the_pandas_engine_invoice_by_invoice(db, tmp_path):
    win = query(db, "reconciliation_window.sql").set_index("invoice_id")["status"]
    merged, _ = match_engine.run(report_path=str(tmp_path / "r.csv"), unapplied_path=str(tmp_path / "u.csv"))
    pandas_status = merged.set_index("invoice_id")["status"]
    assert (win.sort_index() == pandas_status.sort_index()).all()


def test_expected_counts_on_the_sample_data(db):
    counts = query(db, "reconciliation_window.sql")["status"].value_counts().to_dict()
    assert counts == {"Paid": 50, "Unpaid": 15, "Short Pay": 15, "Overpaid": 10, "Duplicate": 10}
