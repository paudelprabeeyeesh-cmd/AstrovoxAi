"""Platform evolution package initialization."""
from .versioning import VersionManager, VersionPolicy
from .migration import MigrationEngine, MigrationPlan
from .deprecation import DeprecationManager, DeprecationNotice

__all__ = [
    "VersionManager",
    "VersionPolicy",
    "MigrationEngine",
    "MigrationPlan",
    "DeprecationManager",
    "DeprecationNotice",
]
