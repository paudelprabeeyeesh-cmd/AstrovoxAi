"""Production-grade distributed consensus engine (Raft protocol).

This package implements a complete Raft consensus system with:
- Leader election with pre-vote
- Log replication with pipelining
- Snapshotting and log compaction
- Joint consensus for membership changes
- Byzantine failure detection
- Disk recovery and WAL
- Formal verification tests

Architecture:
    types.py          - Core data structures and protobuf-like messages
    transport.py      - gRPC transport layer (abstracted for testing)
    state_machine.py  - Core Raft state machine
    leader_election.py - Pre-vote and leader election logic
    log_replicator.py - Log replication and commit tracking
    snapshot.py       - Snapshot creation, transfer, and installation
    membership.py     - Joint consensus membership changes
    recovery.py       - Disk recovery and WAL replay
    verification.py   - Formal safety tests and property checks
    __init__.py       - Public API facade
"""
