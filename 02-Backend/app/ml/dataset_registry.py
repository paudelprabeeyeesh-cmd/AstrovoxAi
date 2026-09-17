import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class Dataset:
    name: str
    version: str
    location: str
    metadata: dict[str, Any] = field(default_factory=dict)
    lineage: list[str] = field(default_factory=list)


@dataclass
class ValidationResult:
    valid: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


class DatasetRegistry:
    def __init__(self) -> None:
        self._datasets: dict[str, dict[str, Dataset]] = {}

    def register_dataset(self, name: str, version: str, location: str, metadata: dict[str, Any] | None = None) -> Dataset:
        dataset = Dataset(name=name, version=version, location=location, metadata=metadata or {})
        self._datasets.setdefault(name, {})[version] = dataset
        logger.info(f"Registered dataset {name} version {version}")
        return dataset

    def get_dataset(self, name: str, version: str) -> Dataset | None:
        return self._datasets.get(name, {}).get(version)

    def list_datasets(self) -> list[Dataset]:
        datasets: list[Dataset] = []
        for versions in self._datasets.values():
            datasets.extend(versions.values())
        return datasets

    def validate_dataset(self, dataset: Dataset) -> ValidationResult:
        errors: list[str] = []
        warnings: list[str] = []

        if not dataset.name:
            errors.append("Dataset name is required")
        if not dataset.version:
            errors.append("Dataset version is required")
        if not dataset.location:
            errors.append("Dataset location is required")
        else:
            warnings.append("Dataset location should be verified for accessibility")

        return ValidationResult(valid=len(errors) == 0, errors=errors, warnings=warnings)
