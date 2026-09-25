"""Self-consistency decoding and verifier patterns."""

from __future__ import annotations

import logging
import random
import time
import uuid
from collections import Counter
from dataclasses import dataclass, field
from typing import Any

from app.config import settings

logger = logging.getLogger(__name__)


@dataclass
class DecodeCandidate:
    text: str
    tokens: list[str] = field(default_factory=list)
    logprobs: list[float] = field(default_factory=list)
    latency_ms: float = 0.0


class SelfConsistencyDecoder:
    def __init__(self, model: str = "gpt-4o-mini-2024-07-18", num_samples: int = 5, temperature: float = 0.7):
        self.model = model
        self.num_samples = num_samples
        self.temperature = temperature
        self._client = None

    def _get_client(self):
        if self._client is None:
            import openai
            self._client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
        return self._client

    def decode(self, prompt: str, stop: list[str] | None = None) -> DecodeCandidate:
        candidates = self._sample(prompt, stop)
        if not candidates:
            return DecodeCandidate(text="")
        majority = self._majority_vote(candidates)
        return majority

    def _sample(self, prompt: str, stop: list[str] | None = None) -> list[DecodeCandidate]:
        candidates: list[DecodeCandidate] = []
        try:
            client = self._get_client()
            for _ in range(self.num_samples):
                start = time.perf_counter()
                result = client.chat.completions.create(
                    model=self.model,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=self.temperature,
                    stop=stop,
                    max_tokens=512,
                )
                latency = (time.perf_counter() - start) * 1000
                text = result.choices[0].message.content or ""
                candidates.append(DecodeCandidate(text=text, latency_ms=latency))
        except Exception as exc:
            logger.error("Self-consistency sampling failed: %s", exc)
        return candidates

    def _majority_vote(self, candidates: list[DecodeCandidate]) -> DecodeCandidate:
        if not candidates:
            return DecodeCandidate(text="")
        if len(candidates) == 1:
            return candidates[0]
        counts: Counter[str] = Counter(c.text.strip() for c in candidates if c.text.strip())
        if not counts:
            return candidates[0]
        best_text = counts.most_common(1)[0][0]
        best = next(c for c in candidates if c.text.strip() == best_text)
        return best


class Verifier:
    def __init__(self, model: str = "gpt-4o-mini-2024-07-18"):
        self.model = model
        self._client = None

    def _get_client(self):
        if self._client is None:
            import openai
            self._client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
        return self._client

    def verify(self, prompt: str, candidate: str) -> tuple[bool, str, float]:
        try:
            client = self._get_client()
            result = client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "Verify if the answer is correct. Return JSON with keys: valid (bool), reason (str), confidence (float 0-1)."},
                    {"role": "user", "content": f"Prompt:\n{prompt}\n\nCandidate:\n{candidate}"},
                ],
                temperature=0.0,
            )
            import json
            content = result.choices[0].message.content or "{}"
            data = json.loads(content)
            return bool(data.get("valid", False)), str(data.get("reason", "")), float(data.get("confidence", 0.0))
        except Exception as exc:
            logger.error("Verification failed: %s", exc)
            return False, str(exc), 0.0

    def majority_verify(self, prompt: str, candidates: list[str]) -> tuple[str, float]:
        valid: list[tuple[str, float]] = []
        for candidate in candidates:
            ok, _, confidence = self.verify(prompt, candidate)
            if ok:
                valid.append((candidate, confidence))
        if not valid:
            return "", 0.0
        best_text, best_conf = max(valid, key=lambda item: item[1])
        return best_text, best_conf
