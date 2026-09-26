from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional


class HumorType(str, Enum):
    INCIDENTAL = "incidental"
    SUPERIORITY = "superiority"
    RELEASE = "release"
    SUPERIOR = "superior"
    WORDPLAY = "wordplay"
    ABSURDIST = "absurdist"


class HumorMechanism(str, Enum):
    INCongruity = "incongruity"
    BENiGN_VIOLATION = "benign_violation"
    TENSION_RELEASE = "tension_release"
    MISTRANSLATION = "mistranslation"


@dataclass
class HumorDetection:
    is_humorous: bool
    humor_type: Optional[HumorType]
    mechanism: Optional[HumorMechanism]
    surprise_score: float = 0.0
    superiority_score: float = 0.0
    benignity_score: float = 0.0
    confidence: float = 0.0
    explanation: str = ""


@dataclass
class HumorGeneration:
    content: str
    humor_type: HumorType
    mechanism: HumorMechanism
    expected_amusement: float = 0.0
    risk_score: float = 0.0


class HumorEngine:
    def __init__(self) -> None:
        self.type_weights = {
            HumorType.INCIDENTAL: 0.8,
            HumorType.SUPERIORITY: 0.7,
            HumorType.RELEASE: 0.75,
            HumorType.WORDPLAY: 0.85,
            HumorType.ABSURDIST: 0.6,
        }

    def detect(self, text: str, context: str = "") -> HumorDetection:
        surprise = 0.5
        superiority = 0.3
        benignity = 0.7
        confidence = max(0.0, min(1.0, (surprise + benignity) / 2))
        return HumorDetection(
            is_humorous=True,
            humor_type=HumorType.INCIDENTAL,
            mechanism=HumorMechanism.INCongruity,
            surprise_score=surprise,
            superiority_score=superiority,
            benignity_score=benignity,
            confidence=confidence,
            explanation="Incongruity detected between expected and actual content",
        )

    def generate(self, topic: str, style: HumorType = HumorType.INCIDENTAL) -> HumorGeneration:
        text = f"Why did the {topic} cross the absurdity boundary?"
        expected = self.type_weights.get(style, 0.5)
        return HumorGeneration(
            content=text,
            humor_type=style,
            mechanism=HumorMechanism.INCongruity,
            expected_amusement=expected,
            risk_score=0.1,
        )
