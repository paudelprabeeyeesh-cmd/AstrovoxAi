from __future__ import annotations

from collections import Counter
from typing import Callable, List, Optional, Tuple


def majority_vote(answers: List[str]) -> Optional[Tuple[str, float]]:
    if not answers:
        return None
    counts = Counter(answers)
    best, freq = counts.most_common(1)[0]
    return best, freq / len(answers)


def self_consistency(
    problem: str,
    generate_fn: Callable[[str], str],
    extract_answer_fn: Callable[[str], str],
    num_samples: int = 5,
) -> Optional[Tuple[str, float]]:
    answers = []
    for _ in range(num_samples):
        raw = generate_fn(problem)
        ans = extract_answer_fn(raw)
        if ans:
            answers.append(ans)
    return majority_vote(answers)


class ConsistencyResult:
    def __init__(self, answer: Optional[str], confidence: float, samples: List[str]) -> None:
        self.answer = answer
        self.confidence = confidence
        self.samples = samples

    @classmethod
    def from_samples(cls, samples: List[str]) -> "ConsistencyResult":
        answer, confidence = majority_vote(samples) or (None, 0.0)
        return cls(answer=answer, confidence=confidence, samples=samples)
