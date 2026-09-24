# Database Design

## Overview

AstrovoxAI uses PostgreSQL with pgvector for embeddings and Redis for caching.

## Entity Relationship Diagram

```mermaid
erDiagram
    users ||--o{ conversations : owns
    users ||--o{ memories : has
    users ||--o{ messages : sends
    conversations ||--o{ messages : contains
    conversations ||--o{ embeddings : references
    messages ||--o{ embeddings : generates
    
    users {
        uuid id PK
        string email UK
        string full_name
        boolean email_verified
        timestamp created_at
        timestamp updated_at
    }
    
    conversations {
        uuid id PK
        uuid user_id FK
        string title
        string model
        boolean pinned
        boolean archived
        string folder
        timestamp created_at
        timestamp updated_at
    }
    
    messages {
        uuid id PK
        uuid conversation_id FK
        uuid user_id FK
        string role
        text content
        string model_used
        integer tokens_used
        timestamp created_at
    }
    
    memories {
        uuid id PK
        uuid user_id FK
        string key
        text value
        string memory_type
        float importance_score
        vector embedding
        timestamp created_at
    }
    
    embeddings {
        uuid id PK
        uuid source_id FK
        string source_type
        text content
        vector embedding
        integer dimension
        timestamp created_at
    }
```

## Table Specifications

### users

Primary user table. Created via Supabase Auth.

| Column | Type | Constraints |
|--------|------|-------------|
| id | uuid | PRIMARY KEY |
| email | varchar(255) | UNIQUE, NOT NULL |
| full_name | varchar(255) | NULLABLE |
| email_verified | boolean | DEFAULT false |
| created_at | timestamp | DEFAULT now() |
| updated_at | timestamp | DEFAULT now() |

**Indexes:**
- `idx_users_email` on `email`

---

### conversations

Chat conversations linked to users.

| Column | Type | Constraints |
|--------|------|-------------|
| id | uuid | PRIMARY KEY |
| user_id | uuid | FK -> users.id |
| title | varchar(200) | NULLABLE |
| model | varchar(50) | DEFAULT 'gpt-4' |
| pinned | boolean | DEFAULT false |
| archived | boolean | DEFAULT false |
| folder | varchar(100) | NULLABLE |
| created_at | timestamp | DEFAULT now() |
| updated_at | timestamp | DEFAULT now() |

**Indexes:**
- `idx_conversations_user_id` on `user_id`
- `idx_conversations_updated_at` on `(user_id, updated_at DESC)`

---

### messages

Individual messages within conversations.

| Column | Type | Constraints |
|--------|------|-------------|
| id | uuid | PRIMARY KEY |
| conversation_id | uuid | FK -> conversations.id |
| user_id | uuid | FK -> users.id |
| role | varchar(20) | CHECK (role IN ('user', 'assistant', 'system')) |
| content | text | NOT NULL |
| model_used | varchar(50) | NULLABLE |
| tokens_used | integer | NULLABLE |
| created_at | timestamp | DEFAULT now() |

**Indexes:**
- `idx_messages_conversation_id` on `conversation_id`
- `idx_messages_created_at` on `(conversation_id, created_at ASC)`

---

### memories

User memory entries with vector embeddings.

| Column | Type | Constraints |
|--------|------|-------------|
| id | uuid | PRIMARY KEY |
| user_id | uuid | FK -> users.id |
| key | varchar(200) | NOT NULL |
| value | text | NOT NULL |
| memory_type | varchar(20) | DEFAULT 'conversation' |
| importance_score | float | DEFAULT 0.5 |
| embedding | vector(1536) | NULLABLE |
| created_at | timestamp | DEFAULT now() |

**Indexes:**
- `idx_memories_user_id` on `user_id`
- `idx_memories_embedding` on `embedding` (ivfflat, cosine)

---

### embeddings

Document and message embeddings for RAG.

| Column | Type | Constraints |
|--------|------|-------------|
| id | uuid | PRIMARY KEY |
| source_id | uuid | NOT NULL |
| source_type | varchar(50) | NOT NULL |
| content | text | NOT NULL |
| embedding | vector(1536) | NOT NULL |
| dimension | integer | DEFAULT 1536 |
| created_at | timestamp | DEFAULT now() |

**Indexes:**
- `idx_embeddings_source` on `(source_type, source_id)`
- `idx_embeddings_embedding` on `embedding` (ivfflat, cosine)

---

### audit_logs

Immutable audit trail for compliance.

| Column | Type | Constraints |
|--------|------|-------------|
| id | uuid | PRIMARY KEY |
| user_id | uuid | FK -> users.id |
| action | varchar(100) | NOT NULL |
| resource_type | varchar(50) | NOT NULL |
| resource_id | uuid | NULLABLE |
| metadata | jsonb | NULLABLE |
| ip_address | inet | NULLABLE |
| user_agent | text | NULLABLE |
| created_at | timestamp | DEFAULT now() |

**Constraints:**
- No UPDATE or DELETE allowed (append-only)
- Partitioned by month for performance

---

## Database Configuration

### Connection Pool

```python
# 02-Backend/app/database.py
DATABASE_URL = "postgresql://astrovox:astrovox@localhost:5432/astrovox"
```

### pgvector Setup

```sql
CREATE EXTENSION IF NOT EXISTS vector;

-- For approximate nearest neighbor search
CREATE INDEX IF NOT EXISTS idx_memories_embedding 
  ON memories USING ivfflat (embedding vector_cosine_ops) 
  WITH (lists = 100);
```

### Query Patterns

#### Paginated Conversation List

```sql
SELECT * FROM conversations
WHERE user_id = $1 AND is_deleted = false
ORDER BY updated_at DESC
LIMIT $2 OFFSET $3;
```

#### Semantic Memory Search

```sql
SELECT id, key, value, importance_score,
       1 - (embedding <=> $1) AS similarity
FROM memories
WHERE user_id = $2
ORDER BY embedding <=> $1
LIMIT 10;
```

## Migrations

```bash
# Generate migration
alembic revision --autogenerate -m "add memories table"

# Apply
alembic upgrade head

# Rollback
alembic downgrade -1
```

## Backup & Restore

```bash
# Backup
pg_dump -U astrovox -d astrovox -F c -f backup.dump

# Restore
pg_restore -U astrovox -d astrovox -c backup.dump
```

## Performance Tuning

| Parameter | Recommendation |
|-----------|----------------|
| `shared_buffers` | 25% of RAM |
| `effective_cache_size` | 75% of RAM |
| `maintenance_work_mem` | 256MB |
| `work_mem` | 16MB |
| `max_connections` | 100 |
