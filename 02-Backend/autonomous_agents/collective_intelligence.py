from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
import numpy as np


@dataclass
class Agent:
    id: str
    position: np.ndarray
    capability: float = 0.5
    opinion: Optional[np.ndarray] = None


@dataclass
class ConsensusResult:
    decision: np.ndarray
    confidence: float
    agreement_score: float
    participating_agents: List[str]


class CollectiveIntelligence:
    def __init__(self, swarm_size: int = 10, opinion_dim: int = 8, influence_decay: float = 0.9):
        self.swarm_size = swarm_size
        self.opinion_dim = opinion_dim
        self.influence_decay = influence_decay
        self.agents: Dict[str, Agent] = {}
        self.consensus_history: List[ConsensusResult] = []
        self.interaction_graph: Dict[str, List[str]] = {}
        self._step = 0

    def add_agent(self, agent_id: str, position: Optional[np.ndarray] = None) -> Agent:
        pos = position if position is not None else np.random.randn(self.opinion_dim)
        agent = Agent(id=agent_id, position=pos.copy())
        self.agents[agent_id] = agent
        if len(self.agents) > self.swarm_size:
            oldest = next(iter(self.agents))
            del self.agents[oldest]
        return agent

    def form_opinion(self, agent_id: str, opinion: np.ndarray) -> Optional[Agent]:
        agent = self.agents.get(agent_id)
        if agent is None:
            return None
        agent.opinion = np.array(opinion, dtype=np.float64)
        return agent

    def local_interaction(self, agent_a: str, agent_b: str) -> Tuple[Optional[Agent], Optional[Agent]]:
        a = self.agents.get(agent_a)
        b = self.agents.get(agent_b)
        if a is None or b is None or a.opinion is None or b.opinion is None:
            return a, b
        influence = np.exp(-np.linalg.norm(a.position - b.position) ** 2)
        a.opinion = (1.0 - influence) * a.opinion + influence * b.opinion
        b.opinion = (1.0 - influence) * b.opinion + influence * a.opinion
        self._record_interaction(agent_a, agent_b)
        return a, b

    def swarm_consensus(self) -> Optional[ConsensusResult]:
        opinions = [a.opinion for a in self.agents.values() if a.opinion is not None]
        if not opinions:
            return None
        stacked = np.stack(opinions)
        decision = np.mean(stacked, axis=0)
        distances = [np.linalg.norm(op - decision) for op in opinions]
        mean_dist = float(np.mean(distances)) if distances else 0.0
        confidence = max(0.0, min(1.0, 1.0 - mean_dist / (np.std(decision) + 1e-6)))
        agreement = max(0.0, min(1.0, 1.0 / (1.0 + mean_dist)))
        result = ConsensusResult(
            decision=decision,
            confidence=confidence,
            agreement_score=agreement,
            participating_agents=[a.id for a in self.agents.values() if a.opinion is not None],
        )
        self.consensus_history.append(result)
        if len(self.consensus_history) > 1000:
            self.consensus_history.pop(0)
        self._step += 1
        return result

    def collective_decision(self, task_vector: np.ndarray) -> ConsensusResult:
        for agent in self.agents.values():
            if agent.opinion is None:
                agent.opinion = np.random.randn(self.opinion_dim)
            affinity = np.exp(-np.linalg.norm(agent.opinion - task_vector) ** 2)
            agent.opinion = agent.opinion + affinity * 0.1 * task_vector
        return self.swarm_consensus()

    def get_swarm_metrics(self) -> Dict[str, Any]:
        return {
            "agent_count": len(self.agents),
            "consensus_count": len(self.consensus_history),
            "interaction_density": self._compute_density(),
            "step": self._step,
        }

    def _record_interaction(self, a: str, b: str) -> None:
        self.interaction_graph.setdefault(a, []).append(b)
        self.interaction_graph.setdefault(b, []).append(a)

    def _compute_density(self) -> float:
        n = len(self.agents)
        if n < 2:
            return 0.0
        total_edges = sum(len(v) for v in self.interaction_graph.values())
        max_edges = n * (n - 1)
        return total_edges / max_edges
