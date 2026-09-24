from dataclasses import dataclass
from typing import Dict, List, Optional
import re


@dataclass
class PersuasionFeatures:
    text: str
    word_count: int = 0
    sentence_count: int = 0
    exclamation_count: int = 0
    question_count: int = 0
    authority_signals: int = 0
    social_proof_signals: int = 0
    scarcity_signals: int = 0
    reciprocity_signals: int = 0
    consistency_signals: int = 0
    liking_signals: int = 0

    def __post_init__(self):
        self.exclamation_count = self.text.count("!")
        self.question_count = self.text.count("?")

    def persuasion_score(self) -> float:
        if self.sentence_count == 0:
            return 0.0
        raw = (
            self.authority_signals * 0.25
            + self.social_proof_signals * 0.2
            + self.scarcity_signals * 0.2
            + self.reciprocity_signals * 0.15
            + self.consistency_signals * 0.1
            + self.liking_signals * 0.1
        )
        return min(1.0, raw / max(1, self.sentence_count))


class PersuasionDetector:
    def __init__(self):
        self.patterns = {
            "authority": re.compile(r"\b(expert|authority|official|research|study|doctor|professor|certified)\b", re.I),
            "social_proof": re.compile(r"\b(everyone|most|majority|popular|trend|best.?sell|million|billion)\b", re.I),
            "scarcity": re.compile(r"\b(limited|rare|exclusive|only|last|hurry|deadline|sold.?out|expire)\b", re.I),
            "reciprocity": re.compile(r"\b(free|gift|bonus|extra|complimentary|included|give|offer)\b", re.I),
            "consistency": re.compile(r"\b(commit|promise|always|never|consistently|guarantee|pledge|oath)\b", re.I),
            "liking": re.compile(r"\b(like|love|friend|trust|admire|respect|kind|support|beautiful|wonderful)\b", re.I),
        }

    def analyze(self, text: str) -> PersuasionFeatures:
        sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if s.strip()]
        words = re.findall(r"[a-zA-Z]+", text)
        pf = PersuasionFeatures(
            text=text,
            word_count=len(words),
            sentence_count=len(sentences),
            exclamation_count=text.count("!"),
            question_count=text.count("?"),
        )
        for key, pattern in self.patterns.items():
            matches = pattern.findall(text)
            if key == "authority":
                pf.authority_signals = len(matches)
            elif key == "social_proof":
                pf.social_proof_signals = len(matches)
            elif key == "scarcity":
                pf.scarcity_signals = len(matches)
            elif key == "reciprocity":
                pf.reciprocity_signals = len(matches)
            elif key == "consistency":
                pf.consistency_signals = len(matches)
            elif key == "liking":
                pf.liking_signals = len(matches)
        return pf

    def batch_analyze(self, texts: List[str]) -> List[PersuasionFeatures]:
        return [self.analyze(t) for t in texts]
