-- Dropship Reconciliation Engine — schema
-- Designed for MySQL/Postgres/SQLite compatibility where reasonable.

CREATE TABLE accounts (
    account_code    VARCHAR(20) PRIMARY KEY,
    account_name    VARCHAR(100) NOT NULL,
    channel         VARCHAR(50)              -- e.g. 'Marketplace', 'Direct'
);

CREATE TABLE invoices (
    invoice_id      INTEGER PRIMARY KEY,
    account_code    VARCHAR(20) NOT NULL REFERENCES accounts(account_code),
    po_number       VARCHAR(50) NOT NULL,
    invoice_amount  DECIMAL(12,2) NOT NULL,
    invoice_date    DATE NOT NULL
);

CREATE TABLE payments (
    payment_id      INTEGER PRIMARY KEY,
    account_code    VARCHAR(20) NOT NULL REFERENCES accounts(account_code),
    po_number       VARCHAR(50) NOT NULL,
    payment_amount  DECIMAL(12,2) NOT NULL,
    payment_date    DATE NOT NULL,
    payment_ref     VARCHAR(100)             -- e.g. check/remittance ID
);

-- One invoice's PO can have zero, one, or multiple payment rows
-- (multiple partial payments, or a duplicate/erroneous second payment).
CREATE INDEX idx_invoices_po   ON invoices(account_code, po_number);
CREATE INDEX idx_payments_po   ON payments(account_code, po_number);

-- Output of the matching engine — one row per invoice, its reconciled status.
CREATE TABLE reconciliation_report (
    invoice_id        INTEGER NOT NULL REFERENCES invoices(invoice_id),
    account_code      VARCHAR(20) NOT NULL,
    po_number         VARCHAR(50) NOT NULL,
    invoice_amount    DECIMAL(12,2) NOT NULL,
    total_paid        DECIMAL(12,2) NOT NULL DEFAULT 0,
    difference        DECIMAL(12,2) NOT NULL,   -- invoice_amount - total_paid
    status            VARCHAR(20) NOT NULL,      -- Paid / Unpaid / Short Pay / Overpaid / Duplicate
    payment_count     INTEGER NOT NULL DEFAULT 0
);
