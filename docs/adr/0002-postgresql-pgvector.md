# ADR-0002: Use PostgreSQL with pgvector

- **Status**: Accepted
- **Date**: 2026-09-17
- **Context**: AstrovoxAi requires persistent storage for chat sessions, embeddings, and semantic search capabilities.

## Decision
Use **PostgreSQL** as the primary datastore with the **pgvector** extension for vector similarity search.

## Rationale
- Relational integrity for sessions, users, and audit logs.
- pgvector enables efficient cosine and L2 distance queries on embeddings.
- Single database eliminates operational complexity of multi-store architectures.
- Mature replication and backup tooling.

## Consequences
- All embedding operations require normalized vectors for pgvector compatibility.
- Migration management must include pgvector extension setup (`CREATE EXTENSION vector`).
- High-vector-cardinality tables may require HNSW or IVFFlat indexing strategies.
