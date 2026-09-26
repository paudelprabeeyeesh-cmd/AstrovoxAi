"""Database package initialization."""

from backend.app.database.abstraction import (
    BaseDatabase,
    DatabaseConfig,
    DatabaseRegistry,
    DatabaseType,
    MultiDatabaseManager,
)
from backend.app.database.failover import FailoverController, FailoverConfig
from backend.app.database.replication import ReplicationManager, RegionConfig, RegionRole
from backend.app.database.read_write_split import ReadWriteSplitter, ReplicaConfig, RoutingStats
from backend.app.database.sharding import ShardManager, ShardRouter, ShardConfig
from backend.app.database.distributed_transactions import TwoPhaseCommitCoordinator, DistributedTransaction
from backend.app.database.schema_migration import MigrationStep, SchemaMigration
from backend.app.database.query_optimizer import QueryOptimizer
from backend.app.database.ai_indexing import AIIndexingEngine, IndexSuggestion
from backend.app.database.vector_optimization import VectorIndexOptimizer, VectorIndexConfig
from backend.app.database.hybrid_search import HybridSearchEngine, HybridQuery
from backend.app.database.backup_verification import BackupVerifier, BackupManifest
from backend.app.database.storage_lifecycle import StorageLifecycleManager, LifecyclePolicy, StorageObject, StorageTier
from backend.app.database.data_integrity import DataIntegrityManager, IntegrityCheck
from backend.app.database.dr_simulation import DRSimulation, SimulationScenario

__all__ = [
    "BaseDatabase",
    "DatabaseConfig",
    "DatabaseRegistry",
    "DatabaseType",
    "MultiDatabaseManager",
    "FailoverController",
    "FailoverConfig",
    "ReplicationManager",
    "RegionConfig",
    "RegionRole",
    "ReadWriteSplitter",
    "ReplicaConfig",
    "RoutingStats",
    "ShardManager",
    "ShardRouter",
    "ShardConfig",
    "TwoPhaseCommitCoordinator",
    "DistributedTransaction",
    "MigrationStep",
    "SchemaMigration",
    "QueryOptimizer",
    "AIIndexingEngine",
    "IndexSuggestion",
    "VectorIndexOptimizer",
    "VectorIndexConfig",
    "HybridSearchEngine",
    "HybridQuery",
    "BackupVerifier",
    "BackupManifest",
    "StorageLifecycleManager",
    "LifecyclePolicy",
    "StorageObject",
    "StorageTier",
    "DataIntegrityManager",
    "IntegrityCheck",
    "DRSimulation",
    "SimulationScenario",
]
