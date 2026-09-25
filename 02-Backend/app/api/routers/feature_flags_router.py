"""Feature flag evaluation service and admin endpoint."""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


@dataclass
class FeatureFlag:
    key: str
    enabled: bool
    variants: Dict[str, Any] = field(default_factory=dict)
    rollout_percentage: int = 100
    rules: List[Dict[str, Any]] = field(default_factory=list)

    def evaluate(self, context: Dict[str, Any]) -> Any:
        if not self.enabled:
            return False
        for rule in self.rules:
            if _matches_rule(context, rule):
                return rule.get("value", True)
        if self.variants:
            bucket = _hash_context(context, self.key) % 100
            if bucket < self.rollout_percentage:
                variant_keys = list(self.variants.keys())
                if variant_keys:
                    idx = _hash_context(context, self.key + "v") % len(variant_keys)
                    return self.variants[variant_keys[idx]]
        return True


def _matches_rule(context: Dict[str, Any], rule: Dict[str, Any]) -> bool:
    for attr, expected in rule.get("where", {}).items():
        if context.get(attr) != expected:
            return False
    return True


def _hash_context(context: Dict[str, Any], salt: str) -> int:
    import hashlib
    raw = salt + json.dumps(context, sort_keys=True, default=str)
    return int(hashlib.md5(raw.encode()).hexdigest()[:8], 16)


@dataclass
class FeatureFlagStore:
    _flags: Dict[str, FeatureFlag] = field(default_factory=dict)

    def register(self, flag: FeatureFlag) -> None:
        self._flags[flag.key] = flag

    def is_enabled(self, key: str, context: Optional[Dict[str, Any]] = None) -> bool:
        flag = self._flags.get(key)
        if not flag:
            return False
        result = flag.evaluate(context or {})
        return bool(result)

    def get(self, key: str, context: Optional[Dict[str, Any]] = None) -> Any:
        flag = self._flags.get(key)
        if not flag:
            return None
        return flag.evaluate(context or {})

    def list_flags(self) -> List[Dict[str, Any]]:
        return [
            {
                "key": f.key,
                "enabled": f.enabled,
                "rollout_percentage": f.rollout_percentage,
                "rules": f.rules,
                "variants": list(f.variants.keys()),
            }
            for f in self._flags.values()
        ]


flag_store = FeatureFlagStore()


class EvaluateRequest(BaseModel):
    flags: List[str] = Field(..., min_length=1, max_length=100)
    context: Dict[str, Any] = Field(default_factory=dict)


class EvaluateResponse(BaseModel):
    values: Dict[str, Any]
    metadata: Dict[str, Any] = Field(default_factory=dict)


router = APIRouter(prefix="/api/feature-flags", tags=["feature-flags"])


@router.post("/evaluate", response_model=EvaluateResponse)
async def evaluate_flags(request: EvaluateRequest):
    values: Dict[str, Any] = {}
    for key in request.flags:
        values[key] = flag_store.get(key, request.context)
    return EvaluateResponse(values=values)


@router.get("/flags")
async def list_flags():
    return {"flags": flag_store.list_flags()}
