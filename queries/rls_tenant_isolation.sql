-- Verify row-level security is enforced: run as two different roles.
-- The second query must return zero rows when the owner is a different user.
-- Use `SET LOCAL role` in a transaction to emulate another tenant.

SET ROLE authenticated;

-- 1. Rows visible to the current user.
SELECT count(*) AS visible_rows FROM conversations;

-- 2. Explicitly request another tenant's rows (must be 0).
SELECT count(*) AS leaked_rows
FROM conversations
WHERE user_id <> current_setting('request.jwt.claim.sub', true)::uuid;
