-- Unapplied payments: payments whose (account_code, po_number) doesn't
-- match ANY invoice at all -- money that came in but was never claimed.
--
-- Uses NOT EXISTS (a correlated subquery) instead of a LEFT JOIN + IS NULL
-- here on purpose, to show the alternative pattern -- both approaches solve
-- "rows in A with no match in B", and it's worth being comfortable with
-- either one since interviewers ask for both.
SELECT p.*
FROM payments p
WHERE NOT EXISTS (
    SELECT 1
    FROM invoices i
    WHERE i.account_code = p.account_code
      AND i.po_number    = p.po_number
)
ORDER BY p.payment_id;
