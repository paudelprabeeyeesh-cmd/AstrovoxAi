# Migration Guides

## v1.x → v2.x

### Breaking Changes

#### Authentication

- **Before:** `/auth/login` returned `access_token` only.
- **After:** Returns `access_token` + `refresh_token`. Use `/auth/refresh` to renew.

#### Chat API

- **Before:** `/solve` endpoint for single-turn chat.
- **After:** `/chat/conversations` + `/chat/message` for multi-turn. `/solve` is deprecated.

#### Memory API

- **Before:** `/memory` with flat key-value store.
- **After:** `/memory/save` and `/memory/context` with typed memory (short_term, conversation, long_term, project).

#### Database

- **Before:** SQLite supported for development.
- **After:** PostgreSQL only. SQLite fallback removed.

#### Rate Limiting

- **Before:** No rate limiting on auth endpoints.
- **After:** `/register` and `/forgot-password` limited to 5 requests/hour per email.

### Migration Steps

1. Update environment variables:
   ```bash
   # Old
   DATABASE_URL=sqlite:///./astrovox.db
   
   # New
   DATABASE_URL=postgresql://astrovox:astrovox@localhost:5432/astrovox
   ```

2. Run database migrations:
   ```bash
   alembic upgrade head
   ```

3. Update API client calls:
   ```python
   # Old
   resp = client.post("/solve", json={"text": "Hello"})
   
   # New
   conv = client.post("/chat/conversations", json={"title": "Chat"}).json()
   conv_id = conv["conversation"]["id"]
   resp = client.post("/chat/message", json={
       "conversation_id": conv_id,
       "message": "Hello"
   })
   ```

4. Handle token refresh:
   ```python
   import time
   
   def get_valid_token(client):
       if time.time() > client.token_expiry:
           resp = client.post("/auth/refresh", json={
               "refresh_token": client.refresh_token
           })
           client.access_token = resp.json()["session"]["access_token"]
       return client.access_token
   ```

## v0.x → v1.x

### Summary

- Migrated from Flask to FastAPI
- Added async/await throughout
- Switched from SQLAlchemy to Supabase client
- Added pgvector for embeddings
- Introduced rate limiting and structured logging

### Steps

1. Update Python to 3.12
2. Install new dependencies: `pip install -r requirements.txt`
3. Run `alembic upgrade head`
4. Update client code to use new endpoint paths
5. Configure `ALLOWED_ORIGINS` for CORS

## Database Schema Migrations

### Adding new tables

```bash
# Generate migration
alembic revision --autogenerate -m "add new table"

# Review and edit migration file in alembic/versions/

# Apply
alembic upgrade head
```

### Rolling back

```bash
# Rollback one step
alembic downgrade -1

# Rollback to specific revision
alembic downgrade <revision_id>
```

## Model Version Migrations

### Upgrading LLM models

When upgrading from one model version to another:

1. Update `model` parameter in API calls
2. Test with 10% traffic before full rollout
3. Compare outputs for consistency
4. Update prompt templates if needed

### Deprecated models

| Deprecated | Replacement | Notes |
|------------|-------------|-------|
| `gpt-3.5-turbo` | `gpt-4o-mini` | Faster, cheaper, smarter |
| `claude-2` | `claude-3-5-sonnet` | Better reasoning |
| `gemini-pro` | `gemini-2.0-flash` | Multimodal support |
