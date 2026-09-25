"""
Next-generation distributed systems facade.

Imports all subsystems from the next_gen_distributed package so existing
imports from this module continue to work unchanged.
"""

from __future__ import annotations

from ASTROVOX_AI.ai_core.next_gen_distributed import (
    ServerlessQuantumFunctions,
    EdgeAIFederatedLearning,
    DecentralizedAIModelNetwork,
    BlockchainModelVerifier,
    ZeroKnowledgePrivacy,
    HomomorphicEncryptionSimulator,
    SecureMultiPartyComputation,
    DistributedQuantumComputing,
    MeshNetworkingForAI,
    P2PModelSharing,
    DistributedConsensus,
    ByzantineFaultTolerance,
    DistributedLedgerForAI,
    QuantumSecureCryptography,
    NextGenDistributedCoordinator,
    AgentTask,
)


class NextGenDistributedSystems:
    def __init__(self):
        self.serverless_quantum = ServerlessQuantumFunctions()
        self.edge_federated: EdgeAIFederatedLearning | None = None
        self.decentralized_network = DecentralizedAIModelNetwork(node_id="node-1")
        self.blockchain_verifier = BlockchainModelVerifier()
        self.zk_privacy = ZeroKnowledgePrivacy()
        self.homomorphic = HomomorphicEncryptionSimulator()
        self.smpc: SecureMultiPartyComputation | None = None
        self.distributed_quantum = DistributedQuantumComputing()
        self.mesh = MeshNetworkingForAI(local_node_id="node-1", local_address="10.0.0.1:8080")
        self.p2p = P2PModelSharing(node_id="node-1")
        self.consensus = DistributedConsensus(node_id="node-1", peers=["node-2", "node-3"])
        self.bft = ByzantineFaultTolerance(node_id="node-1", num_nodes=4, max_byzantine=1)
        self.ledger = DistributedLedgerForAI(node_id="node-1", shard_id="shard-0")
        self.quantum_crypto = QuantumSecureCryptography()
        self.coordinator = NextGenDistributedCoordinator(coordinator_id="coordinator-1")

    def setup_federated_learning(self, model, client_ids):
        self.edge_federated = EdgeAIFederatedLearning(model, len(client_ids), client_ids)
        return self.edge_federated

    def setup_smpc(self, num_parties: int, threshold: int = 2):
        self.smpc = SecureMultiPartyComputation(num_parties, threshold)
        return self.smpc
