"""The matching core. All money is integer cents, so sums and comparisons are exact.

Status rules, in order (first match wins):

    Unpaid     no payment lines
    Paid       net paid is within the tolerance of the invoice
    Short Pay  net paid is less than the invoice
    Duplicate  2+ payment lines whose net total is exactly 2x, 3x or 4x the invoice
    Overpaid   net paid is more than the invoice

A "payment line" is a positive amount. Negative lines (fees, freight, chargebacks) are
deductions: they are categorised, subtracted from what was received, and reported
separately so a short payment can be explained by them.
"""

import re
from dataclasses import dataclass

import pandas as pd

from .normalize import dollars

DUPLICATE_MULTIPLES = (2, 3, 4)


def classify(invoice_cents, net_paid_cents, payment_lines, tolerance_cents):
    if payment_lines == 0:
        return "Unpaid"
    diff = invoice_cents - net_paid_cents
    if abs(diff) <= tolerance_cents:
        return "Paid"
    if diff > 0:
        return "Short Pay"
    if payment_lines >= 2 and any(abs(net_paid_cents - invoice_cents * m) <= tolerance_cents
                                  for m in DUPLICATE_MULTIPLES):
        return "Duplicate"
    return "Overpaid"


def categorise_deduction(description, rules):
    for category, pattern in rules.items():
        if re.search(pattern, description or "", flags=re.IGNORECASE):
            return category
    return "Uncategorised"


@dataclass
class Result:
    invoices: pd.DataFrame      # one row per PO, with status
    unapplied: pd.DataFrame     # payment lines whose PO has no invoice
    deductions: pd.DataFrame    # every negative line, categorised
    summary: dict


def reconcile(invoices, payments, account):
    """invoices / payments use the STANDARD columns from ingest. Returns a Result."""
    tol = account.tolerance_cents

    inv = (invoices.groupby("po_key", sort=True)
           .agg(invoice_cents=("amount_cents", "sum"), invoice_lines=("amount_cents", "size"),
                invoice_date=("date", "first"), po_raw=("po_raw", "first"))
           .reset_index())

    pay = payments.copy()
    pay["is_deduction"] = pay["amount_cents"] < 0
    received = pay[~pay["is_deduction"]].groupby("po_key").agg(
        gross_cents=("amount_cents", "sum"), payment_lines=("amount_cents", "size"))
    taken = pay[pay["is_deduction"]].groupby("po_key").agg(
        deduction_cents=("amount_cents", lambda s: int(-s.sum())))

    out = (inv.merge(received, on="po_key", how="left").merge(taken, on="po_key", how="left")
           .fillna({"gross_cents": 0, "payment_lines": 0, "deduction_cents": 0}))
    for col in ("gross_cents", "payment_lines", "deduction_cents"):
        out[col] = out[col].astype("int64")
    out["net_cents"] = out["gross_cents"] - out["deduction_cents"]
    out["diff_cents"] = out["invoice_cents"] - out["net_cents"]
    out["status"] = [classify(i, n, l, tol) for i, n, l in
                     zip(out["invoice_cents"], out["net_cents"], out["payment_lines"])]
    out["explained_by_deductions"] = (
        (out["status"] == "Short Pay") & (out["deduction_cents"] > 0)
        & ((out["diff_cents"] - out["deduction_cents"]).abs() <= tol))

    invoice_keys = set(inv["po_key"])
    unapplied = pay[~pay["is_deduction"] & ~pay["po_key"].isin(invoice_keys)].copy()
    deductions = pay[pay["is_deduction"]].copy()
    deductions["category"] = [categorise_deduction(d, account.deductions)
                              for d in deductions["description"]]
    deductions["matched_invoice"] = deductions["po_key"].isin(invoice_keys)

    report = pd.DataFrame({
        "PO": out["po_key"], "Original PO": out["po_raw"], "Invoice date": out["invoice_date"],
        "Invoice amount": out["invoice_cents"].map(dollars),
        "Received": out["gross_cents"].map(dollars),
        "Deductions": out["deduction_cents"].map(dollars),
        "Net paid": out["net_cents"].map(dollars),
        "Difference": out["diff_cents"].map(dollars),
        "Payment lines": out["payment_lines"], "Status": out["status"],
        "Explained by deductions": out["explained_by_deductions"].map({True: "Yes", False: ""}),
    })
    counts = out["status"].value_counts().to_dict()
    summary = {
        "invoices": int(len(out)), "status_counts": counts,
        "invoiced": dollars(int(out["invoice_cents"].sum())),
        "net_paid_on_invoices": dollars(int(out["net_cents"].sum())),
        "owed": dollars(int(out.loc[out["status"].isin(["Unpaid", "Short Pay"]), "diff_cents"].sum())),
        "excess": dollars(int(-out.loc[out["status"].isin(["Overpaid", "Duplicate"]), "diff_cents"].sum())),
        "unapplied_count": int(len(unapplied)),
        "unapplied_amount": dollars(int(unapplied["amount_cents"].sum())),
        "deduction_count": int(len(deductions)),
        "deduction_amount": dollars(int(-deductions["amount_cents"].sum())),
    }
    return Result(report, unapplied, deductions, summary)
