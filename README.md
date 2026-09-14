# Dropship Reconciliation Engine

A financial reconciliation engine that matches invoices against payments for
multi-account dropship/retail operations — detecting unpaid invoices,
short-payments, overpayments, and duplicate billing automatically.

This project is modeled on real invoice/payment reconciliation work I do
professionally as a Financial Data Analyst across 15+ major retail dropship
accounts (Lowe's, Home Depot, Walmart, Sam's Club, Wayfair, and others).
**All data here is synthetic** — generated to reproduce the same real-world
edge cases (short pay, overpayment, duplicate billing, unapplied payments)
without using any real client data.

## The problem

When a business ships goods through multiple retail marketplaces, invoices
and payments arrive from different systems, on different schedules, with
inconsistent formats — and money regularly goes missing in the gap:

- An invoice never gets paid at all
- A payment covers *less* than the invoice (short payment / deduction)
- A payment covers *more* than the invoice (overpayment)
- The same invoice gets billed/paid twice (duplicate billing)
- A payment arrives but never gets applied to any invoice (unapplied credit)

Finding these automatically, per account, at scale, is the actual job this
engine does.

## How it works

1. **Load** invoice and payment records (per account) — `data/`
2. **Match** each payment to its invoice by PO number + account code
3. **Classify** every invoice as Paid / Unpaid / Short Pay / Overpaid / Duplicate
4. **Report** a per-account reconciliation summary

```
invoices.csv + payments.csv → match_engine.py → reconciliation_report.csv
```

## Project structure

```
schema/schema.sql          — table definitions (for a real SQL-backed version)
data/generate_sample_data.py  — creates synthetic invoices.csv / payments.csv with real edge cases baked in
src/match_engine.py        — core matching + classification logic
tests/test_match_engine.py — unit tests covering each edge case
```

## Running it

```bash
pip install -r requirements.txt
python data/generate_sample_data.py     # generates data/invoices.csv and data/payments.csv
python src/match_engine.py              # produces reconciliation_report.csv
```

## Status

🚧 Work in progress — built incrementally, each stage tested against real
edge cases before moving to the next. See commit history for progression.

## Roadmap

- [x] Schema design
- [x] Synthetic data generator with real edge cases
- [x] Core matching engine (pandas)
- [ ] SQL-backed version (load into SQLite/Postgres, matching via SQL)
- [ ] PySpark version for scale
- [ ] Power BI / dashboard reporting layer
