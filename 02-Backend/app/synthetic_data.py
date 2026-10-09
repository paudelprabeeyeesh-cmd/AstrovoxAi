"""Synthetic data pipeline."""

from __future__ import annotations

import hashlib
import json
import logging
import random
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class SyntheticDataset:
    dataset_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    schema: Dict[str, Any] = field(default_factory=dict)
    rows: List[Dict[str, Any]] = field(default_factory=list)
    source_dataset_id: Optional[str] = None
    generation_method: str = "template"
    created_at: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DataSchema:
    columns: List[Dict[str, Any]] = field(default_factory=list)
    constraints: Dict[str, Any] = field(default_factory=dict)


class SyntheticDataPipeline:
    """Synthetic data generation pipeline."""

    def __init__(self):
        self._datasets: Dict[str, SyntheticDataset] = {}
        self._schemas: Dict[str, DataSchema] = {}

    def register_schema(self, name: str, schema: DataSchema) -> None:
        self._schemas[name] = schema
        logger.info("Registered schema: %s", name)

    def generate(self, schema_name: str, num_rows: int = 100, seed: Optional[int] = None) -> SyntheticDataset:
        schema = self._schemas.get(schema_name)
        if not schema:
            raise ValueError(f"Schema {schema_name} not found")
        if seed is not None:
            random.seed(seed)
        rows = []
        for _ in range(num_rows):
            row = {}
            for col in schema.columns:
                col_name = col.get("name", "")
                col_type = col.get("type", "string")
                if col_type == "string":
                    row[col_name] = self._generate_string(col)
                elif col_type == "integer":
                    row[col_name] = random.randint(col.get("min", 0), col.get("max", 100))
                elif col_type == "float":
                    row[col_name] = round(random.uniform(col.get("min", 0.0), col.get("max", 1.0)), 2)
                elif col_type == "boolean":
                    row[col_name] = random.choice([True, False])
                elif col_type == "enum":
                    row[col_name] = random.choice(col.get("values", []))
                else:
                    row[col_name] = None
            rows.append(row)
        dataset = SyntheticDataset(name=schema_name, schema=schema.__dict__, rows=rows, generation_method="random")
        self._datasets[dataset.dataset_id] = dataset
        logger.info("Generated synthetic dataset %s with %d rows", dataset.dataset_id, num_rows)
        return dataset

    def anonymize(self, dataset_id: str, pii_columns: List[str]) -> Optional[SyntheticDataset]:
        dataset = self._datasets.get(dataset_id)
        if not dataset:
            return None
        anonymized_rows = []
        for row in dataset.rows:
            new_row = dict(row)
            for col in pii_columns:
                if col in new_row:
                    new_row[col] = hashlib.sha256(str(new_row[col]).encode()).hexdigest()[:16]
            anonymized_rows.append(new_row)
        new_dataset = SyntheticDataset(name=f"{dataset.name}_anonymized", schema=dataset.schema, rows=anonymized_rows, source_dataset_id=dataset_id, generation_method="anonymization")
        self._datasets[new_dataset.dataset_id] = new_dataset
        return new_dataset

    def get_dataset(self, dataset_id: str) -> Optional[SyntheticDataset]:
        return self._datasets.get(dataset_id)

    def _generate_string(self, col: Dict[str, Any]) -> str:
        min_len = col.get("min_length", 5)
        max_len = col.get("max_length", 20)
        length = random.randint(min_len, max_len)
        return "".join(random.choices("abcdefghijklmnopqrstuvwxyz", k=length))


synthetic_data_pipeline = SyntheticDataPipeline()
