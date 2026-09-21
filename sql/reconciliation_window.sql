-- The same classification as reconciliation_query.sql, written with window functions
-- instead of "GROUP BY in a CTE, then join".
--
-- GROUP BY collapses payments to one row per PO before the join. Here the join happens
-- first, and the window functions add the per-invoice totals to every row without
-- collapsing anything. ROW_NUMBER() then keeps one row per invoice. The advantage of
-- this shape: the individual payment rows are still available in the same query (for
-- example to test whether EACH payment equals the invoice amount) without a second pass.
--
--   COUNT(p.payment_id) OVER w   payments for this invoice (0 when unpaid)
--   SUM(p.payment_amount) OVER w total paid for this invoice
--   PARTITION BY i.invoice_id    "w" is one window per invoice

WITH joined AS (
    SELECT
        i.invoice_id,
        i.account_code,
        i.po_number,
        i.invoice_amount,
        COUNT(p.payment_id)   OVER w AS payment_count,
        SUM(p.payment_amount) OVER w AS total_paid,
        ROW_NUMBER() OVER (PARTITION BY i.invoice_id ORDER BY p.payment_id) AS rn
    FROM invoices i
    LEFT JOIN payments p
           ON p.account_code = i.account_code
          AND p.po_number    = i.po_number
    WINDOW w AS (PARTITION BY i.invoice_id)
)
SELECT
    invoice_id,
    account_code,
    po_number,
    invoice_amount,
    COALESCE(total_paid, 0)                              AS total_paid,
    ROUND(invoice_amount - COALESCE(total_paid, 0), 2)   AS difference,
    payment_count,
    CASE
        WHEN payment_count = 0
            THEN 'Unpaid'
        WHEN ABS(invoice_amount - total_paid) <= 0.01
            THEN 'Paid'
        WHEN invoice_amount - total_paid > 0.01
            THEN 'Short Pay'
        WHEN payment_count >= 2 AND (
                 ABS(total_paid - invoice_amount * 2) <= 0.01
              OR ABS(total_paid - invoice_amount * 3) <= 0.01
              OR ABS(total_paid - invoice_amount * 4) <= 0.01
             )
            THEN 'Duplicate'
        ELSE 'Overpaid'
    END AS status
FROM joined
WHERE rn = 1
ORDER BY invoice_id;
