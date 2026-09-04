"""Log replication and commit tracking for Raft.

Implements:
- AppendEntries RPC handling with pipelining
- Log matching and consistency checks
- Commit index advancement
- Fast-forward optimization with hints
- Backpressure and flow control
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from .types import (
    AppendEntriesRequest,
    AppendEntriesResponse,
    Command,
    LogEntry,
    LogIndex,
    NodeId,
    Term,
)
from .state_machine import RaftNode

logger = logging.getLogger(__name__)


@dataclass
class ReplicationState:
    """Tracks replication state for a single follower."""

    next_index: LogIndex
    match_index: LogIndex
    inflight_rpc: Optional[asyncio.Task] = None
    last_send_ns: int = 0
    backoff_s: float = 0.0


class LogReplicator:
    """Manages log replication from leader to followers.

    Features:
    - Pipelined RPCs for throughput
    - Backoff on failures
    - Fast-forward on log inconsistency
    - Batch compression
    """

    def __init__(self, node: RaftNode) -> None:
        self.node = node
        self._followers: Dict[NodeId, ReplicationState] = {}
        self._max_batch = node.config.append_entries_batch_size
        self._rpc_timeout = node.config.rpc_timeout_s
        self._running = False
        self._replicate_task: Optional[asyncio.Task] = None

    def start(self) -> None:
        """Start replication loop."""
        if self._running:
            return
        self._running = True
        self._replicate_task = asyncio.create_task(self._replication_loop())

    def stop(self) -> None:
        """Stop replication loop."""
        self._running = False
        if self._replicate_task:
            self._replicate_task.cancel()
            try:
                asyncio.get_event_loop().run_until_complete(self._replicate_task)
            except (asyncio.CancelledError, RuntimeError):
                pass

    def on_membership_change(self, new_nodes: set) -> None:
        """Update follower tracking when membership changes."""
        current = set(self._followers.keys())
        added = new_nodes - current - {self.node.config.node_id}
        removed = current - new_nodes

        for node_id in added:
            last_index = self.node.persistent.last_index()
            self._followers[node_id] = ReplicationState(
                next_index=last_index + LogIndex(1),
                match_index=LogIndex(0),
            )

        for node_id in removed:
            del self._followers[node_id]

    async def _replication_loop(self) -> None:
        """Main replication loop."""
        while self._running:
            try:
                if self.node.cluster.state == NodeState.LEADER:
                    await self._replicate_all()
                await asyncio.sleep(self.node.config.heartbeat_period_s)
            except asyncio.CancelledError:
                break
            except Exception:
                logger.exception("error in replication loop")

    async def _replicate_all(self) -> None:
        """Replicate to all followers."""
        tasks = []
        for peer_id in self._followers:
            tasks.append(self._replicate_to_follower(peer_id))
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    async def _replicate_to_follower(self, peer_id: NodeId) -> None:
        """Replicate log entries to a single follower."""
        state = self._followers.get(peer_id)
        if state is None:
            return

        # Backoff check
        if state.backoff_s > 0:
            await asyncio.sleep(state.backoff_s)
            state.backoff_s = max(0, state.backoff_s - 0.1)

        # Build request
        prev_index = state.next_index - LogIndex(1)
        prev_term = Term(0)
        for entry in reversed(self.node.persistent.log):
            if entry.index == prev_index:
                prev_term = entry.term
                break

        entries = self._get_entries_since(state.next_index)
        if len(entries) > self._max_batch:
            entries = entries[: self._max_batch]

        request = AppendEntriesRequest(
            term=self.node.persistent.current_term,
            leader_id=self.node.config.node_id,
            prev_log_index=prev_index,
            prev_log_term=prev_term,
            entries=entries,
            leader_commit=self.node.volatile.commit_index,
        )

        # Send with timeout
        try:
            result = await asyncio.wait_for(
                self.node.transport.send_append_entries(peer_id, request),
                timeout=self._rpc_timeout,
            )
            self._handle_response(peer_id, state, result)
        except asyncio.TimeoutError:
            logger.debug("replication to %s timed out", peer_id)
            state.backoff_s = min(1.0, state.backoff_s + 0.1)
        except Exception:
            logger.debug("replication to %s failed", peer_id)
            state.backoff_s = min(1.0, state.backoff_s + 0.1)

    def _get_entries_since(self, index: LogIndex) -> List[LogEntry]:
        """Get log entries starting from the given index."""
        return [e for e in self.node.persistent.log if e.index >= index]

    def _handle_response(
        self,
        peer_id: NodeId,
        state: ReplicationState,
        result,
    ) -> None:
        """Handle AppendEntries response from follower."""
        if not result.success:
            logger.debug("append entries to %s rejected", peer_id)
            # Fast-forward using hint
            if result.response.hint is not None:
                state.next_index = LogIndex(result.response.hint)
            else:
                state.next_index = state.next_index - LogIndex(1)
            state.match_index = LogIndex(0)
            state.backoff_s = min(0.5, state.backoff_s + 0.05)
            return

        response = result.response
        if response.success:
            state.match_index = response.match_index
            state.next_index = response.match_index + LogIndex(1)
            state.backoff_s = 0.0
            state.last_send_ns = time.monotonic_ns()
            self._advance_commit_index()
        else:
            state.backoff_s = min(0.5, state.backoff_s + 0.05)

    def _advance_commit_index(self) -> None:
        """Advance commit index based on majority replication."""
        if self.node.cluster.state != NodeState.LEADER:
            return

        match_indices = [state.match_index for state in self._followers.values()]
        match_indices.append(self.node.persistent.last_index())  # Leader's own log

        # Sort descending
        match_indices.sort(key=lambda x: x.value, reverse=True)

        majority_count = len(self.node.cluster.membership.nodes) // 2 + 1
        if len(match_indices) >= majority_count:
            new_commit = match_indices[majority_count - 1]
            if new_commit > self.node.volatile.commit_index:
                self.node.volatile.commit_index = new_commit
                self.node._apply_committed_entries()

    def on_leader_change(self, is_leader: bool) -> None:
        """Handle leader change event."""
        if not is_leader:
            self._followers.clear()
            self._running = False
