import hashlib
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class ModelLicense(str, Enum):
    MIT = "mit"
    APACHE_2 = "apache-2.0"
    GPL_3 = "gpl-3.0"
    CC_BY = "cc-by-4.0"
    CC_BY_NC = "cc-by-nc-4.0"
    PROPRIETARY = "proprietary"


class ModelVisibility(str, Enum):
    PUBLIC = "public"
    UNLISTED = "unlisted"
    PRIVATE = "private"


@dataclass
class ModelVersion:
    version_id: str
    model_id: str
    version: str
    file_path: str
    file_size: int
    sha256: str
    description: str
    license: ModelLicense
    tags: List[str] = field(default_factory=list)
    uploaded_at: datetime = field(default_factory=datetime.utcnow)
    download_count: int = 0


@dataclass
class ModelRating:
    rating_id: str
    model_id: str
    user_id: str
    score: int
    review: str
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class MarketplaceModel:
    model_id: str
    name: str
    author_id: str
    description: str
    visibility: ModelVisibility
    license: ModelLicense
    tags: List[str] = field(default_factory=list)
    versions: Dict[str, ModelVersion] = field(default_factory=dict)
    ratings: List[ModelRating] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)


class ModelMarketplace:
    def __init__(self, storage_dir: Optional[str] = None) -> None:
        self._storage_dir = Path(storage_dir) if storage_dir else Path(".marketplace/models")
        self._storage_dir.mkdir(parents=True, exist_ok=True)
        self._models: Dict[str, MarketplaceModel] = {}
        self._ratings: Dict[str, List[ModelRating]] = {}

    def upload_model(
        self,
        name: str,
        author_id: str,
        description: str,
        version: str,
        file_path: str,
        license: ModelLicense,
        visibility: ModelVisibility = ModelVisibility.PUBLIC,
        tags: Optional[List[str]] = None,
    ) -> MarketplaceModel:
        model_file = Path(file_path)
        if not model_file.exists():
            raise FileNotFoundError(f"Model file not found: {file_path}")

        sha256 = hashlib.sha256()
        with open(model_file, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                sha256.update(chunk)
        file_hash = sha256.hexdigest()

        version_id = str(uuid.uuid4())
        version_obj = ModelVersion(
            version_id=version_id,
            model_id="",
            version=version,
            file_path=str(model_file),
            file_size=model_file.stat().st_size,
            sha256=file_hash,
            description=description,
            license=license,
            tags=tags or [],
        )

        model_id = str(uuid.uuid4())
        version_obj.model_id = model_id
        version_dir = self._storage_dir / model_id / version
        version_dir.mkdir(parents=True, exist_ok=True)
        dest = version_dir / model_file.name
        import shutil
        shutil.copy2(model_file, dest)
        version_obj.file_path = str(dest)

        marketplace_model = MarketplaceModel(
            model_id=model_id,
            name=name,
            author_id=author_id,
            description=description,
            visibility=visibility,
            license=license,
            tags=tags or [],
            versions={version: version_obj},
        )

        self._models[model_id] = marketplace_model
        self._ratings[model_id] = []
        logger.info("Uploaded model %s version %s", name, version)
        return marketplace_model

    def download_model(self, model_id: str, version: Optional[str] = None) -> ModelVersion:
        if model_id not in self._models:
            raise KeyError(f"Model not found: {model_id}")
        model = self._models[model_id]
        versions = list(model.versions.values())
        if not versions:
            raise ValueError("No versions available")
        selected = versions[-1]
        if version:
            selected = next((v for v in versions if v.version == version), selected)
        selected.download_count += 1
        return selected

    def add_version(
        self,
        model_id: str,
        version: str,
        file_path: str,
        description: str,
    ) -> ModelVersion:
        if model_id not in self._models:
            raise KeyError(f"Model not found: {model_id}")
        model = self._models[model_id]
        model_file = Path(file_path)
        if not model_file.exists():
            raise FileNotFoundError(f"Model file not found: {file_path}")

        sha256 = hashlib.sha256()
        with open(model_file, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                sha256.update(chunk)
        file_hash = sha256.hexdigest()

        version_id = str(uuid.uuid4())
        version_obj = ModelVersion(
            version_id=version_id,
            model_id=model_id,
            version=version,
            file_path=str(model_file),
            file_size=model_file.stat().st_size,
            sha256=file_hash,
            description=description,
            license=model.license,
            tags=model.tags,
        )

        version_dir = self._storage_dir / model_id / version
        version_dir.mkdir(parents=True, exist_ok=True)
        dest = version_dir / model_file.name
        import shutil
        shutil.copy2(model_file, dest)
        version_obj.file_path = str(dest)

        model.versions[version] = version_obj
        model.updated_at = datetime.utcnow()
        logger.info("Added version %s to model %s", version, model_id)
        return version_obj

    def rate_model(self, model_id: str, user_id: str, score: int, review: str = "") -> ModelRating:
        if model_id not in self._models:
            raise KeyError(f"Model not found: {model_id}")
        if score < 1 or score > 5:
            raise ValueError("Score must be between 1 and 5")
        rating = ModelRating(
            rating_id=str(uuid.uuid4()),
            model_id=model_id,
            user_id=user_id,
            score=score,
            review=review,
        )
        self._ratings[model_id].append(rating)
        self._models[model_id].ratings = self._ratings[model_id]
        logger.info("Rated model %s with score %d", model_id, score)
        return rating

    def search_models(
        self,
        query: str = "",
        tags: Optional[List[str]] = None,
        author_id: Optional[str] = None,
        min_rating: Optional[float] = None,
        limit: int = 20,
    ) -> List[MarketplaceModel]:
        results = list(self._models.values())
        if query:
            q = query.lower()
            results = [m for m in results if q in m.name.lower() or q in m.description.lower()]
        if tags:
            tag_set = set(tags)
            results = [m for m in results if tag_set.issubset(set(m.tags))]
        if author_id:
            results = [m for m in results if m.author_id == author_id]
        if min_rating is not None:
            filtered = []
            for m in results:
                ratings = self._ratings.get(m.model_id, [])
                if ratings:
                    avg = sum(r.score for r in ratings) / len(ratings)
                    if avg >= min_rating:
                        filtered.append(m)
            results = filtered
        return results[:limit]

    def get_model(self, model_id: str) -> MarketplaceModel:
        if model_id not in self._models:
            raise KeyError(f"Model not found: {model_id}")
        return self._models[model_id]

    def list_models(self) -> List[MarketplaceModel]:
        return list(self._models.values())
