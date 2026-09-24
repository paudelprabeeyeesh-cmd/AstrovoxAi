import numpy as np
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, field


@dataclass
class SocialCue:
    sender: str
    receiver: str
    content: Any
    modality: str
    confidence: float = 1.0
    timestamp: float = field(default_factory=lambda: __import__('time').time())


class TheoryOfMind:
    def __init__(self, n_agents: int = 4, belief_dim: int = 8):
        self.beliefs: Dict[str, np.ndarray] = {}
        self.intentions: Dict[str, np.ndarray] = {}
        self.belief_dim = belief_dim

    def update_belief(self, agent_id: str, observation: np.ndarray, confidence: float = 1.0) -> None:
        if agent_id not in self.beliefs:
            self.beliefs[agent_id] = np.zeros(self.belief_dim)
        self.beliefs[agent_id] = (1 - confidence) * self.beliefs[agent_id] + confidence * observation

    def infer_intention(self, agent_id: str, action: np.ndarray) -> np.ndarray:
        if agent_id not in self.beliefs:
            return np.zeros(self.belief_dim)
        similarity = np.dot(self.beliefs[agent_id], action)
        norm = np.linalg.norm(self.beliefs[agent_id]) * np.linalg.norm(action)
        if norm == 0:
            return np.zeros(self.belief_dim)
        return self.beliefs[agent_id] * (similarity / norm)

    def get_belief(self, agent_id: str) -> np.ndarray:
        return self.beliefs.get(agent_id, np.zeros(self.belief_dim)).copy()


class CommunicationChannel:
    def __init__(self, vocab_size: int = 100, message_dim: int = 16):
        self.vocab_size = vocab_size
        self.message_dim = message_dim
        self.symbol_embeddings: Dict[int, np.ndarray] = {}
        self._history: List[SocialCue] = []

    def encode(self, message: str, sender: str) -> np.ndarray:
        embedding = np.zeros(self.message_dim)
        for i, ch in enumerate(message[: self.message_dim]):
            embedding[i] = (ord(ch) % 256) / 256.0
        return embedding

    def decode(self, embedding: np.ndarray) -> str:
        symbols = []
        for val in embedding:
            symbols.append(chr(int(val * 256) % 256))
        return "".join(symbols)

    def send(self, sender: str, receiver: str, content: Any, modality: str = "text",
             confidence: float = 1.0) -> SocialCue:
        cue = SocialCue(
            sender=sender,
            receiver=receiver,
            content=content,
            modality=modality,
            confidence=confidence,
        )
        self._history.append(cue)
        return cue

    def get_history(self) -> List[Dict[str, Any]]:
        return [
            {
                "sender": c.sender,
                "receiver": c.receiver,
                "content": str(c.content)[:50],
                "modality": c.modality,
                "confidence": c.confidence,
            }
            for c in self._history[-50:]
        ]


class ReputationSystem:
    def __init__(self):
        self.reputations: Dict[str, float] = {}
        self.interaction_log: List[Dict[str, Any]] = []

    def record_interaction(self, agent_id: str, outcome: float, observers: Optional[List[str]] = None) -> None:
        current = self.reputations.get(agent_id, 0.5)
        self.reputations[agent_id] = 0.8 * current + 0.2 * np.clip(outcome, 0, 1)
        entry = {
            "agent_id": agent_id,
            "outcome": outcome,
            "new_reputation": self.reputations[agent_id],
        }
        self.interaction_log.append(entry)
        if observers:
            for obs in observers:
                if obs not in self.reputations:
                    self.reputations[obs] = 0.5

    def get_reputation(self, agent_id: str) -> float:
        return self.reputations.get(agent_id, 0.5)

    def get_trust_ranking(self) -> List[Tuple[str, float]]:
        return sorted(self.reputations.items(), key=lambda x: x[1], reverse=True)


class SocialEngine:
    def __init__(self):
        self.tom = TheoryOfMind()
        self.comm = CommunicationChannel()
        self.reputation = ReputationSystem()
        self._interaction_count = 0

    def observe(self, agent_id: str, observation: np.ndarray, confidence: float = 1.0) -> None:
        self.tom.update_belief(agent_id, observation, confidence=confidence)

    def send_message(self, sender: str, receiver: str, content: Any,
                     modality: str = "text", confidence: float = 1.0) -> SocialCue:
        self._interaction_count += 1
        return self.comm.send(sender, receiver, content, modality=modality, confidence=confidence)

    def record_outcome(self, agent_id: str, outcome: float, observers: Optional[List[str]] = None) -> None:
        self.reputation.record_interaction(agent_id, outcome, observers=observers)

    def get_social_state(self) -> Dict[str, Any]:
        return {
            "interaction_count": self._interaction_count,
            "known_agents": len(self.tom.beliefs),
            "communication_history": len(self.comm._history),
            "trust_ranking": self.reputation.get_trust_ranking()[:5],
        }
