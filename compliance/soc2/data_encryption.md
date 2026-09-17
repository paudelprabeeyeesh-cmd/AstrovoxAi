# Data Encryption Policy

## Purpose
Defines cryptographic controls for protecting data at rest, in transit, and in use, aligned with SOC 2 CC6.7 and CC6.1 criteria.

## Data Classification
- **Confidential**: Customer PII, credentials, API keys, LLM prompts/responses
- **Internal**: Internal documentation, metrics, non-sensitive configuration
- **Public**: Marketing materials, public API documentation

## Encryption at Rest
- **Databases**: PostgreSQL with pgcrypto extensions and disk-level encryption (AES-256).
- **Object Storage**: S3-compatible storage with server-side encryption (SSE-S3 or SSE-KMS).
- **Backups**: Database backups are encrypted using AES-256 before upload to offsite storage.
- **Secrets**: All secrets are stored in HashiCorp Vault or Kubernetes Secrets with encryption at rest.

## Encryption in Transit
- **External APIs**: TLS 1.3 with certificate pinning for all third-party integrations.
- **Internal Services**: mTLS between all Kubernetes services via service mesh (Istio/Linkerd).
- **Database Connections**: PostgreSQL and Redis connections require TLS or run within encrypted network segments.
- **Ingress**: TLS 1.3 termination at the ingress controller with HSTS enabled.

## Key Management
- Encryption keys are generated using FIPS 140-2 validated random number generators.
- Keys are rotated annually; data encryption keys (DEKs) are rotated quarterly.
- Key material is never hardcoded in source code or Docker images.
- Master keys are stored in a Hardware Security Module (HSM) or cloud KMS.

## Cryptographic Standards
- Symmetric: AES-256-GCM
- Asymmetric: RSA-4096 or ECDSA P-384
- Hashing: SHA-256 or SHA-3
- Key Derivation: PBKDF2 with >100,000 iterations or Argon2id
