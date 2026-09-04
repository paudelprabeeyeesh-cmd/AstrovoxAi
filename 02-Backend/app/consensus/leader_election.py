"""Leader election with pre-vote optimization.

Implements:
- Pre-vote phase to prevent unnecessary term advancement
- Randomized election timeouts
- Leader lease for lease-based reads
- Transfer leader support
"""

from __future__ import annotations

import asyncio
import logging
import random
import time
from dataclasses import dataclass, field
from typing import Dict, Optional, Set

from .types import LogIndex, NodeId, NodeState, Term, VoteRequest, VoteResponse
from .state_machine import RaftConfig, RaftNode

logger = logging.getLogger(__name__)


@dataclass
class ElectionState:
    """Tracks election state for a single election attempt."""

    term: Term
    votes_received: Set[NodeId] = field(default_factory=set)
    started_at_ns: int = field(default_factory=lambda: time.monotonic_ns())
    pre_vote_phase: bool = False

    def is_expired(self, timeout_ns: int) -> bool:
        return (time.monotonic_ns() - self.started_at_ns) > timeout_ns


class LeaderElector:
    """Manages leader election for a Raft node.

    Features:
    - Pre-vote to avoid unnecessary term increases
    - Randomized timeouts to prevent split votes
    - Leader lease tracking for lease-based reads
    """

    def __init__(self, node: RaftNode) -> None:
        self.node = node
        self.config = node.config
        self._current_election: Optional[ElectionState] = None
        self._lease_deadline_ns: int = 0

    def on_election_timeout(self) -> None:
        """Called when election timeout fires."""
        if self.node.cluster.state == NodeState.LEADER:
            return

        last_index = self.node.persistent.last_index()
        last_term = self.node.persistent.last_term()

        if self.config.pre_vote and self._should_pre_vote():
            self._start_pre_vote()
        else:
            self._start_real_election()

    def _should_pre_vote(self) -> bool:
        """Determine if we should do pre-vote instead of real election."""
        # Pre-vote if we haven't received a heartbeat recently
        now_ns = time.monotonic_ns()
        heartbeat_timeout = int(self.config.election_timeout_max_s * 1e9)
        return (now_ns - self.node._election_deadline_ns) > heartbeat_timeout

    def _start_pre_vote(self) -> None:
        """Start pre-vote phase."""
        term = self.node.persistent.current_term
        self._current_election = ElectionState(
            term=term, pre_vote_phase=True
        )
        self.node.cluster.state = NodeState.CANDIDATE
        logger.debug("starting pre-vote for term %s", term)

        request = VoteRequest(
            term=term,
            candidate_id=self.config.node_id,
            last_log_index=self.node.persistent.last_index(),
            last_log_term=self.node.persistent.last_term(),
            pre_vote=True,
        )

        asyncio.create_task(self._send_vote_requests(request))

    def _start_real_election(self) -> None:
        """Start real leader election."""
        term = self.node.persistent.current_term + Term(1)
        self.node.persistent.current_term = term
        self.node.persistent.voted_for = self.config.node_id

        self._current_election = ElectionState(
            term=term, pre_vote_phase=False
        )
        self.node.cluster.state = NodeState.CANDIDATE

        request = VoteRequest(
            term=term,
            candidate_id=self.config.node_id,
            last_log_index=self.node.persistent.last_index(),
            last_log_term=self.node.persistent.last_term(),
            pre_vote=False,
        )

        logger.info("starting real election for term %s", term)
        asyncio.create_task(self._send_vote_requests(request))

    async def _send_vote_requests(self, request: VoteRequest) -> None:
        """Send vote requests to all peers and tally results."""
        if self._current_election is None:
            return

        majority = len(self.node.cluster.membership.nodes) // 2 + 1
        votes = {self.config.node_id}  # Vote for self

        tasks = []
        for peer_id in self.node.cluster.membership.nodes:
            if peer_id == self.config.node_id:
                continue
            task = asyncio.create_task(
                self._request_vote_from_peer(peer_id, request)
            )
            tasks.append(task)

        results = await asyncio.gather(*tasks, return_exceptions=True)
        for result in results:
            if isinstance(result, NodeId) and result is not None:
                votes.add(result)

        if len(votes) >= majority:
            self._on_election_won()
        else:
            self._on_election_lost()

    async def _request_vote_from_peer(
        self, peer_id: NodeId, request: VoteRequest
    ) -> Optional[NodeId]:
        """Request vote from a single peer."""
        try:
            result = await self.node.transport.send_vote_request(
                peer_id, request
            )
            if result.success and result.response.vote_granted:
                return result.response.voter_id
        except Exception:
            logger.debug("vote request to %s failed", peer_id)
        return None

    def _on_election_won(self) -> None:
        """Handle election victory."""
        if self._current_election is None:
            return

        logger.info(
            "won election for term %s with %d votes",
            self._current_election.term,
            len(self._current_election.votes_received) + 1,
        )
        self.node._become_leader()
        self._current_election = None

    def _on_election_lost(self) -> None:
        """Handle election loss."""
        if self._current_election is None:
            return

        logger.debug("lost election for term %s", self._current_election.term)
        self._current_election = None
        if self.node.cluster.state == NodeState.CANDIDATE:
            self.node.cluster.state = NodeState.FOLLOWER

    def on_vote_response(self, response: VoteResponse) -> None:
        """Process incoming vote response."""
        if self._current_election is None:
            return

        if response.term > self.node.persistent.current_term:
            self.node._become_follower(response.term)
            self._current_election = None
            return

        if response.vote_granted and response.term == self._current_election.term:
            self._current_election.votes_received.add(response.voter_id)
            majority = len(self.node.cluster.membership.nodes) // 2 + 1
            if len(self._current_election.votes_received) + 1 >= majority:
                self._on_election_won()

    def on_append_entries(self, term: Term) -> None:
        """Reset election state when receiving valid heartbeat."""
        if term >= self.node.persistent.current_term:
            self._current_election = None
            if self.node.cluster.state == NodeState.CANDIDATE:
                self.node.cluster.state = NodeState.FOLLOWER

    def get_lease_deadline_ns(self) -> int:
        """Get current leader lease deadline."""
        return self._lease_deadline_ns

    def renew_lease(self) -> None:
        """Renew leader lease."""
        self._lease_deadline_ns = time.monotonic_ns() + int(
            self.config.lease_duration_s * 1e9
        )

    def is_lease_valid(self) -> bool:
        """Check if leader lease is still valid."""
        return time.monotonic_ns() < self._lease_deadline_ns
