"""Production-grade distributed consensus engine (Raft protocol).

Public API:
    ConsensusEngine - Main facade for Raft consensus
    ConsensusConfig - Configuration for consensus nodes
    ConsensusNode - Individual Raft node (for advanced usage)

Quick start:
    from app.consensus import ConsensusEngine, ConsensusConfig

    config = ConsensusConfig(node_id="node-1", peers={"node-2", "node-3"})
    engine = ConsensusEngine(config)
    await engine.start()

    # Submit command (leader only)
    index = await engine.submit(Command(b"hello"))

    # Get current leader
    leader = engine.get_leader()
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Union

from .types import (
    Command,
    EvidenceRecord,
    MembershipConfig,
    NodeId,
    PersistentState,
    Snapshot,
    Term,
    VoteRequest,
    VoteResponse,
)
from .transport import (
    GrpcTransport,
    InMemoryTransport,
    RaftTransport,
)
from .state_machine import RaftCallbacks, RaftConfig, RaftNode
from .leader_election import LeaderElector, ElectionState
from .log_replicator import LogReplicator, ReplicationState
from .membership import MembershipManager
from .recovery import RecoveryManager, WriteAheadLog
from .snapshot import SnapshotManager, SnapshotWriter, SnapshotReceiver
from .verification import ConsensusVerifier, InvariantCheck

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------


@dataclass
class ConsensusConfig:
    """Configuration for a Raft consensus node."""

    node_id: str
    peers: Set[str]
    address: str = "localhost:0"
    data_dir: Path = field(default_factory=lambda: Path("./consensus_data"))
    heartbeat_period_s: float = 0.05
    election_timeout_min_s: float = 0.15
    election_timeout_max_s: float = 0.30
    pre_vote: bool = True
    lease_duration_s: float = 0.10
    snapshot_threshold: int = 10_000
    snapshot_age_s: float = 86_400
    max_log_size: int = 1_000_000
    append_entries_batch_size: int = 100
    rpc_timeout_s: float = 1.0
    transport: str = "in_memory"  # "in_memory" | "grpc"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


class ConsensusEngine:
    """High-level facade for Raft consensus.

    Provides a simplified interface for:
    - Starting/stopping consensus nodes
    - Submitting commands
    - Querying leader and cluster state
    - Managing membership changes
    - Snapshot management
    """

    def __init__(self, config: ConsensusConfig) -> None:
        self.config = config
        self.node_id = NodeId(config.node_id)
        self._callbacks: Optional[RaftCallbacks] = None
        self._transport: Optional[RaftTransport] = None
        self._node: Optional[RaftNode] = None
        self._running = False

    def set_callbacks(
        self,
        apply_command: Callable[[Command], None],
        build_snapshot: Callable[[], bytes],
        restore_snapshot: Callable[[bytes], None],
        on_leader_change: Optional[Callable[[Optional[NodeId]], None]] = None,
        on_membership_change: Optional[Callable[[MembershipConfig], None]] = None,
        on_evidence: Optional[Callable[[EvidenceRecord], None]] = None,
    ) -> None:
        """Set application callbacks for state machine integration."""
        self._callbacks = RaftCallbacks(
            apply_command=apply_command,
            build_snapshot=build_snapshot,
            restore_snapshot=restore_snapshot,
            on_leader_change=on_leader_change,
            on_membership_change=on_membership_change,
            on_evidence=on_evidence,
        )

    async def start(self) -> None:
        """Start the consensus engine."""
        if self._running:
            return

        # Create transport
        if self.config.transport == "grpc":
            self._transport = GrpcTransport(
                node_id=self.node_id,
                bind_address=self.config.address,
            )
        else:
            self._transport = InMemoryTransport(node_id=self.node_id)

        # Create Raft node
        if self._callbacks is None:
            # Default callbacks
            self._callbacks = RaftCallbacks(
                apply_command=lambda cmd: None,
                build_snapshot=lambda: b"",
                restore_snapshot=lambda state: None,
            )

        raft_config = RaftConfig(
            node_id=self.node_id,
            heartbeat_period_s=self.config.heartbeat_period_s,
            election_timeout_min_s=self.config.election_timeout_min_s,
            election_timeout_max_s=self.config.election_timeout_max_s,
            pre_vote=self.config.pre_vote,
            lease_duration_s=self.config.lease_duration_s,
            snapshot_threshold=self.config.snapshot_threshold,
            snapshot_age_s=self.config.snapshot_age_s,
            max_log_size=self.config.max_log_size,
            append_entries_batch_size=self.config.append_entries_batch_size,
            rpc_timeout_s=self.config.rpc_timeout_s,
        )

        self._node = RaftNode(
            config=raft_config,
            transport=self._transport,
            callbacks=self._callbacks,
        )

        # Start transport
        await self._transport.start()
        self._running = True
        logger.info("Consensus engine started for node %s", self.node_id)

    async def stop(self) -> None:
        """Stop the consensus engine."""
        if not self._running:
            return

        if self._node:
            await self._node.stop()

        if self._transport:
            await self._transport.stop()

        self._running = False
        logger.info("Consensus engine stopped for node %s", self.node_id)

    async def submit(self, command: Union[Command, bytes]) -> int:
        """Submit a command to the consensus log.

        Args:
            command: Command to submit (or raw bytes)

        Returns:
            Log index where command is stored

        Raises:
            RuntimeError: If this node is not the leader
            TimeoutError: If command is not committed in time
        """
        if isinstance(command, bytes):
            command = Command(payload=command)

        if self._node is None:
            raise RuntimeError("engine not started")

        index = await self._node.submit(command)
        return index.value

    def get_leader(self) -> Optional[str]:
        """Get current leader node ID, or None if unknown."""
        if self._node is None:
            return None
        leader = self._node.get_leader()
        return str(leader) if leader else None

    def get_term(self) -> int:
        """Get current term."""
        if self._node is None:
            return 0
        term, _, _ = self._node.get_state()
        return term.value

    def is_leader(self) -> bool:
        """Check if this node is the current leader."""
        if self._node is None:
            return False
        _, _, is_leader = self._node.get_state()
        return is_leader

    def get_commit_index(self) -> int:
        """Get current commit index."""
        if self._node is None:
            return 0
        return self._node.volatile.commit_index.value

    def get_last_applied(self) -> int:
        """Get last applied index."""
        if self._node is None:
            return 0
        return self._node.volatile.last_applied.value

    def request_membership_change(
        self, node_id: str, change_type: str, address: str = ""
    ) -> bool:
        """Request a membership change.

        Args:
            node_id: Node to add/remove
            change_type: "add" or "remove"
            address: Address for new node (required for "add")

        Returns:
            True if request was accepted
        """
        if self._node is None:
            return False

        from .types import ChangeType as CT

        ct = CT.ADD if change_type == "add" else CT.REMOVE
        try:
            self._node.request_membership_change(NodeId(node_id), ct, address)
            return True
        except RuntimeError:
            return False

    async def transfer_leader(self, target_node: str) -> bool:
        """Transfer leadership to another node."""
        if self._node is None:
            return False

        from .types import TransferLeaderRequest, Term

        request = TransferLeaderRequest(
            term=self._node.persistent.current_term,
            leader_id=self.node_id,
            target_node=NodeId(target_node),
        )
        result = await self._node.transport.send_transfer_leader(
            NodeId(target_node), request
        )
        return result.success

    def get_status(self) -> Dict[str, Any]:
        """Get consensus engine status."""
        if self._node is None:
            return {"state": "stopped"}

        term, leader, is_leader = self._node.get_state()
        return {
            "state": self._node.cluster.state.value,
            "term": term.value,
            "leader": str(leader) if leader else None,
            "is_leader": is_leader,
            "commit_index": self._node.volatile.commit_index.value,
            "last_applied": self._node.volatile.last_applied.value,
            "log_size": len(self._node.persistent.log),
            "membership_size": len(self._node.cluster.membership.nodes),
            "membership_version": self._node.cluster.membership.version,
        }

    def get_membership(self) -> Dict[str, Any]:
        """Get cluster membership info."""
        if self._node is None:
            return {}

        nodes = self._node.cluster.membership.nodes
        return {
            "nodes": [str(n) for n in nodes],
            "version": self._node.cluster.membership.version,
            "phase": self._node.cluster.membership.phase.value,
        }

    async def verify(self) -> List[Dict[str, Any]]:
        """Run consensus invariant checks.

        Returns list of check results.
        """
        # This would need access to all cluster nodes
        # For single-node verification:
        results = []
        if self._node:
            verifier = ConsensusVerifier([self._node])
            checks = verifier.check_all()
            results.extend(
                {
                    "name": c.name,
                    "passed": c.passed,
                    "details": c.details,
                }
                for c in checks
            )
        return results

    async def add_peer_transport(self, peer_id: str, transport: RaftTransport) -> None:
        """Add a peer transport for in-memory testing."""
        if hasattr(self._transport, "add_peer"):
            peer_transport = transport
            if isinstance(peer_transport, InMemoryTransport):
                self._transport.add_peer(peer_transport)  # type: ignore
