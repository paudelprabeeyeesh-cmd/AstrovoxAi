"""Temporal database with event sourcing, CQRS, and point-in-time queries.

Provides:
- Event sourcing with event store
- CQRS implementation
- Temporal versioning for all entities
- Point-in-time queries
- Temporal constraints
- Audit trail with blockchain
- Data lineage tracking
"""

from __future__ import annotations

import copy
import hashlib
import hmac
import json
import logging
import threading
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

from app.logging_config import get_logger

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Core types
# ---------------------------------------------------------------------------


class OperationType(str, Enum):
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    RESTORE = "restore"
    MERGE = "merge"
    SNAPSHOT = "snapshot"


class ConsistencyLevel(str, Enum):
    STRONG = "strong"
    EVENTUAL = "eventual"
    CAUSAL = "causal"


@dataclass(frozen=True)
class TemporalEntity:
    entity_id: str
    entity_type: str
    data: Dict[str, Any]
    valid_from: datetime
    valid_to: Optional[datetime]
    version: int
    operation: OperationType
    actor: str
    correlation_id: Optional[str]
    causation_id: Optional[str]
    checksum: str
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "entity_id": self.entity_id,
            "entity_type": self.entity_type,
            "data": self.data,
            "valid_from": self.valid_from.isoformat(),
            "valid_to": self.valid_to.isoformat() if self.valid_to else None,
            "version": self.version,
            "operation": self.operation.value,
            "actor": self.actor,
            "correlation_id": self.correlation_id,
            "causation_id": self.causation_id,
            "checksum": self.checksum,
            "metadata": self.metadata,
        }


@dataclass(frozen=True)
class AuditRecord:
    audit_id: str
    entity_id: str
    entity_type: str
    operation: OperationType
    actor: str
    timestamp: datetime
    before_state: Optional[Dict[str, Any]]
    after_state: Dict[str, Any]
    checksum: str
    signature: Optional[str]
    block_hash: Optional[str] = None
    previous_block_hash: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "audit_id": self.audit_id,
            "entity_id": self.entity_id,
            "entity_type": self.entity_type,
            "operation": self.operation.value,
            "actor": self.actor,
            "timestamp": self.timestamp.isoformat(),
            "before_state": self.before_state,
            "after_state": self.after_state,
            "checksum": self.checksum,
            "signature": self.signature,
            "block_hash": self.block_hash,
            "previous_block_hash": self.previous_block_hash,
            "metadata": self.metadata,
        }


@dataclass(frozen=True)
class LineageNode:
    lineage_id: str
    entity_id: str
    operation: OperationType
    timestamp: datetime
    parent_entity_id: Optional[str]
    parent_lineage_id: Optional[str]
    actor: str
    metadata: Dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Temporal constraint engine
# ---------------------------------------------------------------------------


@dataclass
class TemporalConstraint:
    constraint_id: str
    entity_type: str
    rule: str
    validator: Callable[[Dict[str, Any], Optional[Dict[str, Any]]], bool]
    description: str = ""
    enabled: bool = True


class TemporalConstraintEngine:
    """Validates temporal constraints on entity state transitions."""

    def __init__(self) -> None:
        self._constraints: Dict[str, List[TemporalConstraint]] = {}
        self._violations: List[Dict[str, Any]] = []

    def register(self, constraint: TemporalConstraint) -> None:
        self._constraints.setdefault(constraint.entity_type, []).append(constraint)
        logger.info("registered temporal constraint %s on %s", constraint.constraint_id, constraint.entity_type)

    def validate(self, entity_type: str, new_state: Dict[str, Any], old_state: Optional[Dict[str, Any]] = None) -> List[str]:
        violations = []
        constraints = self._constraints.get(entity_type, [])
        for c in constraints:
            if not c.enabled:
                continue
            try:
                if not c.validator(new_state, old_state):
                    violations.append(f"{c.constraint_id}: {c.description or c.rule}")
            except Exception as e:
                violations.append(f"{c.constraint_id}: validation error: {e}")
        if violations:
            self._violations.append({
                "entity_type": entity_type,
                "violations": violations,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })
        return violations

    def get_violations(self, limit: int = 100) -> List[Dict[str, Any]]:
        return self._violations[-limit:]


# ---------------------------------------------------------------------------
# Audit trail with blockchain
# ---------------------------------------------------------------------------


class AuditBlockchain:
    """Append-only audit trail with hash-chain integrity."""

    def __init__(self, secret: Optional[str] = None) -> None:
        self._chain: List[AuditRecord] = []
        self._secret = secret or "audit-secret"
        self._lock = threading.Lock()

    def append(self, record: AuditRecord) -> None:
        previous_hash = self._chain[-1].block_hash if self._chain else "0" * 64
        block_content = json.dumps({
            "audit_id": record.audit_id,
            "entity_id": record.entity_id,
            "operation": record.operation.value,
            "timestamp": record.timestamp.isoformat(),
            "after_state": record.after_state,
            "previous_hash": previous_hash,
        }, sort_keys=True)
        block_hash = hashlib.sha256(block_content.encode()).hexdigest()
        signature = hmac.new(self._secret.encode(), block_hash.encode(), hashlib.sha256).hexdigest()
        signed_record = AuditRecord(
            audit_id=record.audit_id,
            entity_id=record.entity_id,
            entity_type=record.entity_type,
            operation=record.operation,
            actor=record.actor,
            timestamp=record.timestamp,
            before_state=record.before_state,
            after_state=record.after_state,
            checksum=record.checksum,
            signature=signature,
            block_hash=block_hash,
            previous_block_hash=previous_hash,
            metadata=record.metadata,
        )
        with self._lock:
            self._chain.append(signed_record)
        logger.debug("appended audit record %s block %s", record.audit_id, block_hash[:16])

    def verify(self) -> bool:
        with self._lock:
            for i in range(1, len(self._chain)):
                prev = self._chain[i - 1]
                curr = self._chain[i]
                if curr.previous_block_hash != prev.block_hash:
                    return False
                block_content = json.dumps({
                    "audit_id": curr.audit_id,
                    "entity_id": curr.entity_id,
                    "operation": curr.operation.value,
                    "timestamp": curr.timestamp.isoformat(),
                    "after_state": curr.after_state,
                    "previous_hash": curr.previous_block_hash,
                }, sort_keys=True)
                expected_hash = hashlib.sha256(block_content.encode()).hexdigest()
                if curr.block_hash != expected_hash:
                    return False
        return True

    def get_history(self, entity_id: str, limit: int = 100) -> List[Dict[str, Any]]:
        return [r.to_dict() for r in self._chain if r.entity_id == entity_id][-limit:]

    def tail(self, limit: int = 100) -> List[Dict[str, Any]]:
        return [r.to_dict() for r in self._chain[-limit:]]

    @property
    def height(self) -> int:
        return len(self._chain)


# ---------------------------------------------------------------------------
# Data lineage
# ---------------------------------------------------------------------------


class LineageTracker:
    """Tracks data lineage and transformation history."""

    def __init__(self) -> None:
        self._nodes: Dict[str, LineageNode] = {}
        self._edges: List[Tuple[str, str]] = []
        self._lock = threading.Lock()

    def record(self, entity_id: str, operation: OperationType, parent_entity_id: Optional[str] = None, actor: str = "system", metadata: Optional[Dict[str, Any]] = None) -> LineageNode:
        lineage_id = f"lin-{uuid.uuid4().hex[:12]}"
        parent_lineage_id = None
        if parent_entity_id:
            for node in reversed(list(self._nodes.values())):
                if node.entity_id == parent_entity_id:
                    parent_lineage_id = node.lineage_id
                    break
        node = LineageNode(
            lineage_id=lineage_id,
            entity_id=entity_id,
            operation=operation,
            timestamp=datetime.now(timezone.utc),
            parent_entity_id=parent_entity_id,
            parent_lineage_id=parent_lineage_id,
            actor=actor,
            metadata=metadata or {},
        )
        with self._lock:
            self._nodes[lineage_id] = node
            if parent_lineage_id:
                self._edges.append((parent_lineage_id, lineage_id))
        logger.debug("recorded lineage %s for entity %s", lineage_id, entity_id)
        return node

    def get_lineage(self, entity_id: str) -> List[Dict[str, Any]]:
        nodes = [n for n in self._nodes.values() if n.entity_id == entity_id]
        return [{
            "lineage_id": n.lineage_id,
            "entity_id": n.entity_id,
            "operation": n.operation.value,
            "timestamp": n.timestamp.isoformat(),
            "parent_entity_id": n.parent_entity_id,
            "parent_lineage_id": n.parent_lineage_id,
            "actor": n.actor,
            "metadata": n.metadata,
        } for n in sorted(nodes, key=lambda x: x.timestamp)]

    def get_ancestors(self, entity_id: str) -> List[str]:
        lineage_ids = {n.lineage_id for n in self._nodes.values() if n.entity_id == entity_id}
        ancestors: List[str] = []
        visited: set = set()
        queue = list(lineage_ids)
        while queue:
            lid = queue.pop(0)
            if lid in visited:
                continue
            visited.add(lid)
            for parent, child in self._edges:
                if child == lid:
                    ancestors.append(parent)
                    queue.append(parent)
        return ancestors


# ---------------------------------------------------------------------------
# CQRS
# ---------------------------------------------------------------------------


@dataclass
class Command:
    command_id: str
    command_type: str
    entity_type: str
    entity_id: str
    payload: Dict[str, Any]
    actor: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Query:
    query_id: str
    query_type: str
    entity_type: str
    filters: Dict[str, Any]
    options: Dict[str, Any] = field(default_factory=dict)


@dataclass
class QueryResult:
    query_id: str
    items: List[Dict[str, Any]]
    total: int
    took_ms: float
    cached: bool = False


class CommandHandler:
    """Handles write operations in CQRS."""

    def __init__(self, event_store: "TemporalEventStore", audit: AuditBlockchain, lineage: LineageTracker) -> None:
        self._store = event_store
        self._audit = audit
        self._lineage = lineage
        self._handlers: Dict[str, Callable] = {}

    def register(self, command_type: str, handler: Callable) -> None:
        self._handlers[command_type] = handler

    def execute(self, command: Command) -> TemporalEntity:
        handler = self._handlers.get(command.command_type)
        if handler is None:
            raise ValueError(f"unknown command: {command.command_type}")
        result = handler(command)
        self._audit.append(AuditRecord(
            audit_id=f"aud-{uuid.uuid4().hex[:12]}",
            entity_id=command.entity_id,
            entity_type=command.entity_type,
            operation=result.operation,
            actor=command.actor,
            timestamp=datetime.now(timezone.utc),
            before_state=None,
            after_state=result.data,
            checksum=result.checksum,
            signature=None,
            metadata=command.metadata,
        ))
        self._lineage.record(command.entity_id, result.operation, actor=command.actor)
        return result


class QueryHandler:
    """Handles read operations in CQRS."""

    def __init__(self, event_store: "TemporalEventStore") -> None:
        self._store = event_store
        self._read_models: Dict[str, Dict[str, Any]] = {}

    def register_read_model(self, name: str, model: Dict[str, Any]) -> None:
        self._read_models[name] = model

    def execute(self, query: Query) -> QueryResult:
        start = time.monotonic()
        model = self._read_models.get(query.query_type, {})
        items = list(model.values())
        for key, value in query.filters.items():
            items = [i for i in items if i.get(key) == value]
        total = len(items)
        took_ms = (time.monotonic() - start) * 1000
        return QueryResult(query_id=query.query_id, items=items, total=total, took_ms=took_ms)


# ---------------------------------------------------------------------------
# Temporal event store
# ---------------------------------------------------------------------------


class TemporalEventStore:
    """Extended event store with temporal queries and versioning."""

    def __init__(self, consistency: ConsistencyLevel = ConsistencyLevel.EVENTUAL) -> None:
        self._events: List[TemporalEntity] = []
        self._entity_index: Dict[str, List[TemporalEntity]] = {}
        self._snapshots: Dict[str, Dict[int, TemporalEntity]] = {}
        self._consistency = consistency
        self._lock = threading.Lock()

    def append(self, entity: TemporalEntity) -> None:
        with self._lock:
            self._events.append(entity)
            self._entity_index.setdefault(entity.entity_id, []).append(entity)
            logger.debug("appended temporal entity %s v%d", entity.entity_id, entity.version)

    def get_history(self, entity_id: str, limit: int = 100) -> List[Dict[str, Any]]:
        entities = self._entity_index.get(entity_id, [])
        return [e.to_dict() for e in sorted(entities, key=lambda x: x.valid_from)][-limit:]

    def point_in_time(self, entity_id: str, target_time: datetime) -> Optional[Dict[str, Any]]:
        entities = self._entity_index.get(entity_id, [])
        candidates = [e for e in entities if e.valid_from <= target_time and (e.valid_to is None or e.valid_to > target_time)]
        if not candidates:
            return None
        entity = max(candidates, key=lambda e: e.valid_from)
        return entity.data

    def snapshot(self, entity_id: str, state: Dict[str, Any], version: int) -> None:
        entity = TemporalEntity(
            entity_id=entity_id,
            entity_type="snapshot",
            data=state,
            valid_from=datetime.now(timezone.utc),
            valid_to=None,
            version=version,
            operation=OperationType.SNAPSHOT,
            actor="system",
            correlation_id=None,
            causation_id=None,
            checksum="",
        )
        entity.checksum = hashlib.sha256(json.dumps(entity.data, sort_keys=True).encode()).hexdigest()
        self._snapshots.setdefault(entity_id, {})[version] = entity

    def get_snapshot(self, entity_id: str, version: int) -> Optional[Dict[str, Any]]:
        entity = self._snapshots.get(entity_id, {}).get(version)
        return copy.deepcopy(entity.data) if entity else None

    def latest(self, entity_id: str) -> Optional[Dict[str, Any]]:
        entities = self._entity_index.get(entity_id, [])
        if not entities:
            return None
        entity = max(entities, key=lambda e: e.valid_from)
        return copy.deepcopy(entity.data)

    def all_versions(self, entity_id: str) -> List[Dict[str, Any]]:
        return [e.to_dict() for e in sorted(self._entity_index.get(entity_id, []), key=lambda x: x.version)]

    def stats(self) -> Dict[str, Any]:
        return {
            "total_events": len(self._events),
            "entity_count": len(self._entity_index),
            "snapshot_count": sum(len(v) for v in self._snapshots.values()),
            "consistency": self._consistency.value,
        }


# ---------------------------------------------------------------------------
# Main temporal database facade
# ---------------------------------------------------------------------------


class TemporalDatabase:
    """Facade integrating temporal event store, CQRS, constraints, audit, and lineage."""

    def __init__(self, consistency: ConsistencyLevel = ConsistencyLevel.EVENTUAL, audit_secret: Optional[str] = None) -> None:
        self._store = TemporalEventStore(consistency=consistency)
        self._constraints = TemporalConstraintEngine()
        self._audit = AuditBlockchain(secret=audit_secret)
        self._lineage = LineageTracker()
        self._commands = CommandHandler(self._store, self._audit, self._lineage)
        self._queries = QueryHandler(self._store)
        self._lock = threading.Lock()

    def apply(self, entity_id: str, operation: OperationType, new_state: Dict[str, Any], actor: str = "system", entity_type: str = "entity", old_state: Optional[Dict[str, Any]] = None, correlation_id: Optional[str] = None, causation_id: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None) -> TemporalEntity:
        with self._lock:
            violations = self._constraints.validate(entity_type, new_state, old_state)
            if violations:
                raise ValueError(f"temporal constraint violated: {violations}")

            version = len(self._store._entity_index.get(entity_id, [])) + 1
            checksum = hashlib.sha256(json.dumps(new_state, sort_keys=True).encode()).hexdigest()
            entity = TemporalEntity(
                entity_id=entity_id,
                entity_type=entity_type,
                data=copy.deepcopy(new_state),
                valid_from=datetime.now(timezone.utc),
                valid_to=None,
                version=version,
                operation=operation,
                actor=actor,
                correlation_id=correlation_id,
                causation_id=causation_id,
                checksum=checksum,
                metadata=metadata or {},
            )
            self._store.append(entity)
            self._audit.append(AuditRecord(
                audit_id=f"aud-{uuid.uuid4().hex[:12]}",
                entity_id=entity_id,
                entity_type=entity_type,
                operation=operation,
                actor=actor,
                timestamp=entity.valid_from,
                before_state=copy.deepcopy(old_state),
                after_state=copy.deepcopy(new_state),
                checksum=checksum,
                signature=None,
                metadata=metadata or {},
            ))
            self._lineage.record(entity_id, operation, actor=actor, metadata={"version": version})
            return entity

    def query(self, entity_id: str, as_of: Optional[datetime] = None) -> Optional[Dict[str, Any]]:
        if as_of:
            return self._store.point_in_time(entity_id, as_of)
        return self._store.latest(entity_id)

    def history(self, entity_id: str, limit: int = 100) -> List[Dict[str, Any]]:
        return self._store.get_history(entity_id, limit=limit)

    def audit_trail(self, entity_id: str, limit: int = 100) -> List[Dict[str, Any]]:
        return self._audit.get_history(entity_id, limit=limit)

    def lineage(self, entity_id: str) -> List[Dict[str, Any]]:
        return self._lineage.get_lineage(entity_id)

    def verify_audit_integrity(self) -> bool:
        return self._audit.verify()

    def stats(self) -> Dict[str, Any]:
        return self._store.stats()
