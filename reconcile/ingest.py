"""Read an account's invoice and payment exports into one standard shape.

Real exports are messy: the header is not always on row 1, column names differ by
account, and PO numbers and amounts arrive as text. Rows that can't be used are
returned in a reject list with a reason. They are never silently dropped.
"""

from pathlib import Path

import pandas as pd

from .normalize import normalize_po, parse_amount_cents

STANDARD = ["source_row", "po_raw", "po_key", "amount_cents", "date", "description"]


class IngestError(ValueError):
    pass


def load_table(path, header_row=1):
    """Read a CSV or Excel file as text. header_row is 1-based."""
    path = Path(path)
    if not path.exists():
        raise IngestError(f"File not found: {path}")
    skip = header_row - 1
    suffix = path.suffix.lower()
    if suffix in {".csv", ".txt"}:
        df = pd.read_csv(path, dtype=str, keep_default_na=False, skiprows=skip,
                         skip_blank_lines=False, encoding="utf-8-sig")
    elif suffix in {".xlsx", ".xlsm", ".xls"}:
        df = pd.read_excel(path, dtype=str, header=skip).fillna("")
    else:
        raise IngestError(f"Unsupported file type {suffix!r}: {path.name}")
    df.columns = [str(c).strip() for c in df.columns]
    df["__row"] = range(header_row + 1, header_row + 1 + len(df))   # row number in the file
    return df


def _pick(df, column, role, path):
    wanted = str(column).strip()
    if wanted in df.columns:
        return wanted
    lowered = {c.lower(): c for c in df.columns}
    if wanted.lower() in lowered:
        return lowered[wanted.lower()]
    raise IngestError(
        f"{Path(path).name}: column {wanted!r} (for {role}) not found. "
        f"Columns in the file: {', '.join(c for c in df.columns if c != '__row')}. "
        f"Check header_row and the column names in the account's config.")


def ingest(path, spec, po_regex="", negate=False):
    """Return (rows, rejects, records_seen). rows uses the STANDARD columns; amounts are integer
    cents. records_seen counts every non-blank line, so rows + rejects must equal it."""
    df = load_table(path, spec.header_row)
    cols = spec.columns
    po_col = _pick(df, cols["po"], "PO", path)
    amt_col = _pick(df, cols["amount"], "amount", path)
    date_col = _pick(df, cols["date"], "date", path) if cols.get("date") else None
    desc_col = _pick(df, cols["description"], "description", path) if cols.get("description") else None

    rows, rejects, seen = [], [], 0
    for rec in df.to_dict("records"):
        if not any(str(v).strip() for k, v in rec.items() if k != "__row"):
            continue  # a fully blank line is not a record
        seen += 1
        po_raw = rec[po_col]
        po_key = normalize_po(po_raw, po_regex)
        cents = parse_amount_cents(rec[amt_col])
        reason = None
        if not po_key:
            reason = "missing PO"
        elif cents is None:
            reason = f"amount is not a number: {rec[amt_col]!r}"
        if reason:
            rejects.append({"source_row": rec["__row"], "po_raw": po_raw,
                            "amount_raw": rec[amt_col], "reason": reason})
            continue
        rows.append({
            "source_row": rec["__row"], "po_raw": str(po_raw).strip(), "po_key": po_key,
            "amount_cents": -cents if negate else cents,
            "date": _as_date(rec[date_col]) if date_col else "",
            "description": str(rec[desc_col]).strip() if desc_col else "",
        })
    return (pd.DataFrame(rows, columns=STANDARD),
            pd.DataFrame(rejects, columns=["source_row", "po_raw", "amount_raw", "reason"]), seen)


def _as_date(value):
    text = str(value).strip()
    if not text:
        return ""
    parsed = pd.to_datetime(text, errors="coerce")
    return text if pd.isna(parsed) else parsed.strftime("%Y-%m-%d")
