import re
from typing import Any, Callable, Iterator


TextTransform = Callable[[str], str]


class TextNormalizer:
    def __init__(self, lowercase: bool = True, strip: bool = True, collapse_whitespace: bool = True) -> None:
        self.lowercase = lowercase
        self.strip = strip
        self.collapse_whitespace = collapse_whitespace

    def transform(self, text: str) -> str:
        if self.lowercase:
            text = text.lower()
        if self.strip:
            text = text.strip()
        if self.collapse_whitespace:
            text = re.sub(r"\s+", " ", text)
        return text


class Tokenizer:
    def __init__(self, pattern: str = r"\w+") -> None:
        self.pattern = pattern
        self._regex = re.compile(pattern)

    def tokenize(self, text: str) -> list[str]:
        return self._regex.findall(text)

    def unique(self, text: str) -> list[str]:
        tokens = self.tokenize(text)
        seen: set[str] = set()
        unique = []
        for token in tokens:
            if token not in seen:
                seen.add(token)
                unique.append(token)
        return unique


class TransformerPipeline:
    def __init__(self, steps: list[TextTransform] | None = None) -> None:
        self.steps = steps or []

    def add(self, step: TextTransform) -> None:
        self.steps.append(step)

    def apply(self, text: str) -> str:
        for step in self.steps:
            text = step(text)
        return text

    def apply_batch(self, texts: list[str]) -> list[str]:
        return [self.apply(text) for text in texts]


def remove_punctuation(text: str) -> str:
    return re.sub(r"[^\w\s]", "", text)


def remove_digits(text: str) -> str:
    return re.sub(r"\d+", "", text)


def replace_pattern(text: str, pattern: str, replacement: str) -> str:
    return re.sub(pattern, replacement, text)


class FeatureExtractor:
    @staticmethod
    def length(text: str) -> int:
        return len(text)

    @staticmethod
    def word_count(text: str) -> int:
        return len(re.findall(r"\w+", text))

    @staticmethod
    def avg_word_length(text: str) -> float:
        words = re.findall(r"\w+", text)
        if not words:
            return 0.0
        return sum(len(w) for w in words) / len(words)

    @staticmethod
    def unique_word_count(text: str) -> int:
        words = re.findall(r"\w+", text)
        return len(set(words))

    @staticmethod
    def vocab_richness(text: str) -> float:
        words = re.findall(r"\w+", text)
        if not words:
            return 0.0
        return len(set(words)) / len(words)

    def extract(self, text: str) -> dict[str, Any]:
        return {
            "length": self.length(text),
            "word_count": self.word_count(text),
            "avg_word_length": self.avg_word_length(text),
            "unique_word_count": self.unique_word_count(text),
            "vocab_richness": self.vocab_richness(text),
        }
