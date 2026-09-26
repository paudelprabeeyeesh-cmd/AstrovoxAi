import logging
import json
from dataclasses import dataclass
from typing import List, Optional

logger = logging.getLogger(__name__)


@dataclass
class DatasetVersionConfig:
    storage_path: str = "./datasets"
    auto_version: bool = True


class DatasetVersionManager:
    def __init__(self, config: Optional[DatasetVersionConfig] = None):
        self.config = config or DatasetVersionConfig()
        self.versions = {}
        logger.info("Dataset version manager initialized at %s", self.config.storage_path)

    def register(self, name: str, version: str, metadata: dict):
        key = f"{name}:{version}"
        self.versions[key] = metadata
        logger.info("Registered dataset %s version %s", name, version)

    def get(self, name: str, version: str) -> Optional[dict]:
        return self.versions.get(f"{name}:{version}")

    def list_versions(self, name: str) -> List[str]:
        return [k.split(":")[1] for k in self.versions if k.startswith(f"{name}:")]

    def save_manifest(self, path: str):
        with open(path, "w") as f:
            json.dump(self.versions, f, indent=2)
        logger.info("Manifest saved to %s", path)
