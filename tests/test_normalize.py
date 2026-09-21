"""PO and amount cleaning: the small things that quietly break reconciliations."""

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from reconcile.normalize import normalize_po, parse_amount_cents  # noqa: E402


@pytest.mark.parametrize("raw,expected", [
    ("2088012076", "2088012076"),
    ("2088012076.0", "2088012076"),          # Excel turned the number into a float
    ("2088012076.000", "2088012076"),
    ("2.088012077E+9", "2088012077"),         # Excel scientific notation
    ("  po123  ", "PO123"),                   # spaces and case
    ("po123", "PO123"),
    (" PO123 ", "PO123"),           # non-breaking spaces from web exports
    ("'00123", "00123"),                      # Excel text prefix; leading zeros are kept
    ("00123", "00123"),
    ('"PO-9"', "PO-9"),
])
def test_normalize_po(raw, expected):
    assert normalize_po(raw) == expected


@pytest.mark.parametrize("blank", [None, "", "  ", "nan", "NaN", "None", "N/A", "-"])
def test_blank_po_becomes_empty(blank):
    assert normalize_po(blank) == ""


def test_suffix_regex_strips_store_and_line_suffixes():
    rx = r"[-_x]\d+$"
    assert normalize_po("1000105-3", rx) == "1000105"
    assert normalize_po("1000105_782", rx) == "1000105"
    assert normalize_po("1000105x2", rx) == "1000105"
    assert normalize_po("1000105", rx) == "1000105"       # nothing to strip


def test_underscore_number_is_not_glued_together():
    """Python's float("358208349_782") is 358208349782.0. A PO like this must be left alone
    for the suffix rule to clean, never merged into one wrong number."""
    assert normalize_po("358208349_782") == "358208349_782"
    assert normalize_po("358208349_782", r"_\d+$") == "358208349"


@pytest.mark.parametrize("raw,cents", [
    ("$1,234.50", 123450),
    ("1234.5", 123450),
    ("$ 12.30", 1230),
    ("(45.00)", -4500),                       # accounting negative
    ("($45.00)", -4500),
    ("45.00-", -4500),                        # trailing minus
    ("-3", -300),
    ("+7.10", 710),
    ("0.005", 1),                             # half a cent rounds up, deliberately
    ("0", 0),
    (".75", 75),
    (1234.5, 123450),
    (0.1 + 0.2, 30),                          # float noise must not leak into cents
])
def test_parse_amount_cents(raw, cents):
    assert parse_amount_cents(raw) == cents


@pytest.mark.parametrize("bad", [None, "", "N/A", "TBD", "abc", "1.2.3", "12,34,5x", "--5"])
def test_unparseable_amount_is_none_not_zero(bad):
    assert parse_amount_cents(bad) is None
