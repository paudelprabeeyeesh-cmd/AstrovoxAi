"""Ecosystem Registry — central catalog for plugins, agents, workflows, compiler extensions, SDK modules, and runtime providers."""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional


class EntityKind(str, Enum):
    PLUGIN = "plugin"
    AGENT = "agent"
    WORKFLOW = "workflow"
    COMPILER_EXTENSION = "compiler_extension"
    SDK_MODULE = "sdk_module"
    RUNTIME_PROVIDER = "runtime_provider"


class TrustLevel(str, Enum):
    UNTRUSTED = "untrusted"
    VERIFIED = "verified"
    TRUSTED = "trusted"
    SYSTEM = "system"


@dataclass
class RegistryEntry:
    id: str
    kind: EntityKind
    name: str
    version: str
    description: str
    author: str
    tags: List[str] = field(default_factory=list)
    dependencies: Dict[str, str] = field(default_factory=dict)
    capabilities: List[str] = field(default_factory=list)
    resource_requirements: Dict[str, Any] = field(default_factory=dict)
    trust_level: TrustLevel = TrustLevel.UNTRUSTED
    signature: Optional[str] = None
    manifest_hash: Optional[str] = None
    discovered_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        data = self.__dict__.copy()
        data["kind"] = self.kind.value
        data["trust_level"] = self.trust_level.value
        return data


@dataclass
class CompatibilityMatrix:
    entry_id: str
    api_versions: List[str]
    runtime_versions: List[str]
    dependency_ranges: Dict[str, str] = field(default_factory=dict)
    conflicts: List[str] = field(default_factory=list)
    required_capabilities: List[str] = field(default_factory=list)
    security_policies: List[str] = field(default_factory=list)


class EcosystemRegistry:
    """Central registry for all ecosystem entities."""

    def __init__(self, secret: Optional[str] = None) -> None:
        self._entries: Dict[str, RegistryEntry] = {}
        self._by_kind: Dict[EntityKind, Dict[str, RegistryEntry]] = {kind: {} for kind in EntityKind}
        self._name_index: Dict[str, List[RegistryEntry]] = {}
        self._secret = secret or os.getenv("ECOSYSTEM_REGISTRY_SECRET", "")
        self._compatibility: Dict[str, CompatibilityMatrix] = {}

    def register(self, entry: RegistryEntry) -> RegistryEntry:
        if entry.id in self._entries:
            raise ValueError(f"Registry entry already exists: {entry.id}")
        entry.manifest_hash = self._hash_entry(entry)
        if self._secret and entry.signature:
            self._verify_signature(entry)
        self._entries[entry.id] = entry
        self._by_kind[entry.kind][entry.id] = entry
        self._name_index.setdefault(entry.name, []).append(entry)
        return entry

    def unregister(self, entry_id: str) -> bool:
        if entry_id not in self._entries:
            return False
        entry = self._entries.pop(entry_id)
        self._by_kind[entry.kind].pop(entry_id, None)
        name_list = self._name_index.get(entry.name, [])
        if entry in name_list:
            name_list.remove(entry)
        self._compatibility.pop(entry_id, None)
        return True

    def get(self, entry_id: str) -> Optional[RegistryEntry]:
        return self._entries.get(entry_id)

    def list_by_kind(self, kind: EntityKind) -> List[RegistryEntry]:
        return list(self._by_kind[kind].values())

    def find_by_name(self, name: str) -> List[RegistryEntry]:
        return list(self._name_index.get(name, []))

    def search(self, query: str, kind: Optional[EntityKind] = None) -> List[RegistryEntry]:
        query_lower = query.lower()
        results: List[RegistryEntry] = []
        candidates = self._entries.values() if kind is None else self._by_kind[kind].values()
        for entry in candidates:
            haystack = " ".join([
                entry.name,
                entry.description,
                " ".join(entry.tags),
                entry.author,
            ]).lower()
            if query_lower in haystack:
                results.append(entry)
        return results

    def set_compatibility(self, matrix: CompatibilityMatrix) -> None:
        self._compatibility[matrix.entry_id] = matrix

    def get_compatibility(self, entry_id: str) -> Optional[CompatibilityMatrix]:
        return self._compatibility.get(entry_id)

    def verify_trust(self, entry_id: str) -> bool:
        entry = self._entries.get(entry_id)
        if not entry:
            return False
        if entry.trust_level == TrustLevel.SYSTEM:
            return True
        if not self._secret or not entry.signature or not entry.manifest_hash:
            return False
        return self._verify_signature(entry)

    def _hash_entry(self, entry: RegistryEntry) -> str:
        stable = entry.to_dict()
        stable.pop("discovered_at", None)
        stable.pop("updated_at", None)
        payload = json.dumps(stable, sort_keys=True, default=str)
        return hashlib.sha256(payload.encode()).hexdigest()

    def _verify_signature(self, entry: RegistryEntry) -> bool:
        if not entry.signature or not entry.manifest_hash or not self._secret:
            return False
        expected = hmac.new(
            self._secret.encode(), entry.manifest_hash.encode(), hashlib.sha256
        ).hexdigest()
        return hmac.compare_digest(expected, entry.signature)


_ecosystem_registry = EcosystemRegistry()


def get_ecosystem_registry() -> EcosystemRegistry:
    return _ecosystem_registry
