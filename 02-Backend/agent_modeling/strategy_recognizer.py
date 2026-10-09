import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


@dataclass
class StrategySignature:
    strategy_id: str
    pattern: List[str]
    confidence: float
    occurrence_count: int


@dataclass
class StrategyMatch:
    strategy_id: str
    confidence: float
    matched_actions: List[str]
    start_index: int


class StrategyRecognizer:
    def __init__(self, history_size: int = 500):
        self.history_size = history_size
        self.action_sequence: List[str] = []
        self.strategies: Dict[str, StrategySignature] = {}
        self.matches: List[StrategyMatch] = []
        self.transitions: Dict[str, Dict[str, int]] = {}

    def observe_sequence(self, actions: List[str]) -> List[StrategyMatch]:
        self.action_sequence.extend(actions)
        if len(self.action_sequence) > self.history_size:
            self.action_sequence = self.action_sequence[-self.history_size :]
        return self.recognize()

    def recognize(self) -> List[StrategyMatch]:
        matches = []
        for strategy_id, sig in self.strategies.items():
            matched = self._match_pattern(sig.pattern)
            if matched:
                confidence = self._calculate_confidence(sig.pattern, matched)
                match = StrategyMatch(strategy_id=strategy_id, confidence=confidence, matched_actions=matched, start_index=0)
                matches.append(match)
        self.matches = matches
        return matches

    def _match_pattern(self, pattern: List[str]) -> Optional[List[str]]:
        n = len(pattern)
        if n == 0 or n > len(self.action_sequence):
            return None
        for i in range(len(self.action_sequence) - n + 1):
            window = self.action_sequence[i : i + n]
            if window == pattern:
                return window
        return None

    def _calculate_confidence(self, pattern: List[str], matched: List[str]) -> float:
        if not pattern:
            return 0.0
        matches = sum(1 for a, b in zip(pattern, matched) if a == b)
        return matches / len(pattern)

    def register_strategy(self, strategy_id: str, pattern: List[str]) -> None:
        if strategy_id in self.strategies:
            self.strategies[strategy_id].pattern = pattern
        else:
            self.strategies[strategy_id] = StrategySignature(strategy_id=strategy_id, pattern=pattern, confidence=0.0, occurrence_count=0)

    def known_strategies(self) -> List[StrategySignature]:
        return list(self.strategies.values())

    def strategy_transitions(self) -> Dict[str, Dict[str, int]]:
        for i in range(len(self.action_sequence) - 1):
            curr = self.action_sequence[i]
            next_a = self.action_sequence[i + 1]
            if curr not in self.transitions:
                self.transitions[curr] = {}
            self.transitions[curr][next_a] = self.transitions[curr].get(next_a, 0) + 1
        return self.transitions

    def pattern_frequency(self, pattern: List[str]) -> int:
        count = 0
        n = len(pattern)
        for i in range(len(self.action_sequence) - n + 1):
            if self.action_sequence[i : i + n] == pattern:
                count += 1
        return count
