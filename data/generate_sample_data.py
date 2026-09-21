"""
Generates synthetic invoices.csv and payments.csv for the reconciliation
engine, with deliberate real-world edge cases baked in:

- Paid exactly       -> one payment, amount matches invoice
- Unpaid             -> no payment row at all
- Short pay          -> one payment, less than invoice amount
- Overpay            -> one payment, more than invoice amount
- Duplicate billing  -> two payments for the same invoice (paid twice)
- Unapplied payment  -> a payment whose PO doesn't match any invoice

All data is fake. Account codes are generic stand-ins, not real client data.
"""

import csv
import os
import random
from datetime import date, timedelta

random.seed(42)
HERE = os.path.dirname(os.path.abspath(__file__))  # write next to this script

ACCOUNTS = [
    ("AC1000", "Home Improvement Retailer A", "Marketplace"),
    ("AC2000", "Big Box Retailer B", "Marketplace"),
    ("AC3000", "Wholesale Club C", "Marketplace"),
    ("AC4000", "Furniture Marketplace D", "Marketplace"),
]

START_DATE = date(2026, 6, 1)


def random_date(offset_days=30):
    return START_DATE + timedelta(days=random.randint(0, offset_days))


def generate():
    invoices = []
    payments = []
    invoice_id = 1
    payment_id = 1
    po_seq = 100000

    scenarios = (
        ["paid"] * 40
        + ["unpaid"] * 15
        + ["short_pay"] * 15
        + ["overpay"] * 10
        + ["duplicate"] * 10
        + ["unapplied_extra"] * 10  # adds an extra unmatched payment, invoice still paid normally
    )
    random.shuffle(scenarios)

    for scenario in scenarios:
        account_code = random.choice(ACCOUNTS)[0]
        po_seq += 1
        po_number = f"PO{po_seq}"
        invoice_amount = round(random.uniform(50, 2000), 2)
        inv_date = random_date()

        invoices.append(
            {
                "invoice_id": invoice_id,
                "account_code": account_code,
                "po_number": po_number,
                "invoice_amount": invoice_amount,
                "invoice_date": inv_date.isoformat(),
            }
        )

        if scenario == "paid":
            payments.append(
                {
                    "payment_id": payment_id,
                    "account_code": account_code,
                    "po_number": po_number,
                    "payment_amount": invoice_amount,
                    "payment_date": (inv_date + timedelta(days=random.randint(5, 20))).isoformat(),
                    "payment_ref": f"PMT{payment_id}",
                }
            )
            payment_id += 1

        elif scenario == "unpaid":
            pass  # deliberately no payment row

        elif scenario == "short_pay":
            short_amount = round(invoice_amount * random.uniform(0.5, 0.9), 2)
            payments.append(
                {
                    "payment_id": payment_id,
                    "account_code": account_code,
                    "po_number": po_number,
                    "payment_amount": short_amount,
                    "payment_date": (inv_date + timedelta(days=random.randint(5, 20))).isoformat(),
                    "payment_ref": f"PMT{payment_id}",
                }
            )
            payment_id += 1

        elif scenario == "overpay":
            over_amount = round(invoice_amount * random.uniform(1.05, 1.3), 2)
            payments.append(
                {
                    "payment_id": payment_id,
                    "account_code": account_code,
                    "po_number": po_number,
                    "payment_amount": over_amount,
                    "payment_date": (inv_date + timedelta(days=random.randint(5, 20))).isoformat(),
                    "payment_ref": f"PMT{payment_id}",
                }
            )
            payment_id += 1

        elif scenario == "duplicate":
            for _ in range(2):
                payments.append(
                    {
                        "payment_id": payment_id,
                        "account_code": account_code,
                        "po_number": po_number,
                        "payment_amount": invoice_amount,
                        "payment_date": (inv_date + timedelta(days=random.randint(5, 20))).isoformat(),
                        "payment_ref": f"PMT{payment_id}",
                    }
                )
                payment_id += 1

        elif scenario == "unapplied_extra":
            # Normal payment for this invoice...
            payments.append(
                {
                    "payment_id": payment_id,
                    "account_code": account_code,
                    "po_number": po_number,
                    "payment_amount": invoice_amount,
                    "payment_date": (inv_date + timedelta(days=random.randint(5, 20))).isoformat(),
                    "payment_ref": f"PMT{payment_id}",
                }
            )
            payment_id += 1
            # ...plus an extra payment for a PO that has NO invoice at all (unapplied).
            po_seq += 1
            payments.append(
                {
                    "payment_id": payment_id,
                    "account_code": account_code,
                    "po_number": f"PO{po_seq}",
                    "payment_amount": round(random.uniform(50, 500), 2),
                    "payment_date": (inv_date + timedelta(days=random.randint(5, 20))).isoformat(),
                    "payment_ref": f"PMT{payment_id}",
                }
            )
            payment_id += 1

        invoice_id += 1

    with open(os.path.join(HERE, "accounts.csv"), "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["account_code", "account_name", "channel"])
        writer.writerows(ACCOUNTS)

    with open(os.path.join(HERE, "invoices.csv"), "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=invoices[0].keys())
        writer.writeheader()
        writer.writerows(invoices)

    with open(os.path.join(HERE, "payments.csv"), "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=payments[0].keys())
        writer.writeheader()
        writer.writerows(payments)

    print(f"Generated {len(invoices)} invoices and {len(payments)} payments.")


if __name__ == "__main__":
    generate()
