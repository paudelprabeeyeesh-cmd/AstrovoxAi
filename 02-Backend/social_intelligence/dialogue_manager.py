from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Dict, List, Optional
import random
import re


class SpeakerRole(Enum):
    AGENT = auto()
    USER = auto()
    SYSTEM = auto()


class TopicStatus(Enum):
    OPEN = auto()
    RESOLVED = auto()
    DEFERRED = auto()


@dataclass
class DialogueTurn:
    speaker: SpeakerRole
    text: str
    topic: str = "general"
    sentiment: float = 0.0
    metadata: Dict = field(default_factory=dict)


@dataclass
class TopicState:
    topic: str
    status: TopicStatus
    turns: int = 0
    last_sentiment: float = 0.0


class DialogueManager:
    def __init__(self, max_turns_per_topic: int = 10):
        self.max_turns_per_topic = max_turns_per_topic
        self.history: List[DialogueTurn] = []
        self.topics: Dict[str, TopicState] = {}

    def add_turn(self, speaker: SpeakerRole, text: str, topic: str = "general") -> DialogueTurn:
        sentiment = self._estimate_sentiment(text)
        turn = DialogueTurn(speaker=speaker, text=text, topic=topic, sentiment=sentiment)
        self.history.append(turn)

        if topic not in self.topics:
            self.topics[topic] = TopicState(topic=topic, status=TopicStatus.OPEN)
        self.topics[topic].turns += 1
        self.topics[topic].last_sentiment = sentiment

        if self.topics[topic].turns >= self.max_turns_per_topic:
            self.topics[topic].status = TopicStatus.DEFERRED

        return turn

    def get_topic_history(self, topic: str) -> List[DialogueTurn]:
        return [t for t in self.history if t.topic == topic]

    def resolve_topic(self, topic: str) -> None:
        if topic in self.topics:
            self.topics[topic].status = TopicStatus.RESOLVED

    def get_active_topics(self) -> List[str]:
        return [t for t, s in self.topics.items() if s.status == TopicStatus.OPEN]

    def get_summary(self) -> Dict:
        return {
            "total_turns": len(self.history),
            "active_topics": len(self.get_active_topics()),
            "resolved_topics": sum(1 for s in self.topics.values() if s.status == TopicStatus.RESOLVED),
        }

    def _estimate_sentiment(self, text: str) -> float:
        positive = {"good", "great", "thanks", "happy", "agree", "yes", "love", "excellent"}
        negative = {"bad", "sorry", "no", "hate", "angry", "sad", "upset", "disagree"}
        words = set(re.findall(r"[a-zA-Z]+", text.lower()))
        pos = len(words & positive)
        neg = len(words & negative)
        total = pos + neg
        if total == 0:
            return 0.0
        return max(-1.0, min(1.0, (pos - neg) / total))
