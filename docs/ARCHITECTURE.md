# ARCHITECTURE

This document provides a high-level overview of AstrovoxAI architecture: frontend (JavaScript), backend (Python), database (Postgres + PL/pgSQL), AI layer (external models via API), embeddings store (vector DB), and infra components (logging, monitoring, backups).

Components:
- Frontend: React / Astro (JS)
- Backend: Python services (FastAPI / Flask)
- Database: PostgreSQL with PL/pgSQL functions
- Vector DB: Chroma / Qdrant / Supabase Vector (TBD)
- CI/CD: GitHub Actions

See individual docs for details.
