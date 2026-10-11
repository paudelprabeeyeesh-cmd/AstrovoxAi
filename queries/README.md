# Saved SQL for local inspection.

Run any file below against the local development database from VS Code
(PostgreSQL / SQLTools extension) or psql.

Connection settings come from the environment; do not hardcode credentials.

```
psql "$DATABASE_URL" -f queries/conversations_by_user.sql
```
