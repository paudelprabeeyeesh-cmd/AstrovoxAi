import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class DatasetLicense(str, Enum):
    MIT = "mit"
    APACHE_2 = "apache-2.0"
    GPL_3 = "gpl-3.0"
    CC_BY = "cc-by-4.0"
    CC_BY_NC = "cc-by-nc-4.0"
    ODC_BY = "odc-by-1.0"
    PROPRIETARY = "proprietary"


class DatasetVisibility(str, Enum):
    PUBLIC = "public"
    UNLISTED = "unlisted"
    PRIVATE = "private"


@dataclass
class DatasetQualityScore:
    overall: float
    completeness: float
    consistency: float
    accuracy: float
    diversity: float
    noise_ratio: float
    evaluated_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class DatasetVersion:
    version_id: str
    dataset_id: str
    version: str
    file_path: str
    file_size: int
    format: str
    description: str
    license: DatasetLicense
    quality_score: Optional[DatasetQualityScore] = None
    uploaded_at: datetime = field(default_factory=datetime.utcnow)
    download_count: int = 0


@dataclass
class DatasetListing:
    dataset_id: str
    name: str
    author_id: str
    description: str
    visibility: DatasetVisibility
    license: DatasetLicense
    tags: List[str] = field(default_factory=list)
    versions: Dict[str, DatasetVersion] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)


class DatasetMarketplace:
    def __init__(self, storage_dir: Optional[str] = None) -> None:
        self._storage_dir = Path(storage_dir) if storage_dir else Path(".marketplace/datasets")
        self._storage_dir.mkdir(parents=True, exist_ok=True)
        self._datasets: Dict[str, DatasetListing] = {}

    def upload_dataset(
        self,
        name: str,
        author_id: str,
        description: str,
        version: str,
        file_path: str,
        license: DatasetLicense,
        format: str = "jsonl",
        visibility: DatasetVisibility = DatasetVisibility.PUBLIC,
        tags: Optional[List[str]] = None,
    ) -> DatasetListing:
        dataset_file = Path(file_path)
        if not dataset_file.exists():
            raise FileNotFoundError(f"Dataset file not found: {file_path}")

        dataset_id = str(uuid.uuid4())
        version_id = str(uuid.uuid4())
        version_obj = DatasetVersion(
            version_id=version_id,
            dataset_id=dataset_id,
            version=version,
            file_path=str(dataset_file),
            file_size=dataset_file.stat().st_size,
            format=format,
            description=description,
            license=license,
        )

        listing = DatasetListing(
            dataset_id=dataset_id,
            name=name,
            author_id=author_id,
            description=description,
            visibility=visibility,
            license=license,
            tags=tags or [],
            versions={version: version_obj},
        )

        self._datasets[dataset_id] = listing
        logger.info("Uploaded dataset %s version %s", name, version)
        return listing

    def add_version(
        self,
        dataset_id: str,
        version: str,
        file_path: str,
        description: str,
        format: str,
    ) -> DatasetVersion:
        if dataset_id not in self._datasets:
            raise KeyError(f"Dataset not found: {dataset_id}")
        dataset = self._datasets[dataset_id]
        dataset_file = Path(file_path)
        if not dataset_file.exists():
            raise FileNotFoundError(f"Dataset file not found: {file_path}")

        version_id = str(uuid.uuid4())
        version_obj = DatasetVersion(
            version_id=version_id,
            dataset_id=dataset_id,
            version=version,
            file_path=str(dataset_file),
            file_size=dataset_file.stat().st_size,
            format=format,
            description=description,
            license=dataset.license,
        )

        version_dir = self._storage_dir / dataset_id / version
        version_dir.mkdir(parents=True, exist_ok=True)
        import shutil
        shutil.copy2(dataset_file, version_dir / dataset_file.name)
        version_obj.file_path = str(version_dir / dataset_file.name)

        dataset.versions[version] = version_obj
        dataset.updated_at = datetime.utcnow()
        logger.info("Added version %s to dataset %s", version, dataset_id)
        return version_obj

    def set_quality_score(
        self,
        dataset_id: str,
        version: str,
        overall: float,
        completeness: float,
        consistency: float,
        accuracy: float,
        diversity: float,
        noise_ratio: float,
    ) -> DatasetQualityScore:
        if dataset_id not in self._datasets:
            raise KeyError(f"Dataset not found: {dataset_id}")
        dataset = self._datasets[dataset_id]
        if version not in dataset.versions:
            raise KeyError(f"Version not found: {dataset_id}:{version}")
        score = DatasetQualityScore(
            overall=overall,
            completeness=completeness,
            consistency=consistency,
            accuracy=accuracy,
            diversity=diversity,
            noise_ratio=noise_ratio,
        )
        dataset.versions[version].quality_score = score
        logger.info("Set quality score for dataset %s version %s", dataset_id, version)
        return score

    def search_datasets(
        self,
        query: str = "",
        tags: Optional[List[str]] = None,
        author_id: Optional[str] = None,
        min_quality: Optional[float] = None,
        limit: int = 20,
    ) -> List[DatasetListing]:
        results = list(self._datasets.values())
        if query:
            q = query.lower()
            results = [d for d in results if q in d.name.lower() or q in d.description.lower()]
        if tags:
            tag_set = set(tags)
            results = [d for d in results if tag_set.issubset(set(d.tags))]
        if author_id:
            results = [d for d in results if d.author_id == author_id]
        if min_quality is not None:
            filtered = []
            for d in results:
                for v in d.versions.values():
                    if v.quality_score and v.quality_score.overall >= min_quality:
                        filtered.append(d)
                        break
            results = filtered
        return results[:limit]

    def get_dataset(self, dataset_id: str) -> DatasetListing:
        if dataset_id not in self._datasets:
            raise KeyError(f"Dataset not found: {dataset_id}")
        return self._datasets[dataset_id]

    def list_datasets(self) -> List[DatasetListing]:
        return list(self._datasets.values())
