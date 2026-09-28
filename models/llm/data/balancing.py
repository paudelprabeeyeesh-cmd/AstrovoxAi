from __future__ import annotations

import random
from collections import defaultdict
from dataclasses import dataclass
from typing import Any

from models.llm.dataset_engineering_v2 import ProcessedDocument


@dataclass
class LanguageBalanceConfig:
    target_ratios: dict[str, float] = field(
        default_factory=lambda: {
            "en": 0.6,
            "es": 0.1,
            "fr": 0.06,
            "de": 0.05,
            "it": 0.04,
            "pt": 0.04,
            "ru": 0.03,
            "zh": 0.03,
            "ja": 0.02,
            "other": 0.03,
        }
    )
    buffer_size: int = 100_000
    seed: int = 42


class LanguageBalancer:
    def __init__(self, config: LanguageBalanceConfig | None = None) -> None:
        self.config = config or LanguageBalanceConfig()
        random.seed(self.config.seed)
        self.buffers: dict[str, list[ProcessedDocument]] = defaultdict(list)
        self.total_seen = 0

    def add(self, document: ProcessedDocument) -> None:
        lang = document.language or "other"
        if lang not in self.config.target_ratios:
            lang = "other"
        self.buffers[lang].append(document)
        self.total_seen += 1

    def sample(self) -> list[ProcessedDocument]:
        if self.total_seen == 0:
            return []
        result: list[ProcessedDocument] = []
        for lang, target_ratio in self.config.target_ratios.items():
            docs = self.buffers.get(lang, [])
            desired = int(self.total_seen * target_ratio)
            if len(docs) > desired:
                random.shuffle(docs)
                docs = docs[:desired]
            result.extend(docs)
        random.shuffle(result)
        return result

    def distribution(self) -> dict[str, float]:
        if self.total_seen == 0:
            return {}
        return {lang: len(docs) / self.total_seen for lang, docs in self.buffers.items()}


@dataclass
class DomainBalanceConfig:
    target_ratios: dict[str, float] = field(
        default_factory=lambda: {
            "web": 0.30,
            "wiki": 0.10,
            "books": 0.10,
            "academic": 0.10,
            "code": 0.10,
            "math": 0.05,
            "qa": 0.05,
            "conversations": 0.10,
            "ocr": 0.05,
            "image_caption": 0.05,
            "multilingual": 0.10,
        }
    )
    buffer_size: int = 100_000
    seed: int = 42


class DomainBalancer:
    def __init__(self, config: DomainBalanceConfig | None = None) -> None:
        self.config = config or DomainBalanceConfig()
        random.seed(self.config.seed)
        self.buffers: dict[str, list[ProcessedDocument]] = defaultdict(list)
        self.total_seen = 0

    def add(self, document: ProcessedDocument) -> None:
        domain = document.domain or "general"
        self.buffers[domain].append(document)
        self.total_seen += 1

    def sample(self) -> list[ProcessedDocument]:
        if self.total_seen == 0:
            return []
        result: list[ProcessedDocument] = []
        for domain, target_ratio in self.config.target_ratios.items():
            docs = self.buffers.get(domain, [])
            desired = int(self.total_seen * target_ratio)
            if len(docs) > desired:
                random.shuffle(docs)
                docs = docs[:desired]
            result.extend(docs)
        random.shuffle(result)
        return result

    def distribution(self) -> dict[str, float]:
        if self.total_seen == 0:
            return {}
        return {domain: len(docs) / self.total_seen for domain, docs in self.buffers.items()}
