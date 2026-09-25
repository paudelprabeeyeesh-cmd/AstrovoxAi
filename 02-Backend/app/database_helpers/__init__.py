"""Database helpers package.

Provides high-value data-layer utilities:
- Migration runner
- Seed data loader
- Connection pool health checks
- Query timeout enforcement
- Read replica routing
- Transaction retry helper
- Soft delete mixin
- Audit columns mixin
- Full-text search helper
- JSON path query helper
- Batch upsert helper
- Data encryption at rest helper
- Backup manifest generator
- Restore smoke test
- Schema drift detector
"""

from app.database_helpers.migrations import MigrationRunner
from app.database_helpers.seeds import SeedLoader, SeedResult
from app.database_helpers.pool import PoolHealth, PoolHealthCheck
from app.database_helpers.query_timeout import QueryTimeout, QueryTimeoutManager
from app.database_helpers.replica import ReplicaRouter
from app.database_helpers.retry import TransactionRetry
from app.database_helpers.mixins import AuditColumnsMixin, SoftDeleteMixin
from app.database_helpers.search import FullTextSearch, SearchResult
from app.database_helpers.json import JsonPathResult, JsonQuery
from app.database_helpers.batch import BatchUpsert
from app.database_helpers.encryption import EncryptionEngine, EncryptionError
from app.database_helpers.backup import BackupManifest, BackupManifestGenerator
from app.database_helpers.smoke import RestoreSmokeTest, SmokeResult
from app.database_helpers.drift import ColumnDiff, DriftReport, SchemaDriftDetector

__all__ = [
    "MigrationRunner",
    "SeedLoader",
    "SeedResult",
    "PoolHealth",
    "PoolHealthCheck",
    "QueryTimeout",
    "QueryTimeoutManager",
    "ReplicaRouter",
    "TransactionRetry",
    "SoftDeleteMixin",
    "AuditColumnsMixin",
    "FullTextSearch",
    "SearchResult",
    "JsonQuery",
    "JsonPathResult",
    "BatchUpsert",
    "EncryptionEngine",
    "EncryptionError",
    "BackupManifest",
    "BackupManifestGenerator",
    "RestoreSmokeTest",
    "SmokeResult",
    "ColumnDiff",
    "DriftReport",
    "SchemaDriftDetector",
]
