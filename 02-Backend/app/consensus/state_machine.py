"""Core Raft state machine with leader election, log replication, and commit.

This module implements the heart of the Raft consensus protocol:
- State transitions (follower → candidate → leader)
- Leader election with pre-vote
- Log replication and commit tracking
- Safety invariants enforcement
"""

from __future__ import annotations

import asyncio
import logging
import time
import weakref
from collections import deque
from dataclasses import dataclass, field
from typing import (
    Any,
    Awaitable,
    Callable,
    Dict,
    List,
    Optional,
    Set,
    Tuple,
    Union,
)

from .types import (
    AppendEntriesRequest,
    AppendEntriesResponse,
    ChangeType,
    ClusterState,
    Command,
    EvidenceRecord,
    GetLeaderRequest,
    GetLeaderResponse,
    InstallSnapshotRequest,
    InstallSnapshotResponse,
    LogEntry,
    LogIndex,
    MembershipChangeRequest,
    MembershipChangeResponse,
    MembershipConfig,
    MembershipPhase,
    NodeId,
    NodeState,
    PersistentState,
    Snapshot,
    Term,
    TransferLeaderRequest,
    TransferLeaderResponse,
    VoteRequest,
    VoteResponse,
    VolatileState,
)
from .transport import RaftTransport

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------


@dataclass
class RaftConfig:
    """Raft node configuration."""

    node_id: NodeId
    heartbeat_period_s: float = 0.05  # 50ms
    election_timeout_min_s: float = 0.15  # 150ms
    election_timeout_max_s: float = 0.30  # 300ms
    pre_vote: bool = True
    lease_duration_s: float = 0.10  # Leader lease for lease reads
    snapshot_threshold: int = 10_000  # Snapshot after N entries
    snapshot_age_s: float = 86_400  # Force snapshot after 24h
    max_log_size: int = 1_000_000  # Max log entries before compaction
    append_entries_batch_size: int = 100  # Max entries per RPC
    rpc_timeout_s: float = 1.0
    max_rpc_retries: int = 3

    def random_election_timeout(self) -> float:
        import random

        return random.uniform(
            self.election_timeout_min_s, self.election_timeout_max_s
        )


# ---------------------------------------------------------------------------
# Callbacks
# ---------------------------------------------------------------------------


@dataclass
class RaftCallbacks:
    """Application callbacks for state machine integration."""

    apply_command: Callable[[Command], None]
    build_snapshot: Callable[[], bytes]
    restore_snapshot: Callable[[bytes], None]
    on_leader_change: Optional[Callable[[Optional[NodeId]], None]] = None
    on_membership_change: Optional[Callable[[MembershipConfig], None]] = None
    on_evidence: Optional[Callable[[EvidenceRecord], None]] = None


# ---------------------------------------------------------------------------
# Raft State Machine
# ---------------------------------------------------------------------------


class RaftNode:
    """Core Raft consensus state machine.

    Thread-safe for single-threaded async execution.
    All state mutations go through this class.
    """

    def __init__(
        self,
        config: RaftConfig,
        transport: RaftTransport,
        callbacks: RaftCallbacks,
        membership: Optional[MembershipConfig] = None,
    ) -> None:
        self.config = config
        self.transport = transport
        self.callbacks = callbacks

        # Persistent state (must be persisted before responding)
        self.persistent = PersistentState()

        # Volatile state (rebuilt on restart)
        self.volatile = VolatileState()

        # Cluster state
        initial_membership = membership or MembershipConfig(
            nodes={config.node_id},
            version=1,
            effective_at=LogIndex(0),
            change_type=ChangeType.ADD,
            phase=MembershipPhase.SINGLE,
        )
        self.cluster = ClusterState(
            node_id=config.node_id,
            address="",
            state=NodeState.FOLLOWER,
            persistent=self.persistent,
            volatile=self.volatile,
            membership=initial_membership,
        )

        # Internal state
        self._election_deadline_ns = time.monotonic_ns() + int(
            config.random_election_timeout() * 1e9
        )
        self._lease_deadline_ns = 0
        self._snapshot_deadline_ns = time.monotonic_ns() + int(
            config.snapshot_age_s * 1e9
        )
        self._pending_config: Optional[MembershipConfig] = None
        self._vote_requests: Set[NodeId] = set()
        self._running = False
        self._main_task: Optional[asyncio.Task] = None
        self._tick_task: Optional[asyncio.Task] = None

        # Register RPC handlers
        transport.register_handler("vote_request", self._handle_vote_request)
        transport.register_handler("vote_response", self._handle_vote_response)
        transport.register_handler("append_entries", self._handle_append_entries)
        transport.register_handler(
            "append_entries_response", self._handle_append_entries_response
        )
        transport.register_handler(
            "install_snapshot", self._handle_install_snapshot
        )
        transport.register_handler(
            "transfer_leader", self._handle_transfer_leader
        )
        transport.register_handler("get_leader", self._handle_get_leader)
        transport.register_handler(
            "membership_change", self._handle_membership_change
        )
        transport.register_handler("evidence", self._handle_evidence)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def start(self) -> None:
        """Start the Raft node."""
        if self._running:
            return
        self._running = True
        await self.transport.start()
        self._main_task = asyncio.create_task(self._run_main_loop())
        self._tick_task = asyncio.create_task(self._run_tick_loop())
        logger.info("Raft node %s started", self.config.node_id)

    async def stop(self) -> None:
        """Stop the Raft node."""
        self._running = False
        if self._main_task:
            self._main_task.cancel()
            try:
                await self._main_task
            except asyncio.CancelledError:
                pass
        if self._tick_task:
            self._tick_task.cancel()
            try:
                await self._tick_task
            except asyncio.CancelledError:
                pass
        await self.transport.stop()
        logger.info("Raft node %s stopped", self.config.node_id)

    async def submit(self, command: Command) -> LogIndex:
        """Submit a command to the Raft log (leader only).

        Returns the log index where the command is stored.
        """
        if self.cluster.state != NodeState.LEADER:
            raise RuntimeError("only leader can submit commands")

        # Check lease
        if time.monotonic_ns() < self._lease_deadline_ns:
            # Still in lease window, but we still need to replicate
            pass

        entry = LogEntry(
            term=self.persistent.current_term,
            index=self.persistent.last_index() + LogIndex(1),
            command=command,
        )
        self.persistent.log.append(entry)

        # Replicate immediately
        await self._replicate_log()

        # Wait for majority replication
        index = entry.index
        timeout = self.config.election_timeout_max_s * 2
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if self.volatile.commit_index >= index:
                return index
            await asyncio.sleep(0.001)

        raise TimeoutError(f"command not committed within {timeout}s")

    def get_leader(self) -> Optional[NodeId]:
        """Get current leader ID, if known."""
        if self.cluster.state == NodeState.LEADER:
            return self.config.node_id
        # Check if we have a valid lease
        if time.monotonic_ns() < self._lease_deadline_ns:
            return None  # No known leader in lease window
        return None

    def get_state(self) -> Tuple[Term, Optional[NodeId], bool]:
        """Return (current_term, leader_id, is_leader)."""
        return (
            self.persistent.current_term,
            self.get_leader(),
            self.cluster.state == NodeState.LEADER,
        )

    def request_membership_change(
        self, node: NodeId, change_type: ChangeType, address: str = ""
    ) -> None:
        """Request a membership change (leader only)."""
        if self.cluster.state != NodeState.LEADER:
            raise RuntimeError("only leader can change membership")

        # Create configuration command
        config = MembershipConfig(
            nodes=self.cluster.membership.nodes | {node}
            if change_type == ChangeType.ADD
            else self.cluster.membership.nodes - {node},
            version=self.cluster.membership.version + 1,
            effective_at=self.persistent.last_index() + LogIndex(1),
            change_type=change_type,
        )

        # Use joint consensus for safety
        self._pending_config = config
        # The actual config change is submitted as a log entry
        # This is simplified - full joint consensus is in membership.py

    # ------------------------------------------------------------------
    # Main loops
    # ------------------------------------------------------------------

    async def _run_main_loop(self) -> None:
        """Main event loop - processes RPC responses."""
        while self._running:
            try:
                await asyncio.sleep(0.001)
                self._check_lease_expiry()
            except asyncio.CancelledError:
                break
            except Exception:
                logger.exception("error in main loop")

    async def _run_tick_loop(self) -> None:
        """Tick loop - handles timeouts and background tasks."""
        while self._running:
            try:
                await asyncio.sleep(0.001)
                self._process_timeouts()
                await self._maybe_snapshot()
            except asyncio.CancelledError:
                break
            except Exception:
                logger.exception("error in tick loop")

    def _process_timeouts(self) -> None:
        """Process election and other timeouts."""
        now_ns = time.monotonic_ns()

        # Election timeout
        if self.cluster.state != NodeState.LEADER:
            if now_ns >= self._election_deadline_ns:
                self._start_election()

        # Lease expiry (for reads)
        if self.cluster.state == NodeState.LEADER:
            if now_ns >= self._lease_deadline_ns:
                # Step down if lease expired without heartbeat
                if self._lease_deadline_ns > 0:
                    logger.warning("leader lease expired, stepping down")
                    self._become_follower(self.persistent.current_term)

    def _check_lease_expiry(self) -> None:
        """Check if leader lease has expired."""
        pass

    async def _maybe_snapshot(self) -> None:
        """Create snapshot if needed."""
        if self.persistent.snapshot is not None:
            snapshot_age = time.monotonic() - (
                self.persistent.snapshot.metadata.timestamp_ns / 1e9
            )
            if snapshot_age < self.config.snapshot_age_s:
                return

        log_size = len(self.persistent.log)
        if log_size < self.config.snapshot_threshold:
            return

        # Create snapshot
        state = self.callbacks.build_snapshot()
        last_index = self.persistent.last_index()
        last_term = self.persistent.last_term()

        snapshot = Snapshot(
            metadata=SnapshotMetadata(
                last_included_index=last_index,
                last_included_term=last_term,
                timestamp_ns=time.time_ns(),
                size_bytes=len(state),
                checksum=hashlib.sha256(state).digest(),
            ),
            state=state,
        )

        self.persistent.snapshot = snapshot
        # Truncate log
        self.persistent.truncate_from(last_index + LogIndex(1))
        logger.info("created snapshot at index %s", last_index)

    # ------------------------------------------------------------------
    # Leader election
    # ------------------------------------------------------------------

    def _start_election(self) -> None:
        """Start a new election (or pre-vote)."""
        now_ns = time.monotonic_ns()
        last_index = self.persistent.last_index()
        last_term = self.persistent.last_term()

        if self.config.pre_vote and not self._needs_real_election():
            # Pre-vote phase
            term = self.persistent.current_term
            self._vote_requests.clear()
            request = VoteRequest(
                term=term,
                candidate_id=self.config.node_id,
                last_log_index=last_index,
                last_log_term=last_term,
                pre_vote=True,
            )
            self.cluster.state = NodeState.CANDIDATE
            logger.debug("starting pre-vote for term %s", term)
            asyncio.create_task(self._send_vote_requests(request))
            return

        # Real election
        term = self.persistent.current_term + Term(1)
        self.persistent.current_term = term
        self.persistent.voted_for = self.config.node_id
        self._vote_requests.clear()
        self.cluster.state = NodeState.CANDIDATE

        request = VoteRequest(
            term=term,
            candidate_id=self.config.node_id,
            last_log_index=last_index,
            last_log_term=last_term,
            pre_vote=False,
        )
        logger.info("starting election for term %s", term)
        asyncio.create_task(self._send_vote_requests(request))

    def _needs_real_election(self) -> bool:
        """Check if we need a real election (vs pre-vote)."""
        # If we're not hearing from a leader, we need a real election
        # This is simplified - production would check actual heartbeat recency
        return True

    async def _send_vote_requests(self, request: VoteRequest) -> None:
        """Send vote requests to all peers."""
        majority = len(self.cluster.membership.nodes) // 2 + 1
        votes_received = 1  # Vote for self

        for peer_id in self.cluster.membership.nodes:
            if peer_id == self.config.node_id:
                continue
            result = await self.transport.send_vote_request(peer_id, request)
            if result.success and result.response.vote_granted:
                votes_received += 1
                if votes_received >= majority:
                    self._become_leader()
                    return

        # Election failed, reset timeout
        self._election_deadline_ns = time.monotonic_ns() + int(
            self.config.random_election_timeout() * 1e9
        )
        if self.cluster.state == NodeState.CANDIDATE:
            self.cluster.state = NodeState.FOLLOWER

    def _become_leader(self) -> None:
        """Transition to leader state."""
        logger.info(
            "node %s became leader for term %s",
            self.config.node_id,
            self.persistent.current_term,
        )
        self.cluster.state = NodeState.LEADER

        # Initialize leader volatile state
        last_index = self.persistent.last_index()
        self.volatile.next_index = {
            node: last_index + LogIndex(1)
            for node in self.cluster.membership.nodes
            if node != self.config.node_id
        }
        self.volatile.match_index = {
            node: LogIndex(0)
            for node in self.cluster.membership.nodes
            if node != self.config.node_id
        }

        # Set lease deadline
        self._lease_deadline_ns = time.monotonic_ns() + int(
            self.config.lease_duration_s * 1e9
        )

        # Submit no-op entry to establish authority
        noop = Command(b"", entry_type="noop")
        entry = LogEntry(
            term=self.persistent.current_term,
            index=last_index + LogIndex(1),
            command=noop,
        )
        self.persistent.log.append(entry)

        # Start heartbeat loop
        asyncio.create_task(self._heartbeat_loop())

        if self.callbacks.on_leader_change:
            self.callbacks.on_leader_change(self.config.node_id)

    def _become_follower(self, term: Term) -> None:
        """Transition to follower state."""
        if self.cluster.state == NodeState.LEADER:
            logger.info("leader stepping down to term %s", term)
            if self.callbacks.on_leader_change:
                self.callbacks.on_leader_change(None)
        else:
            logger.debug("becoming follower for term %s", term)

        self.cluster.state = NodeState.FOLLOWER
        self.persistent.current_term = term
        self.persistent.voted_for = None
        self.volatile.next_index.clear()
        self.volatile.match_index.clear()
        self._lease_deadline_ns = 0
        self._election_deadline_ns = time.monotonic_ns() + int(
            self.config.random_election_timeout() * 1e9
        )

    # ------------------------------------------------------------------
    # Heartbeat / log replication
    # ------------------------------------------------------------------

    async def _heartbeat_loop(self) -> None:
        """Send periodic heartbeats and replicate log."""
        while self._running and self.cluster.state == NodeState.LEADER:
            try:
                await self._replicate_log()
                await asyncio.sleep(self.config.heartbeat_period_s)
            except asyncio.CancelledError:
                break
            except Exception:
                logger.exception("error in heartbeat loop")

    async def _replicate_log(self) -> None:
        """Replicate log entries to all followers."""
        if self.cluster.state != NodeState.LEADER:
            return

        # Extend lease on successful replication
        self._lease_deadline_ns = time.monotonic_ns() + int(
            self.config.lease_duration_s * 1e9
        )

        for peer_id in self.cluster.membership.nodes:
            if peer_id == self.config.node_id:
                continue
            asyncio.create_task(self._replicate_to_peer(peer_id))

    async def _replicate_to_peer(self, peer_id: NodeId) -> None:
        """Replicate log entries to a single peer."""
        next_idx = self.volatile.next_index.get(peer_id, LogIndex(1))
        prev_index = next_idx - LogIndex(1)
        prev_term = Term(0)

        # Find prev entry term
        for entry in reversed(self.persistent.log):
            if entry.index == prev_index:
                prev_term = entry.term
                break

        # Get entries to send
        entries = self.persistent.entries_from(next_idx)
        if len(entries) > self.config.append_entries_batch_size:
            entries = entries[: self.config.append_entries_batch_size]

        request = AppendEntriesRequest(
            term=self.persistent.current_term,
            leader_id=self.config.node_id,
            prev_log_index=prev_index,
            prev_log_term=prev_term,
            entries=entries,
            leader_commit=self.volatile.commit_index,
        )

        result = await self.transport.send_append_entries(peer_id, request)
        if not result.success:
            logger.debug("replication to %s failed: %s", peer_id, result.error)
            return

        response = result.response
        if response.success:
            # Update match index
            if entries:
                self.volatile.match_index[peer_id] = entries[-1].index
                self.volatile.next_index[peer_id] = entries[-1].index + LogIndex(1)
            self._update_commit_index()
        else:
            # Decrement next index and retry
            current = self.volatile.next_index.get(peer_id, LogIndex(1))
            if current > LogIndex(0):
                self.volatile.next_index[peer_id] = current - LogIndex(1)

    def _update_commit_index(self) -> None:
        """Update commit index based on majority replication."""
        if self.cluster.state != NodeState.LEADER:
            return

        majority = len(self.cluster.membership.nodes) // 2 + 1
        committed = 0

        for peer_id, match_idx in self.volatile.match_index.items():
            if match_idx >= self.volatile.commit_index:
                committed += 1

        # Include self
        committed += 1

        if committed >= majority:
            # Find highest log index replicated on majority
            all_indices = [self.volatile.commit_index] + list(
                self.volatile.match_index.values()
            )
            new_commit = max(all_indices)
            self.volatile.commit_index = new_commit
            self._apply_committed_entries()

    def _apply_committed_entries(self) -> None:
        """Apply committed entries to state machine."""
        while self.volatile.last_applied < self.volatile.commit_index:
            next_idx = self.volatile.last_applied + LogIndex(1)
            for entry in self.persistent.log:
                if entry.index == next_idx:
                    try:
                        self.callbacks.apply_command(entry.command)
                        self.volatile.last_applied = next_idx
                    except Exception:
                        logger.exception("failed to apply entry %s", next_idx)
                    break

    # ------------------------------------------------------------------
    # RPC handlers
    # ------------------------------------------------------------------

    async def _handle_vote_request(self, request: VoteRequest) -> VoteResponse:
        """Handle incoming VoteRequest RPC."""
        term = request.term
        current_term = self.persistent.current_term

        # Update term if stale
        if term > current_term:
            self._become_follower(term)

        # Reject if term is stale
        if term < current_term:
            return VoteResponse(
                term=current_term, vote_granted=False, voter_id=self.config.node_id
            )

        # Grant vote if:
        # 1. We haven't voted in this term (or voted for this candidate)
        # 2. Candidate's log is at least as up-to-date as ours
        vote_granted = False

        if self.persistent.voted_for is None or self.persistent.voted_for == request.candidate_id:
            our_last_index = self.persistent.last_index()
            our_last_term = self.persistent.last_term()

            log_ok = (
                request.last_log_term > our_last_term
                or (
                    request.last_log_term == our_last_term
                    and request.last_log_index >= our_last_index
                )
            )

            if log_ok:
                vote_granted = True
                self.persistent.voted_for = request.candidate_id
                self._election_deadline_ns = time.monotonic_ns() + int(
                    self.config.random_election_timeout() * 1e9
                )

        return VoteResponse(
            term=self.persistent.current_term,
            vote_granted=vote_granted,
            voter_id=self.config.node_id,
        )

    async def _handle_vote_response(self, response: VoteResponse) -> None:
        """Handle incoming VoteResponse RPC."""
        if self.cluster.state != NodeState.CANDIDATE:
            return

        if response.term > self.persistent.current_term:
            self._become_follower(response.term)
            return

        if response.vote_granted and response.term == self.persistent.current_term:
            self._vote_requests.add(response.voter_id)
            # Check if we have majority
            majority = len(self.cluster.membership.nodes) // 2 + 1
            if len(self._vote_requests) + 1 >= majority:
                self._become_leader()

    async def _handle_append_entries(
        self, request: AppendEntriesRequest
    ) -> AppendEntriesResponse:
        """Handle incoming AppendEntries RPC."""
        term = request.term
        current_term = self.persistent.current_term

        # Update term if stale
        if term > current_term:
            self._become_follower(term)

        # Reject if term is stale
        if term < current_term:
            return AppendEntriesResponse(
                term=current_term,
                success=False,
                follower_id=self.config.node_id,
                match_index=LogIndex(0),
            )

        # Valid leader - reset election timer
        self._election_deadline_ns = time.monotonic_ns() + int(
            self.config.random_election_timeout() * 1e9
        )
        self._lease_deadline_ns = time.monotonic_ns() + int(
            self.config.lease_duration_s * 1e9
        )

        # Step down if we're a candidate and receive valid AE
        if self.cluster.state == NodeState.CANDIDATE:
            self.cluster.state = NodeState.FOLLOWER

        # Check log consistency
        if request.prev_log_index > LogIndex(0):
            prev_entry = None
            for entry in self.persistent.log:
                if entry.index == request.prev_log_index:
                    prev_entry = entry
                    break

            if prev_entry is None or prev_entry.term != request.prev_log_term:
                # Log inconsistency - fast-forward rejection
                hint = self._find_conflict_hint(request.prev_log_index)
                return AppendEntriesResponse(
                    term=self.persistent.current_term,
                    success=False,
                    follower_id=self.config.node_id,
                    match_index=LogIndex(0),
                    hint=hint,
                )

        # Append entries
        if request.entries:
            self._append_entries(request.entries)

        # Update commit index
        if request.leader_commit > self.volatile.commit_index:
            self.volatile.commit_index = min(
                request.leader_commit, self.persistent.last_index()
            )
            self._apply_committed_entries()

        return AppendEntriesResponse(
            term=self.persistent.current_term,
            success=True,
            follower_id=self.config.node_id,
            match_index=self.persistent.last_index(),
        )

    async def _handle_append_entries_response(
        self, response: AppendEntriesResponse
    ) -> None:
        """Handle incoming AppendEntriesResponse RPC."""
        if self.cluster.state != NodeState.LEADER:
            return

        if response.term > self.persistent.current_term:
            self._become_follower(response.term)
            return

        if response.success:
            self.volatile.match_index[response.follower_id] = response.match_index
            self.volatile.next_index[response.follower_id] = (
                response.match_index + LogIndex(1)
            )
            self._update_commit_index()
        else:
            # Fast-forward using hint
            current = self.volatile.next_index.get(
                response.follower_id, LogIndex(1)
            )
            if response.hint is not None and response.hint < current.value:
                self.volatile.next_index[response.follower_id] = LogIndex(
                    response.hint
                )
            elif current > LogIndex(0):
                self.volatile.next_index[response.follower_id] = (
                    current - LogIndex(1)
                )

    async def _handle_install_snapshot(
        self, request: InstallSnapshotRequest
    ) -> InstallSnapshotResponse:
        """Handle incoming InstallSnapshot RPC."""
        if request.term < self.persistent.current_term:
            return InstallSnapshotResponse(
                term=self.persistent.current_term,
                offset=0,
                accepted=False,
                error="stale term",
            )

        # Accept snapshot
        if request.offset == 0:
            # New snapshot
            self.persistent.snapshot = request.snapshot

        # In production: write chunk to disk
        if request.done:
            # Snapshot complete
            self.persistent.truncate_from(
                request.snapshot.metadata.last_included_index + LogIndex(1)
            )
            self.callbacks.restore_snapshot(request.snapshot.state)
            logger.info("snapshot installed at index %s", request.snapshot.metadata.last_included_index)

        return InstallSnapshotResponse(
            term=self.persistent.current_term,
            offset=request.offset + len(request.chunk),
            accepted=True,
        )

    async def _handle_transfer_leader(
        self, request: TransferLeaderRequest
    ) -> TransferLeaderResponse:
        """Handle leader transfer request."""
        if request.term < self.persistent.current_term:
            return TransferLeaderResponse(
                term=self.persistent.current_term,
                accepted=False,
                error="stale term",
            )

        if self.cluster.state != NodeState.LEADER:
            return TransferLeaderResponse(
                term=self.persistent.current_term,
                accepted=False,
                error="not leader",
            )

        # Step down and trigger election on target
        self._become_follower(self.persistent.current_term)
        return TransferLeaderResponse(
            term=self.persistent.current_term,
            accepted=True,
        )

    async def _handle_get_leader(
        self, request: GetLeaderRequest
    ) -> GetLeaderResponse:
        """Handle GetLeader RPC."""
        leader_id = self.get_leader()
        return GetLeaderResponse(
            term=self.persistent.current_term,
            leader_id=leader_id,
            leader_address="",
        )

    async def _handle_membership_change(
        self, request: MembershipChangeRequest
    ) -> MembershipChangeResponse:
        """Handle membership change request."""
        if request.term < self.persistent.current_term:
            return MembershipChangeResponse(
                term=self.persistent.current_term,
                accepted=False,
                error="stale term",
            )

        # Membership changes must go through log replication
        # This is simplified - full implementation in membership.py
        return MembershipChangeResponse(
            term=self.persistent.current_term,
            accepted=True,
            pending_version=self.cluster.membership.version + 1,
        )

    async def _handle_evidence(self, evidence: EvidenceRecord) -> None:
        """Handle Byzantine fault evidence."""
        self.evidence.append(evidence)
        if self.callbacks.on_evidence:
            self.callbacks.on_evidence(evidence)

    # ------------------------------------------------------------------
    # Log manipulation
    # ------------------------------------------------------------------

    def _append_entries(self, entries: List[LogEntry]) -> None:
        """Append entries to log, overwriting conflicts."""
        if not entries:
            return

        # Find truncation point
        truncate_idx = None
        for entry in entries:
            for existing in self.persistent.log:
                if existing.index == entry.index and existing.term != entry.term:
                    truncate_idx = entry.index
                    break

        if truncate_idx is not None:
            self.persistent.truncate_from(truncate_idx)

        # Append new entries
        existing_indices = {e.index for e in self.persistent.log}
        for entry in entries:
            if entry.index not in existing_indices:
                self.persistent.log.append(entry)

    def _find_conflict_hint(self, index: LogIndex) -> int:
        """Find a hint for fast-forward on log inconsistency."""
        if not self.persistent.log:
            return 0

        for entry in reversed(self.persistent.log):
            if entry.index.value <= index.value:
                return entry.index.value + 1
        return 0

    # ------------------------------------------------------------------
    # Snapshot installation
    # ------------------------------------------------------------------

    async def _install_snapshot(self, snapshot: Snapshot) -> None:
        """Install a snapshot from leader."""
        self.persistent.snapshot = snapshot
        self.persistent.truncate_from(
            snapshot.metadata.last_included_index + LogIndex(1)
        )
        self.callbacks.restore_snapshot(snapshot.state)
        self.volatile.last_applied = snapshot.metadata.last_included_index
        self.volatile.commit_index = snapshot.metadata.last_included_index
