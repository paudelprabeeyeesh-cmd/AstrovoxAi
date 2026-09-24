from dataclasses import dataclass, field
from typing import List, Optional
import random
import string


@dataclass
class StyleProfile:
    avg_sentence_length: float = 15.0
    vocabulary_richness: float = 0.5
    punctuation_density: float = 0.1
    formality: float = 0.5
    tone: str = "neutral"


@dataclass
class StyledText:
    text: str
    style: str
    match_score: float = 0.0


class StyleTransfer:
    def __init__(self, seed: Optional[int] = None):
        if seed is not None:
            random.seed(seed)

    def transfer(self, text: str, target_style: str) -> StyledText:
        profile = self._profile(target_style)
        transformed = self._apply(text, profile)
        score = self._similarity(text, transformed, profile)
        return StyledText(text=transformed, style=target_style, match_score=score)

    def _profile(self, style: str) -> StyleProfile:
        s = style.lower()
        if s in {"shakespearean", "elizabethan"}:
            return StyleProfile(avg_sentence_length=20.0, vocabulary_richness=0.85, punctuation_density=0.25, formality=0.9, tone="archaic")
        if s in {"formal", "academic", "scholarly"}:
            return StyleProfile(avg_sentence_length=25.0, vocabulary_richness=0.7, punctuation_density=0.2, formality=0.95, tone="formal")
        if s in {"casual", "informal", "conversational"}:
            return StyleProfile(avg_sentence_length=10.0, vocabulary_richness=0.4, punctuation_density=0.05, formality=0.2, tone="casual")
        if s in {"poetic", "lyrical"}:
            return StyleProfile(avg_sentence_length=8.0, vocabulary_richness=0.75, punctuation_density=0.3, formality=0.6, tone="lyrical")
        if s in {"noir", "detective"}:
            return StyleProfile(avg_sentence_length=14.0, vocabulary_richness=0.6, punctuation_density=0.15, formality=0.5, tone="gritty")
        return StyleProfile(avg_sentence_length=15.0, vocabulary_richness=0.5, punctuation_density=0.1, formality=0.5, tone="neutral")

    def _apply(self, text: str, profile: StyleProfile) -> str:
        sentences = text.replace("!", ".").replace("?", ".").split(".")
        sentences = [s.strip() for s in sentences if s.strip()]
        result = []
        for s in sentences:
            words = s.split()
            if not words:
                continue
            target_len = max(3, int(profile.avg_sentence_length))
            if len(words) > target_len:
                words = words[:target_len]
            elif len(words) < max(3, target_len // 2):
                filler = ["indeed", "furthermore", "moreover", "thus", "hence"]
                words.extend(random.sample(filler, min(3, target_len - len(words))))
            if profile.punctuation_density > 0.2:
                if random.random() < 0.3:
                    words[0] = words[0].capitalize()
                if random.random() < 0.2 and len(words) > 3:
                    words.insert(random.randint(1, len(words) - 1), ";")
            if profile.vocabulary_richness > 0.7:
                synonyms = {"good": "excellent", "bad": "dreadful", "big": "vast", "small": "minuscule", "fast": "swift", "slow": "leisurely"}
                words = [synonyms.get(w.lower(), w) for w in words]
            result.append(" ".join(words))
        joiner = "; " if profile.punctuation_density > 0.2 else ". "
        return joiner.join(result) + ("." if result else "")

    def _similarity(self, original: str, transformed: str, profile: StyleProfile) -> float:
        orig_len = len(original.split())
        trans_len = len(transformed.split())
        len_ratio = min(orig_len, trans_len) / max(orig_len, trans_len, 1)
        return max(0.0, min(1.0, 0.6 * len_ratio + 0.4 * profile.vocabulary_richness))
