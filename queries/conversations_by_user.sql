-- Conversations for one user, newest first.
-- Bind: :user_id (uuid)
-- Expected index: (user_id, updated_at DESC) on conversations.

SELECT
  c.id,
  c.title,
  c.created_at,
  c.updated_at,
  COUNT(m.id) AS message_count
FROM conversations AS c
LEFT JOIN messages AS m
  ON m.conversation_id = c.id
WHERE c.user_id = :'user_id'::uuid
GROUP BY c.id, c.title, c.created_at, c.updated_at
ORDER BY c.updated_at DESC
LIMIT 50;
