"""Tests for the distributed consensus engine."""

from __future__ import annotations

import asyncio
import logging
import time
import unittest

from app.consensus.types import (
    ChangeType,
    Command,
    EvidenceRecord,
    LogEntry,
    LogIndex,
    MembershipConfig,
    MembershipPhase,
    NodeId,
    NodeState,
    PersistentState,
    Term,
    VoteRequest,
    VoteResponse,
)
from app.consensus.state_machine import RaftConfig, RaftNode, RaftCallbacks
from app.consensus.transport import InMemoryTransport, RaftTransport
from app.consensus.leader_election import LeaderElector, ElectionState
from app.consensus.log_replicator import LogReplicator, ReplicationState
from app.consensus.membership import MembershipManager
from app.consensus.snapshot import SnapshotManager, SnapshotWriter, SnapshotReceiver
from app.consensus.recovery import RecoveryManager, WriteAheadLog
from app.consensus.verification import ConsensusVerifier, InvariantCheck

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_node(
    node_id: str,
    peers: set[str],
    transport: RaftTransport | None = None,
) -> RaftNode:
    """Create a RaftNode with in-memory transport."""
    nid = NodeId(node_id)
    if transport is None:
        transport = InMemoryTransport(nid)

    config = RaftConfig(
        node_id=nid,
        heartbeat_period_s=0.05,
        election_timeout_min_s=0.15,
        election_timeout_max_s=0.30,
        pre_vote=True,
        lease_duration_s=0.10,
    )

    callbacks = RaftCallbacks(
        apply_command=lambda cmd: None,
        build_snapshot=lambda: b"",
        restore_snapshot=lambda state: None,
    )

    node = RaftNode(
        config=config,
        transport=transport,
        callbacks=callbacks,
    )
    return node


def connect_peers(nodes: list[RaftNode]) -> None:
    """Connect RaftNodes via in-memory transport."""
    for i, node in enumerate(nodes):
        transport = node.transport
        if isinstance(transport, InMemoryTransport):
            for other in nodes:
                if other is not node:
                    other_transport = other.transport
                    if isinstance(other_transport, InMemoryTransport):
                        transport.add_peer(other_transport)


async def run_until(condition, timeout: float = 5.0):
    """Run until condition is met or timeout."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if condition():
            return True
        await asyncio.sleep(0.01)
    return False


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TypesTest(unittest.TestCase):
    def test_node_id_equality(self):
        a = NodeId("node-1")
        b = NodeId("node-1")
        c = NodeId("node-2")
        self.assertEqual(a, b)
        self.assertNotEqual(a, c)

    def test_term_ordering(self):
        t1 = Term(1)
        t2 = Term(2)
        self.assertLess(t1, t2)
        self.assertGreater(t2, t1)
        self.assertGreaterEqual(t2, t1)
        self.assertLessEqual(t1, t2)

    def test_log_index_ordering(self):
        i1 = LogIndex(1)
        i2 = LogIndex(2)
        self.assertLess(i1, i2)
        self.assertEqual(i1 + 1, LogIndex(2))

    def test_command_hash(self):
        cmd1 = Command(b"hello")
        cmd2 = Command(b"hello")
        cmd3 = Command(b"world")
        self.assertEqual(cmd1.hash(), cmd2.hash())
        self.assertNotEqual(cmd1.hash(), cmd3.hash())

    def test_log_entry_validation(self):
        entry = LogEntry(
            term=Term(1),
            index=LogIndex(1),
            command=Command(b"test"),
        )
        self.assertEqual(entry.term, Term(1))
        self.assertEqual(entry.index, LogIndex(1))


class MembershipManagerTest(unittest.TestCase):
    def test_add_node(self):
        manager = MembershipManager(NodeId("node-1"))
        config = manager.propose_add_node(NodeId("node-2"), "localhost:5002")
        self.assertIsNotNone(config)
        self.assertIn(NodeId("node-2"), config.nodes)
        self.assertEqual(config.change_type, ChangeType.ADD)
        self.assertEqual(config.phase, MembershipPhase.JOINT)

    def test_remove_node(self):
        manager = MembershipManager(NodeId("node-1"))
        manager._config = MembershipConfig(
            nodes={NodeId("node-1"), NodeId("node-2")},
            version=1,
            effective_at=LogIndex(0),
            change_type=ChangeType.ADD,
        )
        config = manager.propose_remove_node(NodeId("node-2"))
        self.assertIsNotNone(config)
        self.assertNotIn(NodeId("node-2"), config.nodes)

    def test_quorum_size(self):
        manager = MembershipManager(NodeId("node-1"))
        manager._config = MembershipConfig(
            nodes={NodeId("n1"), NodeId("n2"), NodeId("n3")},
            version=1,
            effective_at=LogIndex(0),
            change_type=ChangeType.ADD,
        )
        self.assertEqual(manager.quorum_size(), 2)

    def test_is_quorum(self):
        manager = MembershipManager(NodeId("node-1"))
        manager._config = MembershipConfig(
            nodes={NodeId("n1"), NodeId("n2"), NodeId("n3")},
            version=1,
            effective_at=LogIndex(0),
            change_type=ChangeType.ADD,
        )
        self.assertTrue(manager.is_quorum(2))
        self.assertFalse(manager.is_quorum(1))


class SnapshotManagerTest(unittest.TestCase):
    def test_create_snapshot(self):
        manager = SnapshotManager(NodeId("node-1"))
        snapshot = manager.create_snapshot(
            state=b"test state",
            last_index=LogIndex(100),
            last_term=Term(2),
        )
        self.assertEqual(snapshot.metadata.last_included_index, LogIndex(100))
        self.assertEqual(snapshot.metadata.last_included_term, Term(2))
        self.assertEqual(len(snapshot.state), 10)

    def test_compress_decompress(self):
        manager = SnapshotManager(NodeId("node-1"))
        original = Snapshot(
            metadata=SnapshotMetadata(
                last_included_index=LogIndex(100),
                last_included_term=Term(2),
                timestamp_ns=time.time_ns(),
                size_bytes=1000,
                checksum=b"\x00" * 32,
            ),
            state=b"x" * 1000,
        )
        compressed = manager.compress(original)
        self.assertLess(len(compressed.state), len(original.state))
        decompressed = manager.decompress(compressed)
        self.assertEqual(decompressed.state, original.state)

    def test_snapshot_writer(self):
        manager = SnapshotManager(NodeId("node-1"))
        snapshot = manager.create_snapshot(
            state=b"hello world",
            last_index=LogIndex(1),
            last_term=Term(1),
        )
        writer = SnapshotWriter(snapshot=snapshot, chunk_size=5)

        chunks = []
        while not writer.done:
            chunks.append(writer.get_chunk())
            writer.advance(len(chunks[-1]))

        self.assertEqual(b"".join(chunks), b"hello world")

    def test_snapshot_receiver(self):
        metadata = SnapshotMetadata(
            last_included_index=LogIndex(1),
            last_included_term=Term(1),
            timestamp_ns=time.time_ns(),
            size_bytes=5,
            checksum=hashlib.sha256(b"hello").digest(),
        )
        receiver = SnapshotReceiver(metadata=metadata)

        self.assertTrue(receiver.accept_chunk(b"hello", 0))
        self.assertTrue(receiver.is_complete())

        snapshot = receiver.build_snapshot()
        self.assertEqual(snapshot.state, b"hello")


class RecoveryManagerTest(unittest.TestCase):
    def test_wal_replay_empty(self):
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            wal = WriteAheadLog(
                path=Path(tmpdir) / "test.wal",
                node_id=NodeId("node-1"),
            )
            entries = wal.replay()
            self.assertEqual(entries, [])

    def test_wal_append_replay(self):
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            wal = WriteAheadLog(
                path=Path(tmpdir) / "test.wal",
                node_id=NodeId("node-1"),
            )
            state = PersistentState(current_term=Term(5))
            wal.append(state)
            wal.close()

            entries = wal.replay()
            self.assertEqual(len(entries), 1)
            self.assertEqual(entries[0]["term"], 5)

    def test_validate_log(self):
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            manager = RecoveryManager(NodeId("node-1"), Path(tmpdir))
            log = [
                LogEntry(Term(1), LogIndex(1), Command(b"a")),
                LogEntry(Term(1), LogIndex(2), Command(b"b")),
                LogEntry(Term(2), LogIndex(3), Command(b"c")),
            ]
            valid = manager.validate_log(log)
            self.assertEqual(len(valid), 3)

    def test_compact_log(self):
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            manager = RecoveryManager(NodeId("node-1"), Path(tmpdir))
            log = [
                LogEntry(Term(1), LogIndex(1), Command(b"a")),
                LogEntry(Term(1), LogIndex(2), Command(b"b")),
                LogEntry(Term(1), LogIndex(3), Command(b"c")),
            ]
            compacted = manager.compact_log(log, LogIndex(2))
            self.assertEqual(len(compacted), 1)
            self.assertEqual(compacted[0].index, LogIndex(3))


class ConsensusVerifierTest(unittest.TestCase):
    def test_election_safety_single_leader(self):
        node = make_node("node-1", {"node-2", "node-3"})
        node.cluster.state = NodeState.LEADER
        node.persistent.current_term = Term(1)

        verifier = ConsensusVerifier([node])
        results = verifier.check_all()
        election_check = [r for r in results if r.name == "election_safety"][0]
        self.assertTrue(election_check.passed)

    def test_no_duplicate_leaders(self):
        node1 = make_node("node-1", {"node-2"})
        node1.cluster.state = NodeState.LEADER
        node2 = make_node("node-2", {"node-1"})
        node2.cluster.state = NodeState.FOLLOWER

        verifier = ConsensusVerifier([node1, node2])
        results = verifier.check_all()
        dup_check = [r for r in results if r.name == "no_duplicate_leaders"][0]
        self.assertTrue(dup_check.passed)


class IntegrationTest(unittest.TestCase):
    def test_single_node_leader_election(self):
        """Single node should elect itself immediately."""
        node = make_node("node-1", set())
        # Single node is automatically leader
        self.assertEqual(node.cluster.state, NodeState.LEADER)

    def test_log_replication_single_node(self):
        """Single node should replicate to itself."""
        node = make_node("node-1", set())
        self.assertEqual(node.cluster.state, NodeState.LEADER)

        # Submit a command
        cmd = Command(b"test command")
        entry = LogEntry(
            term=node.persistent.current_term,
            index=node.persistent.last_index() + LogIndex(1),
            command=cmd,
        )
        node.persistent.log.append(entry)

        # Should be immediately committed on single node
        node._update_commit_index()
        self.assertEqual(node.volatile.commit_index, LogIndex(1))


if __name__ == "__main__":
    unittest.main()
