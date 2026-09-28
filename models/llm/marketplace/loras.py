import hashlib
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class LoRACompatibility(str, Enum):
    COMPATIBLE = "compatible"
    INCOMPATIBLE = "incompatible"
    UNKNOWN = "unknown"


@dataclass
class LoRAVersion:
    version_id: str
    lora_id: str
    version: str
    file_path: str
    file_size: int
    sha256: str
    base_model: str
    rank: int
    alpha: int
    target_modules: List[str]
    description: str
    uploaded_at: datetime = field(default_factory=datetime.utcnow)
    download_count: int = 0


@dataclass
class LoRAListing:
    lora_id: str
    name: str
    author_id: str
    description: str
    base_model: str
    tags: List[str] = field(default_factory=list)
    versions: Dict[str, LoRAVersion] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)


class LoRAMarketplace:
    def __init__(self, storage_dir: Optional[str] = None) -> None:
        self._storage_dir = Path(storage_dir) if storage_dir else Path(".marketplace/loras")
        self._storage_dir.mkdir(parents=True, exist_ok=True)
        self._loras: Dict[str, LoRAListing] = {}

    def upload_lora(
        self,
        name: str,
        author_id: str,
        description: str,
        version: str,
        file_path: str,
        base_model: str,
        rank: int,
        alpha: int,
        target_modules: List[str],
        tags: Optional[List[str]] = None,
    ) -> LoRAListing:
        lora_file = Path(file_path)
        if not lora_file.exists():
            raise FileNotFoundError(f"LoRA file not found: {file_path}")

        sha256 = hashlib.sha256()
        with open(lora_file, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                sha256.update(chunk)
        file_hash = sha256.hexdigest()

        lora_id = str(uuid.uuid4())
        version_id = str(uuid.uuid4())
        version_obj = LoRAVersion(
            version_id=version_id,
            lora_id=lora_id,
            version=version,
            file_path=str(lora_file),
            file_size=lora_file.stat().st_size,
            sha256=file_hash,
            base_model=base_model,
            rank=rank,
            alpha=alpha,
            target_modules=target_modules,
            description=description,
        )

        version_dir = self._storage_dir / lora_id / version
        version_dir.mkdir(parents=True, exist_ok=True)
        import shutil
        shutil.copy2(lora_file, version_dir / lora_file.name)
        version_obj.file_path = str(version_dir / lora_file.name)

        listing = LoRAListing(
            lora_id=lora_id,
            name=name,
            author_id=author_id,
            description=description,
            base_model=base_model,
            tags=tags or [],
            versions={version: version_obj},
        )

        self._loras[lora_id] = listing
        logger.info("Uploaded LoRA %s version %s", name, version)
        return listing

    def download_lora(self, lora_id: str, version: Optional[str] = None) -> LoRAVersion:
        if lora_id not in self._loras:
            raise KeyError(f"LoRA not found: {lora_id}")
        lora = self._loras[lora_id]
        versions = list(lora.versions.values())
        if not versions:
            raise ValueError("No versions available")
        selected = versions[-1]
        if version:
            selected = next((v for v in versions if v.version == version), selected)
        selected.download_count += 1
        return selected

    def check_compatibility(self, lora_id: str, target_model: str) -> LoRACompatibility:
        if lora_id not in self._loras:
            raise KeyError(f"LoRA not found: {lora_id}")
        lora = self._loras[lora_id]
        latest = list(lora.versions.values())[-1]
        if latest.base_model == target_model:
            return LoRACompatibility.COMPATIBLE
        return LoRACompatibility.INCOMPATIBLE

    def search_loras(
        self,
        query: str = "",
        base_model: Optional[str] = None,
        tags: Optional[List[str]] = None,
        author_id: Optional[str] = None,
        limit: int = 20,
    ) -> List[LoRAListing]:
        results = list(self._loras.values())
        if query:
            q = query.lower()
            results = [l for l in results if q in l.name.lower() or q in l.description.lower()]
        if base_model:
            results = [l for l in results if l.base_model == base_model]
        if tags:
            tag_set = set(tags)
            results = [l for l in results if tag_set.issubset(set(l.tags))]
        if author_id:
            results = [l for l in results if l.author_id == author_id]
        return results[:limit]

    def get_lora(self, lora_id: str) -> LoRAListing:
        if lora_id not in self._loras:
            raise KeyError(f"LoRA not found: {lora_id}")
        return self._loras[lora_id]

    def list_loras(self) -> List[LoRAListing]:
        return list(self._loras.values())
