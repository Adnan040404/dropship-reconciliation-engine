-- Reconciliation query: matches invoices to payments and classifies each
-- invoice's status, entirely in SQL (this replaces src/match_engine.py's
-- pandas logic for the SQL-backed version of the engine).

-- Step 1 (CTE): aggregate payments per (account_code, po_number) FIRST,
-- before joining -- this avoids double-counting an invoice's amount if it
-- has multiple payment rows (e.g. a duplicate payment or a partial payment
-- followed by a top-up).
WITH payment_totals AS (
    SELECT
        account_code,
        po_number,
        SUM(payment_amount) AS total_paid,
        COUNT(*)            AS payment_count
    FROM payments
    GROUP BY account_code, po_number
)

-- Step 2: LEFT JOIN invoices to the aggregated payment totals -- LEFT JOIN
-- (not INNER) so invoices with ZERO payments still appear, with NULL
-- total_paid, which we then treat as 0 via COALESCE.
SELECT
    i.invoice_id,
    i.account_code,
    i.po_number,
    i.invoice_amount,
    COALESCE(pt.total_paid, 0)                                   AS total_paid,
    ROUND(i.invoice_amount - COALESCE(pt.total_paid, 0), 2)      AS difference,
    COALESCE(pt.payment_count, 0)                                AS payment_count,

    -- Step 3 (CASE WHEN): classify each invoice. CASE WHEN evaluates each
    -- condition top-to-bottom and stops at the FIRST match -- order matters.
    CASE
        WHEN COALESCE(pt.payment_count, 0) = 0
            THEN 'Unpaid'
        WHEN ABS(i.invoice_amount - pt.total_paid) <= 0.01
            THEN 'Paid'
        WHEN i.invoice_amount - pt.total_paid > 0.01
            THEN 'Short Pay'
        WHEN pt.payment_count >= 2 AND (
                 ABS(pt.total_paid - i.invoice_amount * 2) <= 0.01
              OR ABS(pt.total_paid - i.invoice_amount * 3) <= 0.01
              OR ABS(pt.total_paid - i.invoice_amount * 4) <= 0.01
             )
            THEN 'Duplicate'
        ELSE 'Overpaid'
    END AS status

FROM invoices i
LEFT JOIN payment_totals pt
    ON i.account_code = pt.account_code
   AND i.po_number    = pt.po_number
ORDER BY i.invoice_id;
