"""Backup and restore utilities for production deployment.

Provides:
- System state backup
- Restore from backup
- Disaster recovery
"""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class BackupMetadata:
    """Metadata for a backup."""
    backup_id: str
    timestamp: float
    version: str = "1.0.0"
    components: List[str] = field(default_factory=list)


class BackupManager:
    """Manages backups and restores."""
    
    def __init__(self, backup_dir: str = "./backups") -> None:
        self.backup_dir = backup_dir
        os.makedirs(backup_dir, exist_ok=True)
    
    def create_backup(self, state: Dict[str, Any], components: List[str]) -> BackupMetadata:
        """Create a backup of the system state."""
        backup_id = f"backup_{int(time.time())}_{os.urandom(4).hex()}"
        metadata = BackupMetadata(
            backup_id=backup_id,
            timestamp=time.time(),
            components=components
        )
        
        backup_path = os.path.join(self.backup_dir, f"{backup_id}.json")
        backup_data = {
            "metadata": {
                "backup_id": metadata.backup_id,
                "timestamp": metadata.timestamp,
                "version": metadata.version,
                "components": metadata.components
            },
            "state": state
        }
        
        with open(backup_path, "w") as f:
            json.dump(backup_data, f, indent=2, default=str)
        
        return metadata
    
    def restore_backup(self, backup_id: str) -> Optional[Dict[str, Any]]:
        """Restore from a backup."""
        backup_path = os.path.join(self.backup_dir, f"{backup_id}.json")
        if not os.path.exists(backup_path):
            return None
        
        with open(backup_path, "r") as f:
            backup_data = json.load(f)
        
        return backup_data.get("state")
    
    def list_backups(self) -> List[BackupMetadata]:
        """List all available backups."""
        backups = []
        for filename in os.listdir(self.backup_dir):
            if filename.endswith(".json"):
                filepath = os.path.join(self.backup_dir, filename)
                with open(filepath, "r") as f:
                    data = json.load(f)
                metadata_dict = data.get("metadata", {})
                backups.append(BackupMetadata(
                    backup_id=metadata_dict.get("backup_id", filename.replace(".json", "")),
                    timestamp=metadata_dict.get("timestamp", 0),
                    version=metadata_dict.get("version", "1.0.0"),
                    components=metadata_dict.get("components", [])
                ))
        return sorted(backups, key=lambda b: b.timestamp, reverse=True)
    
    def delete_backup(self, backup_id: str) -> bool:
        """Delete a backup."""
        backup_path = os.path.join(self.backup_dir, f"{backup_id}.json")
        if os.path.exists(backup_path):
            os.remove(backup_path)
            return True
        return False


# Global backup manager
_backup_manager: Optional[BackupManager] = None


def get_backup_manager() -> BackupManager:
    """Get global backup manager."""
    global _backup_manager
    if _backup_manager is None:
        _backup_manager = BackupManager()
    return _backup_manager