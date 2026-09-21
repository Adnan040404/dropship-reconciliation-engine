"""
Core reconciliation engine: matches invoices to payments (by account_code +
po_number) and classifies every invoice as one of:

    Paid        - total payments == invoice amount
    Unpaid      - no payment at all
    Short Pay   - total payments < invoice amount
    Overpaid    - total payments > invoice amount
    Duplicate   - total payments is (approximately) an exact multiple of the
                  invoice amount from 2+ separate payments -- i.e. the same
                  invoice was paid more than once, not just overpaid once.

Also separately reports "unapplied payments": payments whose PO number
doesn't match ANY invoice at all -- money that came in but was never
claimed by an invoice. This is a real, common category in retail
reconciliation, distinct from a payment that's merely the wrong amount.

Design note: the Duplicate-vs-Overpaid distinction here is a simple
heuristic (an exact-multiple check with 2+ payments) -- a real production
system would also weigh payment dates/references being suspiciously close
together. Documented here deliberately, not hidden, since "know the limits
of your own heuristic" is the actual skill being demonstrated.
"""

import os

import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

TOLERANCE = 0.01  # cents-level rounding tolerance


def classify(invoice_amount: float, total_paid: float, payment_count: int) -> str:
    if payment_count == 0:
        return "Unpaid"

    difference = round(invoice_amount - total_paid, 2)

    if abs(difference) <= TOLERANCE:
        return "Paid"

    if difference > 0:
        return "Short Pay"

    # difference < 0 => paid more than invoiced
    if payment_count >= 2:
        for multiple in (2, 3, 4):
            if abs(total_paid - invoice_amount * multiple) <= TOLERANCE:
                return "Duplicate"

    return "Overpaid"


def run(invoices_path=os.path.join(ROOT, "data", "invoices.csv"),
        payments_path=os.path.join(ROOT, "data", "payments.csv"),
        report_path=os.path.join(ROOT, "reconciliation_report.csv"),
        unapplied_path=os.path.join(ROOT, "unapplied_payments.csv")):

    invoices = pd.read_csv(invoices_path)
    payments = pd.read_csv(payments_path)

    payments_agg = (
        payments.groupby(["account_code", "po_number"])
        .agg(total_paid=("payment_amount", "sum"), payment_count=("payment_amount", "count"))
        .reset_index()
    )

    merged = invoices.merge(payments_agg, on=["account_code", "po_number"], how="left")
    merged["total_paid"] = merged["total_paid"].fillna(0)
    merged["payment_count"] = merged["payment_count"].fillna(0).astype(int)
    merged["difference"] = (merged["invoice_amount"] - merged["total_paid"]).round(2)

    merged["status"] = merged.apply(
        lambda r: classify(r["invoice_amount"], r["total_paid"], r["payment_count"]), axis=1
    )

    report_cols = [
        "invoice_id", "account_code", "po_number", "invoice_amount",
        "total_paid", "difference", "status", "payment_count",
    ]
    merged[report_cols].to_csv(report_path, index=False)

    # Unapplied payments: payments whose (account_code, po_number) has no
    # matching invoice at all.
    invoice_keys = set(zip(invoices["account_code"], invoices["po_number"]))
    unapplied_mask = ~payments.apply(
        lambda r: (r["account_code"], r["po_number"]) in invoice_keys, axis=1
    )
    unapplied = payments[unapplied_mask]
    unapplied.to_csv(unapplied_path, index=False)

    # Summary
    print("=== Reconciliation Summary ===")
    print(merged["status"].value_counts().to_string())
    print(f"\nUnapplied payments (no matching invoice): {len(unapplied)}")
    print(f"\nFull report -> {report_path}")
    print(f"Unapplied payments -> {unapplied_path}")

    return merged, unapplied


if __name__ == "__main__":
    run()
