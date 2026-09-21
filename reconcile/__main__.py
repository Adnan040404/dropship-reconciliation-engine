"""
Reconcile one account's invoice and payment files into an Excel report.

    python -m reconcile --list-accounts
    python -m reconcile --account AC1000 --invoices examples/AC1000/invoices.csv \\
        --payments examples/AC1000/payments.csv --out output/AC1000_report.xlsx

Account settings (column names, header row, PO suffix rule, tolerance, sign convention,
deduction categories) come from config/accounts.toml.
"""

import argparse
import sys

from .config import ConfigError, DEFAULT_CONFIG, get_account, load_accounts
from .engine import reconcile
from .ingest import IngestError, ingest
from .report import write_report


def main(argv=None):
    p = argparse.ArgumentParser(prog="reconcile", description=__doc__.split("\n\n")[0])
    p.add_argument("--account", help="account code from the config file, e.g. AC1000")
    p.add_argument("--invoices", help="invoice export (CSV or Excel)")
    p.add_argument("--payments", help="payment export (CSV or Excel)")
    p.add_argument("--out", default="reconciliation_report.xlsx", help="Excel file to write")
    p.add_argument("--config", default=str(DEFAULT_CONFIG), help="accounts config (TOML)")
    p.add_argument("--list-accounts", action="store_true", help="show configured accounts and exit")
    args = p.parse_args(argv)

    try:
        if args.list_accounts:
            for code, acct in sorted(load_accounts(args.config).items()):
                print(f"{code}: {acct.name} (tolerance ${acct.tolerance_cents / 100:.2f})")
            return 0
        if not (args.account and args.invoices and args.payments):
            p.error("--account, --invoices and --payments are required")
        account = get_account(args.account, args.config)

        inv, inv_rej, inv_seen = ingest(args.invoices, account.invoices, account.po_regex)
        pay, pay_rej, pay_seen = ingest(args.payments, account.payments, account.po_regex,
                                        negate=account.payments_are_negative)
    except (ConfigError, IngestError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2

    result = reconcile(inv, pay, account)
    counts = {"invoice_seen": inv_seen, "invoice_used": len(inv), "invoice_rejected": len(inv_rej),
              "payment_seen": pay_seen, "payment_used": len(pay), "payment_rejected": len(pay_rej)}
    write_report(args.out, account, result, inv_rej, pay_rej, counts)

    s = result.summary
    print(f"Account {account.code}: {inv_seen} invoice rows, {pay_seen} payment rows")
    if len(inv_rej) or len(pay_rej):
        print(f"  rejected: {len(inv_rej)} invoice rows, {len(pay_rej)} payment rows (see 'Rejected rows')")
    for status in ["Paid", "Unpaid", "Short Pay", "Overpaid", "Duplicate"]:
        print(f"  {status:<10} {s['status_counts'].get(status, 0)}")
    print(f"  owed ${s['owed']:,.2f} | excess ${s['excess']:,.2f} | unapplied {s['unapplied_count']} "
          f"(${s['unapplied_amount']:,.2f}) | deductions {s['deduction_count']} (${s['deduction_amount']:,.2f})")
    print(f"Report: {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
