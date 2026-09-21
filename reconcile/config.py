"""Load and validate the per-account settings from config/accounts.toml."""

import sys
from dataclasses import dataclass, field
from pathlib import Path

if sys.version_info >= (3, 11):
    import tomllib
else:  # pragma: no cover - Python 3.10
    import tomli as tomllib

DEFAULT_CONFIG = Path(__file__).resolve().parent.parent / "config" / "accounts.toml"


class ConfigError(ValueError):
    pass


@dataclass(frozen=True)
class TableSpec:
    header_row: int
    columns: dict  # role -> column name in the file (po, amount, date, description)


@dataclass(frozen=True)
class Account:
    code: str
    name: str
    invoices: TableSpec
    payments: TableSpec
    po_regex: str
    tolerance_cents: int
    payments_are_negative: bool
    deductions: dict = field(default_factory=dict)  # category -> regex


def _table(raw, code, kind, required):
    if kind not in raw:
        raise ConfigError(f"{code}: missing [{kind}] section")
    section = dict(raw[kind])
    missing = [r for r in required if r not in section]
    if missing:
        raise ConfigError(f"{code}.{kind}: missing {', '.join(missing)}")
    header_row = int(section.pop("header_row", 1))
    if header_row < 1:
        raise ConfigError(f"{code}.{kind}: header_row must be 1 or more")
    return TableSpec(header_row=header_row, columns=section)


def load_accounts(path=None):
    path = Path(path or DEFAULT_CONFIG)
    if not path.exists():
        raise ConfigError(f"Config file not found: {path}")
    with open(path, "rb") as f:
        data = tomllib.load(f)
    accounts = {}
    for code, raw in data.get("accounts", {}).items():
        rules = raw.get("rules", {})
        tol = float(rules.get("tolerance", 0.01))
        if tol < 0:
            raise ConfigError(f"{code}: tolerance cannot be negative")
        accounts[code] = Account(
            code=code,
            name=raw.get("name", code),
            invoices=_table(raw, code, "invoices", ["po", "amount"]),
            payments=_table(raw, code, "payments", ["po", "amount"]),
            po_regex=rules.get("po_regex", ""),
            tolerance_cents=int(round(tol * 100)),
            payments_are_negative=bool(rules.get("payments_are_negative", False)),
            deductions=dict(raw.get("deductions", {})),
        )
    if not accounts:
        raise ConfigError(f"No accounts defined in {path}")
    return accounts


def get_account(code, path=None):
    accounts = load_accounts(path)
    if code not in accounts:
        raise ConfigError(f"Unknown account {code!r}. Known accounts: {', '.join(sorted(accounts))}")
    return accounts[code]
