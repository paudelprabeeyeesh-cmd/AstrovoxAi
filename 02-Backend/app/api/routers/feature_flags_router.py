"""Feature flag evaluation service and admin endpoints."""

from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
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
    description: str = ""
    tags: List[str] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

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

    def to_dict(self) -> Dict[str, Any]:
        return {
            "key": self.key,
            "enabled": self.enabled,
            "variants": self.variants,
            "rollout_percentage": self.rollout_percentage,
            "rules": self.rules,
            "description": self.description,
            "tags": self.tags,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


def _matches_rule(context: Dict[str, Any], rule: Dict[str, Any]) -> bool:
    for attr, expected in rule.get("where", {}).items():
        if context.get(attr) != expected:
            return False
    return True


def _hash_context(context: Dict[str, Any], salt: str) -> int:
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
        return [f.to_dict() for f in self._flags.values()]

    def get_flag(self, key: str) -> Optional[FeatureFlag]:
        return self._flags.get(key)

    def delete_flag(self, key: str) -> bool:
        return self._flags.pop(key, None) is not None

    def update_flag(self, key: str, **updates: Any) -> Optional[FeatureFlag]:
        flag = self._flags.get(key)
        if not flag:
            return None
        for attr, value in updates.items():
            if hasattr(flag, attr):
                setattr(flag, attr, value)
        flag.updated_at = datetime.now(timezone.utc).isoformat()
        return flag


flag_store = FeatureFlagStore()


class EvaluateRequest(BaseModel):
    flags: List[str] = Field(..., min_length=1, max_length=100)
    context: Dict[str, Any] = Field(default_factory=dict)


class EvaluateResponse(BaseModel):
    values: Dict[str, Any]
    metadata: Dict[str, Any] = Field(default_factory=dict)


class CreateFlagRequest(BaseModel):
    key: str
    enabled: bool = True
    variants: Dict[str, Any] = Field(default_factory=dict)
    rollout_percentage: int = Field(default=100, ge=0, le=100)
    rules: List[Dict[str, Any]] = Field(default_factory=list)
    description: str = ""
    tags: List[str] = Field(default_factory=list)


class UpdateFlagRequest(BaseModel):
    enabled: Optional[bool] = None
    variants: Optional[Dict[str, Any]] = None
    rollout_percentage: Optional[int] = Field(default=None, ge=0, le=100)
    rules: Optional[List[Dict[str, Any]]] = None
    description: Optional[str] = None
    tags: Optional[List[str]] = None


class FlagResponse(BaseModel):
    key: str
    enabled: bool
    variants: Dict[str, Any]
    rollout_percentage: int
    rules: List[Dict[str, Any]]
    description: str
    tags: List[str]
    created_at: str
    updated_at: str


router = APIRouter(prefix="/api/feature-flags", tags=["feature-flags"])


@router.post("/evaluate", response_model=EvaluateResponse)
async def evaluate_flags(request: EvaluateRequest):
    values: Dict[str, Any] = {}
    for key in request.flags:
        values[key] = flag_store.get(key, request.context)
    return EvaluateResponse(values=values)


@router.get("/flags", response_model=List[FlagResponse])
async def list_flags():
    return [FlagResponse(**f) for f in flag_store.list_flags()]


@router.get("/flags/{key}", response_model=FlagResponse)
async def get_flag(key: str):
    flag = flag_store.get_flag(key)
    if not flag:
        raise HTTPException(status_code=404, detail="Feature flag not found")
    return FlagResponse(**flag.to_dict())


@router.post("/flags", response_model=FlagResponse)
async def create_flag(request: CreateFlagRequest):
    if flag_store.get_flag(request.key):
        raise HTTPException(status_code=409, detail="Feature flag already exists")
    flag = FeatureFlag(
        key=request.key,
        enabled=request.enabled,
        variants=request.variants,
        rollout_percentage=request.rollout_percentage,
        rules=request.rules,
        description=request.description,
        tags=request.tags,
    )
    flag_store.register(flag)
    logger.info("Created feature flag %s", request.key)
    return FlagResponse(**flag.to_dict())


@router.put("/flags/{key}", response_model=FlagResponse)
async def update_flag(key: str, request: UpdateFlagRequest):
    updates = request.model_dump(exclude_none=True)
    if not updates:
        raise HTTPException(status_code=400, detail="No updates provided")
    flag = flag_store.update_flag(key, **updates)
    if not flag:
        raise HTTPException(status_code=404, detail="Feature flag not found")
    logger.info("Updated feature flag %s", key)
    return FlagResponse(**flag.to_dict())


@router.delete("/flags/{key}")
async def delete_flag(key: str):
    if not flag_store.delete_flag(key):
        raise HTTPException(status_code=404, detail="Feature flag not found")
    logger.info("Deleted feature flag %s", key)
    return {"status": "deleted", "key": key}
