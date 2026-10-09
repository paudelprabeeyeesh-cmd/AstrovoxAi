# Deployment Diagrams

## CI/CD Pipeline

```mermaid
flowchart LR
    A[Developer Push] --> B[GitHub Actions]
    B --> C[Lint & TypeCheck]
    C --> D[Security Scan]
    D --> E[Tests]
    E --> F[Build Images]
    F --> G{Push to main?}
    G -->|Yes| H[Deploy Staging]
    H --> I[Smoke Tests]
    I --> J{Tag v*?}
    J -->|Yes| K[Deploy Production]
    K --> L[Monitor]
```

## Staging Deployment

```mermaid
flowchart TB
    A[GitHub Actions] --> B[Build & Push Image]
    B --> C[EKS Staging Cluster]
    C --> D[Rollout Backend]
    C --> E[Rollout Frontend]
    D --> F[Smoke Tests]
    E --> F
    F --> G{Pass?}
    G -->|No| H[Rollback]
    G -->|Yes| I[Ready for QA]
```

## Production Deployment

```mermaid
flowchart TB
    A[Tag Release] --> B[GitHub Actions]
    B --> C[Build & Push Image]
    C --> D[EKS Prod Cluster]
    D --> E[Blue/Green Deploy]
    E --> F[Canary: 10%]
    F --> G{Metrics OK?}
    G -->|No| H[Rollback to Blue]
    G -->|Yes| I[Canary: 50%]
    I --> J{Metrics OK?}
    J -->|No| H
    J -->|Yes| K[Canary: 100%]
    K --> L[Switch to Green]
    L --> M[Monitor 24h]
```

## Helm Release Flow

```mermaid
flowchart LR
    A[helm upgrade] --> B[Render Manifests]
    B --> C[Apply to Cluster]
    C --> D[Wait for Rollout]
    D --> E{Success?}
    E -->|No| F[Rollback]
    E -->|Yes| G[Release Complete]
```

## Database Migration Flow

```mermaid
flowchart LR
    A[New Code] --> B{Alembic Migration?}
    B -->|Yes| C[Generate Migration]
    C --> D[Review SQL]
    D --> E[Run Migration]
    E --> F{Success?}
    F -->|No| G[Rollback Migration]
    F -->|Yes| H[Deploy Code]
```

## Backup Architecture

```mermaid
flowchart TB
    A[PostgreSQL] --> B[Continuous WAL Archiving]
    A --> C[Daily pg_dump]
    B --> D[S3/R2 Storage]
    C --> D
    D --> E[Cross-Region Replication]
    E --> F[Monthly Restore Test]
```

## Disaster Recovery Flow

```mermaid
flowchart TB
    A[Outage Detected] --> B[Assess Severity]
    B --> C{SEV-1?}
    C -->|Yes| D[Failover to DR Region]
    C -->|No| E[Restore from Backup]
    D --> F[Update DNS]
    E --> G[Verify Data Integrity]
    F --> H[Monitor Recovery]
    G --> H
```
