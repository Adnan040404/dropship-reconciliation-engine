"""Cleaning helpers for the two fields that break reconciliations most often:
PO numbers and money amounts.

Both are read as text and parsed by hand. Python's float()/int() are avoided on
purpose: float("358208349_782") is accepted and silently becomes 358208349782,
and floats cannot hold cents exactly. Amounts are returned as integer cents.
"""

import re
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

_SCIENTIFIC = re.compile(r"^[+-]?\d+(\.\d+)?[eE][+-]?\d+$")
_WHOLE_NUMBER = re.compile(r"^\d+(\.0+)?$")
_BLANKS = {"", "nan", "none", "null", "n/a", "na", "-", "--"}


def normalize_po(value, strip_regex=None):
    """Return a comparable key for a PO / order number.

    - trims spaces (including non-breaking ones) and stray quotes
    - repairs numbers Excel has turned into ``2088012076.0`` or ``2.088012076E+9``
    - upper-cases, so ``po123`` and ``PO123`` match
    - optionally removes a suffix or prefix with ``strip_regex`` (e.g. ``[-_x]\\d+$``)
    Leading zeros are kept, because they can be part of the number.
    """
    if value is None:
        return ""
    s = str(value).replace(" ", " ").strip().strip("'\"").strip()
    if s.lower() in _BLANKS:
        return ""
    if _SCIENTIFIC.match(s):
        try:
            d = Decimal(s)
            if d == d.to_integral_value():
                s = str(int(d))
        except InvalidOperation:
            pass
    elif _WHOLE_NUMBER.match(s):
        s = s.split(".")[0]
    s = s.upper()
    if strip_regex:
        s = re.sub(strip_regex, "", s, flags=re.IGNORECASE)
    return s.strip()


def parse_amount_cents(value):
    """Parse text such as ``$1,234.50``, ``(45.00)``, ``45.00-`` or ``-3`` into integer cents.

    Returns None when the value is blank or not a number, so the caller can reject the
    row with a reason instead of treating it as zero.
    """
    if value is None:
        return None
    s = str(value).replace(" ", " ").strip()
    if s.lower() in _BLANKS or s in {"—", "–"}:
        return None
    negative = False
    if s.startswith("(") and s.endswith(")"):
        negative, s = True, s[1:-1].strip()
    if s.endswith("-"):
        negative, s = True, s[:-1].strip()
    if s.startswith("-"):
        negative, s = True, s[1:].strip()
    elif s.startswith("+"):
        s = s[1:].strip()
    s = s.replace("$", "").replace(",", "").strip()
    if not re.fullmatch(r"\d+(\.\d+)?|\.\d+", s):
        return None
    try:
        cents = int((Decimal(s) * 100).to_integral_value(rounding=ROUND_HALF_UP))
    except InvalidOperation:
        return None
    return -cents if negative else cents


def dollars(cents):
    """Integer cents to a two-decimal float, for display only."""
    return round(cents / 100, 2)
