"""
Builds two example accounts in deliberately different, messy export formats, plus an
expected.json for each that records the correct answer BY CONSTRUCTION (not by running
the engine), so tests can check the engine against known truth.

    python examples/make_examples.py

All data is generated. Nothing here comes from a real company or client.

AC1000  header on row 1, suffixes on payment POs (-1, _782, x2), "$1,234.50" text amounts,
        deductions written as (25.00)
AC2000  3 lines of report header above the column names, payments exported as NEGATIVE
        numbers, POs damaged like Excel does it (2088012076.0 and 2.088012077E+9),
        a 5-cent tolerance
"""

import csv
import json
import random
from datetime import date, timedelta
from pathlib import Path

HERE = Path(__file__).resolve().parent
rng = random.Random(11)


def money(cents, style):
    d = f"{abs(cents) / 100:,.2f}"
    if style == "dollar":
        return f"${d}" if cents >= 0 else f"(${d})"
    if style == "paren":
        return d if cents >= 0 else f"({d})"
    return f"{cents / 100:.2f}"


def when(i):
    return date(2026, 6, 1) + timedelta(days=i % 27)


# --------------------------------------------------------------------------- AC1000
def build_ac1000():
    cases = (["paid"] * 14 + ["unpaid"] * 4 + ["short"] * 3 + ["over"] * 3 + ["dup"] * 2
             + ["explained"] * 2)
    rng.shuffle(cases)
    invoices, payments = [], []
    expected = {"Paid": 0, "Unpaid": 0, "Short Pay": 0, "Overpaid": 0, "Duplicate": 0}
    explained = 0
    suffixes = ["", "-1", "_782", "x2", "-3", ""]
    for i, case in enumerate(cases):
        po = 1000101 + i
        amt = rng.randint(4000, 180000)                  # cents
        invoices.append([po, money(amt, "dollar"), when(i).strftime("%m/%d/%Y")])
        d = (when(i) + timedelta(days=12)).strftime("%m/%d/%Y")
        ref = f"{po}{suffixes[i % len(suffixes)]}"

        def pay(cents, note=""):
            payments.append([ref, money(cents, "dollar"), d, note])

        if case == "paid":
            pay(amt); expected["Paid"] += 1
        elif case == "unpaid":
            expected["Unpaid"] += 1
        elif case == "short":
            pay(int(amt * 0.8)); expected["Short Pay"] += 1
        elif case == "over":
            pay(int(amt * 1.15)); expected["Overpaid"] += 1
        elif case == "dup":
            pay(amt); pay(amt); expected["Duplicate"] += 1
        elif case == "explained":
            pay(amt)
            payments.append([ref, money(-2500, "dollar"), d, "Freight deduction"])
            expected["Short Pay"] += 1; explained += 1

    # payments that match no invoice, and a deduction with no invoice
    payments.append(["1999001", money(31250, "dollar"), "06/20/2026", "Remittance, no order"])
    payments.append(["1999002-1", money(8800, "dollar"), "06/21/2026", "Remittance, no order"])
    payments.append(["1999003", money(-1800, "dollar"), "06/21/2026", "Damaged goods claim"])
    # rows the engine must reject with a reason, not skip
    payments.append(["", money(5000, "dollar"), "06/22/2026", "no PO on this line"])
    payments.append([f"{1000101}", "N/A", "06/22/2026", "amount missing"])
    invoices.append([1000999, "TBD", "06/23/2026"])
    rng.shuffle(payments)

    out = HERE / "AC1000"
    out.mkdir(exist_ok=True)
    with open(out / "invoices.csv", "w", newline="") as f:
        w = csv.writer(f); w.writerow(["Order #", "Invoice Amount", "Invoice Date"]); w.writerows(invoices)
    with open(out / "payments.csv", "w", newline="") as f:
        w = csv.writer(f); w.writerow(["PO Number", "Net Paid", "Paid On", "Description"]); w.writerows(payments)
    (out / "expected.json").write_text(json.dumps({
        "status_counts": expected, "explained_by_deductions": explained, "unapplied_lines": 2,
        "deduction_lines": 3, "rejected_invoice_rows": 1, "rejected_payment_rows": 2,
        "invoice_rows": len(invoices), "payment_rows": len(payments)}, indent=2))


# --------------------------------------------------------------------------- AC2000
def build_ac2000():
    cases = (["paid"] * 10 + ["tol"] * 2 + ["unpaid"] * 3 + ["short"] * 2 + ["over"] * 2
             + ["dup"] * 1 + ["explained"] * 2)
    rng.shuffle(cases)
    invoices, payments = [], []
    expected = {"Paid": 0, "Unpaid": 0, "Short Pay": 0, "Overpaid": 0, "Duplicate": 0}
    explained = 0
    for i, case in enumerate(cases):
        po = 2088012070 + i * 7
        amt = rng.randint(6000, 250000)
        invoices.append([po, money(amt, "plain"), when(i).strftime("%Y-%m-%d")])
        d = (when(i) + timedelta(days=9)).strftime("%Y-%m-%d")
        if i % 4 == 0:
            ref = f"{po}.0"                                                    # float artifact
        elif i % 4 == 1:
            ref = f"{po / 1_000_000_000:.9f}".rstrip("0").rstrip(".") + "E+9"  # scientific notation
        else:
            ref = str(po)

        def pay(cents, note="Remittance"):
            payments.append([ref, money(-cents, "plain"), d, note])   # payments exported as negative

        if case == "paid":
            pay(amt); expected["Paid"] += 1
        elif case == "tol":
            pay(amt - 4); expected["Paid"] += 1                       # 4 cents short, inside the 5c tolerance
        elif case == "unpaid":
            expected["Unpaid"] += 1
        elif case == "short":
            pay(int(amt * 0.9)); expected["Short Pay"] += 1
        elif case == "over":
            pay(int(amt * 1.2)); expected["Overpaid"] += 1
        elif case == "dup":
            pay(amt); pay(amt); expected["Duplicate"] += 1
        elif case == "explained":
            pay(amt)
            payments.append([ref, money(3000, "plain"), d, "Commission and referral fee"])   # deduction = positive
            expected["Short Pay"] += 1; explained += 1

    payments.append(["2088999001", money(-45000, "plain"), "2026-06-20", "Remittance, no order"])
    payments.append(["2088999002", money(1200, "plain"), "2026-06-21", "Freight charge"])   # deduction, no invoice
    rng.shuffle(payments)

    out = HERE / "AC2000"
    out.mkdir(exist_ok=True)
    with open(out / "invoices.csv", "w", newline="") as f:
        w = csv.writer(f); w.writerow(["PO", "Total", "Date"]); w.writerows(invoices)
    with open(out / "payments.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["Retailer B Remittance Report"])
        w.writerow(["Run date: 2026-07-02", "Currency: USD"])
        w.writerow([])
        w.writerow(["Invoice Ref", "Amount", "Posting Date", "Reason"])
        w.writerows(payments)
    (out / "expected.json").write_text(json.dumps({
        "status_counts": expected, "explained_by_deductions": explained, "unapplied_lines": 1,
        "deduction_lines": explained + 1, "rejected_invoice_rows": 0, "rejected_payment_rows": 0,
        "invoice_rows": len(invoices), "payment_rows": len(payments)}, indent=2))


if __name__ == "__main__":
    build_ac1000()
    build_ac2000()
    print("Wrote examples/AC1000 and examples/AC2000")
