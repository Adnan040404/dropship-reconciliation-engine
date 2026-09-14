"""
Unit tests for the classification logic -- covers each real edge case
directly, independent of the random synthetic data generator.
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from match_engine import classify  # noqa: E402


def test_paid_exact():
    assert classify(invoice_amount=500.00, total_paid=500.00, payment_count=1) == "Paid"


def test_unpaid_no_payment():
    assert classify(invoice_amount=500.00, total_paid=0.0, payment_count=0) == "Unpaid"


def test_short_pay():
    assert classify(invoice_amount=500.00, total_paid=350.00, payment_count=1) == "Short Pay"


def test_overpay_single_payment():
    assert classify(invoice_amount=500.00, total_paid=600.00, payment_count=1) == "Overpaid"


def test_duplicate_exact_double_payment():
    assert classify(invoice_amount=500.00, total_paid=1000.00, payment_count=2) == "Duplicate"


def test_overpay_not_a_clean_multiple_even_with_two_payments():
    # Two payments, but total isn't a clean multiple -> genuinely just overpaid,
    # not a duplicate (e.g. one full payment + one small extra fee payment).
    assert classify(invoice_amount=500.00, total_paid=550.00, payment_count=2) == "Overpaid"


def test_rounding_tolerance():
    # A one-cent rounding difference should still count as Paid, not Short Pay.
    assert classify(invoice_amount=500.00, total_paid=499.995, payment_count=1) == "Paid"
