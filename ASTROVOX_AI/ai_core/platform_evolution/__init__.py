"""Platform evolution for AI core."""
from .versioning import AIVersionManager, AIVersionPolicy
from .migration import AIMigrationEngine, AIMigrationPlan

__all__ = [
    "AIVersionManager",
    "AIVersionPolicy",
    "AIMigrationEngine",
    "AIMigrationPlan",
]
