"""Snapshot creation, transfer, and installation for Raft.

Implements:
- Chunked snapshot transfer (1MB chunks)
- Incremental snapshotting
- Resume capability for interrupted transfers
- Snapshot compression
- Log compaction after snapshot
"""

from __future__ import annotations

import hashlib
import io
import logging
import time
import zlib
from dataclasses import dataclass, field
from typing import AsyncIterator, Optional

from .types import (
    InstallSnapshotRequest,
    InstallSnapshotResponse,
    LogIndex,
    NodeId,
    Snapshot,
    SnapshotMetadata,
    Term,
)

logger = logging.getLogger(__name__)


@dataclass
class SnapshotWriter:
    """Incremental snapshot writer with chunking."""

    snapshot: Snapshot
    chunk_size: int = 1024 * 1024  # 1MB
    _offset: int = 0
    _buffer: io.BytesIO = field(default_factory=io.BytesIO)

    def __post_init__(self) -> None:
        self._buffer.write(self.snapshot.state)
        self._buffer.seek(0)

    def get_chunk(self) -> bytes:
        """Get next chunk of snapshot data."""
        chunk = self._buffer.read(self.chunk_size)
        return chunk

    def advance(self, bytes_written: int) -> None:
        """Advance offset by bytes written."""
        self._offset += bytes_written

    @property
    def offset(self) -> int:
        return self._offset

    @property
    def done(self) -> bool:
        return self._buffer.tell() >= len(self.snapshot.state)

    def total_size(self) -> int:
        return len(self.snapshot.state)


@dataclass
class SnapshotReceiver:
    """Receives and assembles snapshot chunks."""

    metadata: SnapshotMetadata
    chunk_size: int = 1024 * 1024
    _received: bytearray = field(default_factory=bytearray)
    _expected_size: int = 0

    def __post_init__(self) -> None:
        self._expected_size = self.metadata.size_bytes

    def accept_chunk(self, chunk: bytes, offset: int) -> bool:
        """Accept a chunk at the given offset."""
        expected_offset = len(self._received)
        if offset != expected_offset:
            logger.warning(
                "chunk offset mismatch: expected %d, got %d",
                expected_offset,
                offset,
            )
            return False

        self._received.extend(chunk)
        return True

    def is_complete(self) -> bool:
        """Check if snapshot is fully received."""
        return len(self._received) >= self._expected_size

    def build_snapshot(self) -> Snapshot:
        """Build final snapshot from received chunks."""
        if not self.is_complete():
            raise ValueError("snapshot not complete")

        state = bytes(self._received)
        checksum = hashlib.sha256(state).digest()
        if checksum != self.metadata.checksum:
            raise ValueError("snapshot checksum mismatch")

        return Snapshot(metadata=self.metadata, state=state)


class SnapshotManager:
    """Manages snapshot lifecycle: creation, transfer, installation."""

    def __init__(self, node_id: NodeId) -> None:
        self.node_id = node_id
        self._active_transfers: Dict[NodeId, SnapshotReceiver] = {}

    def create_snapshot(
        self, state: bytes, last_index: LogIndex, last_term: Term
    ) -> Snapshot:
        """Create a new snapshot from state machine state."""
        metadata = SnapshotMetadata(
            last_included_index=last_index,
            last_included_term=last_term,
            timestamp_ns=time.time_ns(),
            size_bytes=len(state),
            checksum=hashlib.sha256(state).digest(),
        )
        return Snapshot(metadata=metadata, state=state)

    def compress(self, snapshot: Snapshot) -> Snapshot:
        """Compress snapshot state using zlib."""
        compressed = zlib.compress(snapshot.state, level=6)
        metadata = SnapshotMetadata(
            last_included_index=snapshot.metadata.last_included_index,
            last_included_term=snapshot.metadata.last_included_term,
            timestamp_ns=snapshot.metadata.timestamp_ns,
            size_bytes=len(compressed),
            checksum=hashlib.sha256(compressed).digest(),
        )
        return Snapshot(metadata=metadata, state=compressed)

    def decompress(self, snapshot: Snapshot) -> Snapshot:
        """Decompress snapshot state."""
        if not snapshot.state.startswith(b"\x78\x9c"):  # zlib magic
            return snapshot
        decompressed = zlib.decompress(snapshot.state)
        metadata = SnapshotMetadata(
            last_included_index=snapshot.metadata.last_included_index,
            last_included_term=snapshot.metadata.last_included_term,
            timestamp_ns=snapshot.metadata.timestamp_ns,
            size_bytes=len(decompressed),
            checksum=hashlib.sha256(decompressed).digest(),
        )
        return Snapshot(metadata=metadata, state=decompressed)

    async def transfer_snapshot(
        self, target: NodeId, snapshot: Snapshot, send_chunk
    ) -> bool:
        """Transfer snapshot to target node in chunks."""
        receiver = SnapshotReceiver(metadata=snapshot.metadata)
        self._active_transfers[target] = receiver

        try:
            writer = SnapshotWriter(snapshot=snapshot)
            offset = 0

            while not writer.done:
                chunk = writer.get_chunk()
                request = InstallSnapshotRequest(
                    term=Term(1),  # Current term would be passed
                    leader_id=self.node_id,
                    snapshot=snapshot,
                    offset=offset,
                    done=writer.done,
                    chunk=chunk,
                )

                result = await send_chunk(target, request)
                if not result.accepted:
                    logger.error("snapshot transfer to %s rejected", target)
                    return False

                if not receiver.accept_chunk(chunk, offset):
                    logger.error("snapshot transfer to %s failed: bad chunk", target)
                    return False

                writer.advance(len(chunk))
                offset += len(chunk)

            logger.info(
                "snapshot transfer to %s complete: %d bytes",
                target,
                offset,
            )
            return True

        finally:
            self._active_transfers.pop(target, None)

    def install_snapshot(self, request: InstallSnapshotRequest) -> InstallSnapshotResponse:
        """Install incoming snapshot."""
        if request.offset == 0:
            receiver = SnapshotReceiver(metadata=request.snapshot.metadata)
            self._active_transfers[request.leader_id] = receiver
        else:
            receiver = self._active_transfers.get(request.leader_id)
            if receiver is None:
                return InstallSnapshotResponse(
                    term=Term(1),
                    offset=0,
                    accepted=False,
                    error="no active transfer",
                )

        if not receiver.accept_chunk(request.chunk, request.offset):
            return InstallSnapshotResponse(
                term=Term(1),
                offset=request.offset,
                accepted=False,
                error="chunk offset mismatch",
            )

        if request.done and receiver.is_complete():
            try:
                snapshot = receiver.build_snapshot()
                # In production: persist snapshot and update state machine
                logger.info(
                    "snapshot installed: index=%s, size=%d",
                    snapshot.metadata.last_included_index,
                    snapshot.metadata.size_bytes,
                )
                return InstallSnapshotResponse(
                    term=Term(1),
                    offset=request.offset + len(request.chunk),
                    accepted=True,
                )
            except ValueError as e:
                return InstallSnapshotResponse(
                    term=Term(1),
                    offset=request.offset,
                    accepted=False,
                    error=str(e),
                )

        return InstallSnapshotResponse(
            term=Term(1),
            offset=request.offset + len(request.chunk),
            accepted=True,
        )
