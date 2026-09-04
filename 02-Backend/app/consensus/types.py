"""Core data structures for the Raft consensus engine."""

from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class NodeState(str, Enum):
    FOLLOWER = "follower"
    CANDIDATE = "candidate"
    LEADER = "leader"
    OBSERVER = "observer"


class ChangeType(str, Enum):
    ADD = "add"
    REMOVE = "remove"
    UPDATE = "update"


class MembershipPhase(str, Enum):
    SINGLE = "single"  # Only C_new or C_old
    JOINT = "joint"    # C_old AND C_new
    FINAL = "final"    # Only C_new after joint committed


class EntryType(str, Enum):
    COMMAND = "command"
    CONFIGURATION = "configuration"
    NOOP = "noop"


# ---------------------------------------------------------------------------
# Core data structures
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class NodeId:
    """Strongly typed node identifier."""

    value: str

    def __post_init__(self) -> None:
        if not self.value or len(self.value) > 256:
            raise ValueError("NodeId must be non-empty and <= 256 chars")

    def __str__(self) -> str:
        return self.value

    def __hash__(self) -> int:
        return hash(self.value)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, NodeId):
            return NotImplemented
        return self.value == other.value


@dataclass(frozen=True)
class Term:
    """Raft term number - monotonically increasing."""

    value: int

    def __post_init__(self) -> None:
        if self.value < 0:
            raise ValueError("Term must be non-negative")

    def __str__(self) -> str:
        return str(self.value)

    def __lt__(self, other: "Term") -> bool:
        if not isinstance(other, Term):
            return NotImplemented
        return self.value < other.value

    def __gt__(self, other: "Term") -> bool:
        if not isinstance(other, Term):
            return NotImplemented
        return self.value > other.value

    def __ge__(self, other: "Term") -> bool:
        if not isinstance(other, Term):
            return NotImplemented
        return self.value >= other.value

    def __le__(self, other: "Term") -> bool:
        if not isinstance(other, Term):
            return NotImplemented
        return self.value <= other.value


@dataclass(frozen=True)
class LogIndex:
    """Monotonically increasing log position."""

    value: int

    def __post_init__(self) -> None:
        if self.value < 0:
            raise ValueError("LogIndex must be non-negative")

    def __str__(self) -> str:
        return str(self.value)

    def __lt__(self, other: "LogIndex") -> bool:
        if not isinstance(other, LogIndex):
            return NotImplemented
        return self.value < other.value

    def __gt__(self, other: "LogIndex") -> bool:
        if not isinstance(other, LogIndex):
            return NotImplemented
        return self.value > other.value

    def __le__(self, other: "LogIndex") -> bool:
        if not isinstance(other, LogIndex):
            return NotImplemented
        return self.value <= other.value

    def __ge__(self, other: "LogIndex") -> bool:
        if not isinstance(other, LogIndex):
            return NotImplemented
        return self.value >= other.value

    def __add__(self, other: Union[int, "LogIndex"]) -> "LogIndex":
        if isinstance(other, LogIndex):
            return LogIndex(self.value + other.value)
        return LogIndex(self.value + other)


@dataclass(frozen=True)
class Command:
    """State machine command to be replicated."""

    payload: bytes
    entry_type: EntryType = EntryType.COMMAND
    timestamp_ns: int = field(default_factory=lambda: time.time_ns())

    def hash(self) -> bytes:
        return hashlib.sha256(self.payload).digest()


@dataclass(frozen=True)
class LogEntry:
    """Single entry in the Raft log."""

    term: Term
    index: LogIndex
    command: Command
    hash: bytes = field(default_factory=lambda: hashlib.sha256().digest())

    def __post_init__(self) -> None:
        if not isinstance(self.term, Term):
            raise TypeError("term must be a Term")
        if not isinstance(self.index, LogIndex):
            raise TypeError("index must be a LogIndex")
        if not isinstance(self.command, Command):
            raise TypeError("command must be a Command")


@dataclass(frozen=True)
class SnapshotMetadata:
    """Metadata for a persisted snapshot."""

    last_included_index: LogIndex
    last_included_term: Term
    timestamp_ns: int
    size_bytes: int
    checksum: bytes


@dataclass(frozen=True)
class Snapshot:
    """Complete state machine snapshot."""

    metadata: SnapshotMetadata
    state: bytes
    chunk_offset: int = 0
    chunk_size: int = 1024 * 1024  # 1MB chunks


@dataclass(frozen=True)
class MembershipConfig:
    """Cluster membership configuration."""

    nodes: Set[NodeId]
    version: int
    effective_at: LogIndex
    change_type: ChangeType
    phase: MembershipPhase = MembershipPhase.SINGLE


@dataclass(frozen=True)
class VoteRequest:
    """RequestVote RPC arguments."""

    term: Term
    candidate_id: NodeId
    last_log_index: LogIndex
    last_log_term: Term
    pre_vote: bool = False


@dataclass(frozen=True)
class VoteResponse:
    """RequestVote RPC response."""

    term: Term
    vote_granted: bool
    voter_id: NodeId


@dataclass(frozen=True)
class AppendEntriesRequest:
    """AppendEntries RPC arguments."""

    term: Term
    leader_id: NodeId
    prev_log_index: LogIndex
    prev_log_term: Term
    entries: List[LogEntry]
    leader_commit: LogIndex
    leader_signature: bytes = b""


@dataclass(frozen=True)
class AppendEntriesResponse:
    """AppendEntries RPC response."""

    term: Term
    success: bool
    follower_id: NodeId
    match_index: LogIndex
    hint: Optional[int] = None  # Optimization hint for fast-forward


@dataclass(frozen=True)
class InstallSnapshotRequest:
    """InstallSnapshot RPC arguments."""

    term: Term
    leader_id: NodeId
    snapshot: Snapshot
    offset: int
    done: bool
    chunk: bytes


@dataclass(frozen=True)
class InstallSnapshotResponse:
    """InstallSnapshot RPC response."""

    term: Term
    offset: int
    accepted: bool
    error: Optional[str] = None


@dataclass(frozen=True)
class TransferLeaderRequest:
    """TransferLeader RPC arguments."""

    term: Term
    leader_id: NodeId
    target_node: NodeId


@dataclass(frozen=True)
class TransferLeaderResponse:
    """TransferLeader RPC response."""

    term: Term
    accepted: bool
    error: Optional[str] = None


@dataclass(frozen=True)
class GetLeaderRequest:
    """GetLeader RPC arguments."""

    requester_id: NodeId


@dataclass(frozen=True)
class GetLeaderResponse:
    """GetLeader RPC response."""

    term: Term
    leader_id: Optional[NodeId]
    leader_address: Optional[str]


@dataclass(frozen=True)
class MembershipChangeRequest:
    """Add/Remove node request."""

    term: Term
    node: NodeId
    change_type: ChangeType
    node_address: str = ""


@dataclass(frozen=True)
class MembershipChangeResponse:
    """Membership change response."""

    term: Term
    accepted: bool
    pending_version: Optional[int] = None
    error: Optional[str] = None


@dataclass(frozen=True)
class EvidenceRecord:
    """Byzantine behavior evidence for fault detection."""

    accused: NodeId
    term: Term
    evidence_type: str
    payload: bytes
    timestamp_ns: int = field(default_factory=lambda: time.time_ns())
    reporter: Optional[NodeId] = None


# ---------------------------------------------------------------------------
# Persistent state (must survive restarts)
# ---------------------------------------------------------------------------


@dataclass
class PersistentState:
    """State that must be persisted before responding to RPCs."""

    current_term: Term = field(default_factory=lambda: Term(0))
    voted_for: Optional[NodeId] = None
    log: List[LogEntry] = field(default_factory=list)
    snapshot: Optional[Snapshot] = None

    def last_entry(self) -> Optional[LogEntry]:
        if self.snapshot is not None:
            # Snapshot covers up to last_included_index
            # Return synthetic entry for snapshot term/index
            return LogEntry(
                term=self.snapshot.metadata.last_included_term,
                index=self.snapshot.metadata.last_included_index,
                command=Command(b""),
            )
        if self.log:
            return self.log[-1]
        return None

    def last_term(self) -> Term:
        entry = self.last_entry()
        return entry.term if entry else Term(0)

    def last_index(self) -> LogIndex:
        entry = self.last_entry()
        return entry.index if entry else LogIndex(0)

    def entries_from(self, index: LogIndex) -> List[LogEntry]:
        """Return entries starting from (and including) the given index."""
        start = index.value
        return [e for e in self.log if e.index.value >= start]

    def truncate_from(self, index: LogIndex) -> None:
        """Remove all entries at or after the given index."""
        self.log = [e for e in self.log if e.index.value < index.value]


@dataclass
class VolatileState:
    """State that is rebuilt on restart (not persisted)."""

    commit_index: LogIndex = field(default_factory=lambda: LogIndex(0))
    last_applied: LogIndex = field(default_factory=lambda: LogIndex(0))

    # Leader-only
    next_index: Dict[NodeId, LogIndex] = field(default_factory=dict)
    match_index: Dict[NodeId, LogIndex] = field(default_factory=dict)


@dataclass
class ClusterState:
    """Complete cluster node state."""

    node_id: NodeId
    address: str
    state: NodeState = NodeState.FOLLOWER
    persistent: PersistentState = field(default_factory=PersistentState)
    volatile: VolatileState = field(default_factory=VolatileState)
    membership: MembershipConfig = field(default_factory=lambda: MembershipConfig(
        nodes=set(),
        version=0,
        effective_at=LogIndex(0),
        change_type=ChangeType.ADD,
    ))
    lease_start_ns: int = 0
    pre_vote_granted: Set[NodeId] = field(default_factory=set)
    evidence: List[EvidenceRecord] = field(default_factory=list)
    last_heartbeat_ns: int = field(default_factory=lambda: time.time_ns())
