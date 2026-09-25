"""System prompt versioning with A/B testing and rollback support."""

from __future__ import annotations

import json
import logging
import os
import re
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

from app.repositories.database.client import get_db

from .prompt_validation import PromptTemplateValidator, PromptValidationResult

logger = logging.getLogger(__name__)


@dataclass
class PromptVersion:
    id: str
    name: str
    template: str
    version: str
    description: str
    created_at: str
    is_active: bool = True
    metadata: dict = field(default_factory=dict)
    validation_errors: list[str] = field(default_factory=list)


class PromptVersionManager:
    def __init__(self):
        self.prompts_dir = "app/prompts"
        os.makedirs(self.prompts_dir, exist_ok=True)
        self._validator = PromptTemplateValidator()
        self._ab_tests: dict[str, dict[str, Any]] = {}

    def create_prompt(
        self,
        name: str,
        template: str,
        version: str,
        description: str,
        metadata: Optional[dict[str, Any]] = None,
    ) -> PromptVersion:
        validation = self._validator.validate(template)
        prompt_id = str(uuid.uuid4())
        created_at = datetime.now(timezone.utc).isoformat()
        meta = metadata or {}
        meta.update({
            "validation_valid": validation.valid,
            "validation_errors": [e.message for e in validation.errors],
            "validation_warnings": [w.message for w in validation.warnings],
        })
        with get_db() as conn:
            conn.execute(
                """INSERT INTO prompt_versions (id, name, template, version, description, created_at, metadata)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (prompt_id, name, template, version, description, created_at, json.dumps(meta)),
            )
            conn.commit()
        return PromptVersion(
            id=prompt_id,
            name=name,
            template=template,
            version=version,
            description=description,
            created_at=created_at,
            metadata=meta,
            validation_errors=[e.message for e in validation.errors],
        )

    def get_prompt(self, name: str, version: Optional[str] = None) -> Optional[PromptVersion]:
        with get_db() as conn:
            if version:
                row = conn.execute(
                    """SELECT id, name, template, version, description, created_at, metadata
                       FROM prompt_versions WHERE name = ? AND version = ?""",
                    (name, version),
                ).fetchone()
            else:
                row = conn.execute(
                    """SELECT id, name, template, version, description, created_at, metadata
                       FROM prompt_versions WHERE name = ? ORDER BY created_at DESC LIMIT 1""",
                    (name,),
                ).fetchone()
        if not row:
            return None
        meta = json.loads(row["metadata"] or "{}")
        return PromptVersion(
            id=row["id"],
            name=row["name"],
            template=row["template"],
            version=row["version"],
            description=row["description"],
            created_at=row["created_at"],
            metadata=meta,
            validation_errors=meta.get("validation_errors", []),
        )

    def list_versions(self, name: str) -> list[PromptVersion]:
        with get_db() as conn:
            rows = conn.execute(
                """SELECT id, name, template, version, description, created_at, metadata
                   FROM prompt_versions WHERE name = ? ORDER BY created_at DESC""",
                (name,),
            ).fetchall()
        return [
            PromptVersion(
                id=r["id"],
                name=r["name"],
                template=r["template"],
                version=r["version"],
                description=r["description"],
                created_at=r["created_at"],
                metadata=json.loads(r["metadata"] or "{}"),
            )
            for r in rows
        ]

    def list_prompts(self) -> list:
        with get_db() as conn:
            rows = conn.execute(
                """SELECT DISTINCT name FROM prompt_versions ORDER BY name ASC"""
            ).fetchall()
            return [r["name"] for r in rows]

    def compare_versions(self, name: str, v1: str, v2: str) -> dict:
        prompt1 = self.get_prompt(name, v1)
        prompt2 = self.get_prompt(name, v2)
        if not prompt1 or not prompt2:
            raise ValueError("Prompt version not found")
        return {
            "name": name,
            "version_1": v1,
            "version_2": v2,
            "template_1": prompt1.template,
            "template_2": prompt2.template,
            "description_1": prompt1.description,
            "description_2": prompt2.description,
            "metadata_1": prompt1.metadata,
            "metadata_2": prompt2.metadata,
        }

    def rollback_prompt(self, name: str, version: str) -> PromptVersion:
        target = self.get_prompt(name, version)
        if not target:
            raise ValueError("Prompt version not found")
        new_version = f"{version}_rollback_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
        return self.create_prompt(name, target.template, new_version, f"Rollback to {version}", metadata=target.metadata)

    def create_ab_test(self, name: str, variant_a: str, variant_b: str, traffic_split: float = 0.5) -> dict:
        test_id = str(uuid.uuid4())
        self._ab_tests[test_id] = {
            "name": name,
            "variant_a": variant_a,
            "variant_b": variant_b,
            "traffic_split": traffic_split,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "results": {"a": 0, "b": 0},
        }
        return {"test_id": test_id, **self._ab_tests[test_id]}

    def get_ab_variant(self, test_id: str, user_id: str) -> Optional[str]:
        test = self._ab_tests.get(test_id)
        if not test:
            return None
        if hash(f"{test_id}:{user_id}") % 100 < int(test["traffic_split"] * 100):
            return test["variant_a"]
        return test["variant_b"]

    def record_ab_result(self, test_id: str, variant: str) -> None:
        test = self._ab_tests.get(test_id)
        if test and variant in test["results"]:
            test["results"][variant] += 1
