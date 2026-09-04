"""Transport layer abstraction for Raft consensus.

Provides an async interface for RPC communication between Raft nodes.
Default implementation uses in-memory queues for testing; production
implementation uses gRPC with Protobuf.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable, Dict, List, Optional

from .types import (
    AppendEntriesRequest,
    AppendEntriesResponse,
    EvidenceRecord,
    GetLeaderRequest,
    GetLeaderResponse,
    InstallSnapshotRequest,
    InstallSnapshotResponse,
    MembershipChangeRequest,
    MembershipChangeResponse,
    NodeId,
    Term,
    TransferLeaderRequest,
    TransferLeaderResponse,
    VoteRequest,
    VoteResponse,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# RPC message types
# ---------------------------------------------------------------------------


@dataclass
class RpcError(Exception):
    """RPC transport error."""

    code: str = "INTERNAL"
    message: str = ""

    def __str__(self) -> str:
        return f"{self.code}: {self.message}"


@dataclass
class RpcResult:
    """Wrapper for RPC responses."""

    success: bool
    response: Any = None
    error: Optional[RpcError] = None
    latency_ms: float = 0.0


# ---------------------------------------------------------------------------
# Transport interface
# ---------------------------------------------------------------------------


class RaftTransport:
    """Abstract transport layer for Raft RPCs.

    Implementations:
    - InMemoryTransport (testing, single-process)
    - gRpcTransport (production, multi-process)
    """

    async def send_vote_request(self, target: NodeId, request: VoteRequest) -> RpcResult:
        raise NotImplementedError

    async def send_vote_response(self, target: NodeId, response: VoteResponse) -> RpcResult:
        raise NotImplementedError

    async def send_append_entries(
        self, target: NodeId, request: AppendEntriesRequest
    ) -> RpcResult:
        raise NotImplementedError

    async def send_append_entries_response(
        self, target: NodeId, response: AppendEntriesResponse
    ) -> RpcResult:
        raise NotImplementedError

    async def send_install_snapshot(
        self, target: NodeId, request: InstallSnapshotRequest
    ) -> RpcResult:
        raise NotImplementedError

    async def send_transfer_leader(
        self, target: NodeId, request: TransferLeaderRequest
    ) -> RpcResult:
        raise NotImplementedError

    async def send_get_leader(
        self, target: NodeId, request: GetLeaderRequest
    ) -> RpcResult:
        raise NotImplementedError

    async def send_membership_change(
        self, target: NodeId, request: MembershipChangeRequest
    ) -> RpcResult:
        raise NotImplementedError

    async def broadcast_evidence(self, evidence: EvidenceRecord) -> None:
        """Broadcast Byzantine fault evidence to all nodes."""
        raise NotImplementedError

    def register_handler(
        self, rpc_type: str, handler: Callable[..., Awaitable[Any]]
    ) -> None:
        raise NotImplementedError

    async def start(self) -> None:
        raise NotImplementedError

    async def stop(self) -> None:
        raise NotImplementedError


# ---------------------------------------------------------------------------
# In-memory transport (for testing)
# ---------------------------------------------------------------------------


class InMemoryTransport(RaftTransport):
    """Single-process in-memory transport for testing."""

    def __init__(self, node_id: NodeId) -> None:
        self.node_id = node_id
        self._handlers: Dict[str, Callable[..., Awaitable[Any]]] = {}
        self._peers: Dict[NodeId, "InMemoryTransport"] = {}
        self._running = False

    def add_peer(self, peer: "InMemoryTransport") -> None:
        self._peers[peer.node_id] = peer

    def register_handler(
        self, rpc_type: str, handler: Callable[..., Awaitable[Any]]
    ) -> None:
        self._handlers[rpc_type] = handler

    async def _send(self, target: NodeId, rpc_type: str, payload: Any) -> RpcResult:
        if target not in self._peers:
            return RpcResult(
                success=False,
                error=RpcError("UNAVAILABLE", f"node {target} not connected"),
            )
        peer = self._peers[target]
        handler = peer._handlers.get(rpc_type)
        if handler is None:
            return RpcResult(
                success=False,
                error=RpcError("UNIMPLEMENTED", f"no handler for {rpc_type}"),
            )
        start = time.monotonic()
        try:
            result = await handler(payload)
            latency = (time.monotonic() - start) * 1000
            return RpcResult(success=True, response=result, latency_ms=latency)
        except Exception as exc:
            latency = (time.monotonic() - start) * 1000
            return RpcResult(
                success=False,
                error=RpcError("INTERNAL", str(exc)),
                latency_ms=latency,
            )

    async def send_vote_request(self, target: NodeId, request: VoteRequest) -> RpcResult:
        return await self._send(target, "vote_request", request)

    async def send_vote_response(self, target: NodeId, response: VoteResponse) -> RpcResult:
        return await self._send(target, "vote_response", response)

    async def send_append_entries(
        self, target: NodeId, request: AppendEntriesRequest
    ) -> RpcResult:
        return await self._send(target, "append_entries", request)

    async def send_append_entries_response(
        self, target: NodeId, response: AppendEntriesResponse
    ) -> RpcResult:
        return await self._send(target, "append_entries_response", response)

    async def send_install_snapshot(
        self, target: NodeId, request: InstallSnapshotRequest
    ) -> RpcResult:
        return await self._send(target, "install_snapshot", request)

    async def send_transfer_leader(
        self, target: NodeId, request: TransferLeaderRequest
    ) -> RpcResult:
        return await self._send(target, "transfer_leader", request)

    async def send_get_leader(
        self, target: NodeId, request: GetLeaderRequest
    ) -> RpcResult:
        return await self._send(target, "get_leader", request)

    async def send_membership_change(
        self, target: NodeId, request: MembershipChangeRequest
    ) -> RpcResult:
        return await self._send(target, "membership_change", request)

    async def broadcast_evidence(self, evidence: EvidenceRecord) -> None:
        for peer in self._peers.values():
            handler = peer._handlers.get("evidence")
            if handler:
                asyncio.create_task(handler(evidence))

    async def start(self) -> None:
        self._running = True

    async def stop(self) -> None:
        self._running = False
        self._peers.clear()
        self._handlers.clear()


# ---------------------------------------------------------------------------
# gRPC transport (production stub)
# ---------------------------------------------------------------------------


class GrpcTransport(RaftTransport):
    """Production gRPC transport.

    This is a stub implementation showing the interface.
    A real implementation would use grpcio with generated protobuf stubs.
    """

    def __init__(self, node_id: NodeId, bind_address: str) -> None:
        self.node_id = node_id
        self.bind_address = bind_address
        self._server = None
        self._stubs: Dict[NodeId, Any] = {}
        self._handlers: Dict[str, Callable[..., Awaitable[Any]]] = {}
        self._running = False

    def register_handler(
        self, rpc_type: str, handler: Callable[..., Awaitable[Any]]
    ) -> None:
        self._handlers[rpc_type] = handler

    async def start(self) -> None:
        # In production: start gRPC server, register services
        self._running = True
        logger.info("gRPC transport started on %s", self.bind_address)

    async def stop(self) -> None:
        self._running = False
        if self._server:
            await self._server.stop(grace=5)
        self._stubs.clear()

    async def _call(self, target: NodeId, method: str, request: Any) -> RpcResult:
        # In production: call gRPC stub method
        return RpcResult(success=False, error=RpcError("NOT_IMPLEMENTED"))

    async def send_vote_request(self, target: NodeId, request: VoteRequest) -> RpcResult:
        return await self._call(target, "RequestVote", request)

    async def send_vote_response(self, target: NodeId, response: VoteResponse) -> RpcResult:
        return await self._call(target, "RequestVoteResponse", response)

    async def send_append_entries(
        self, target: NodeId, request: AppendEntriesRequest
    ) -> RpcResult:
        return await self._call(target, "AppendEntries", request)

    async def send_append_entries_response(
        self, target: NodeId, response: AppendEntriesResponse
    ) -> RpcResult:
        return await self._call(target, "AppendEntriesResponse", response)

    async def send_install_snapshot(
        self, target: NodeId, request: InstallSnapshotRequest
    ) -> RpcResult:
        return await self._call(target, "InstallSnapshot", request)

    async def send_transfer_leader(
        self, target: NodeId, request: TransferLeaderRequest
    ) -> RpcResult:
        return await self._call(target, "TransferLeader", request)

    async def send_get_leader(
        self, target: NodeId, request: GetLeaderRequest
    ) -> RpcResult:
        return await self._call(target, "GetLeader", request)

    async def send_membership_change(
        self, target: NodeId, request: MembershipChangeRequest
    ) -> RpcResult:
        return await self._call(target, "MembershipChange", request)

    async def broadcast_evidence(self, evidence: EvidenceRecord) -> None:
        # In production: broadcast to all connected nodes
        pass
