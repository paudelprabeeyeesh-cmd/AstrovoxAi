"""Conversation summarization with sliding window and topic extraction."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Any, Optional

logger = logging.getLogger(__name__)


@dataclass
class SummaryResult:
    summary: str
    topics: list[str]
    key_points: list[str]
    token_count: int
    original_message_count: int


class ConversationSummarizer:
    def __init__(self, llm_client: Any | None = None, keep_last_n: int = 6):
        self.llm_client = llm_client
        self.keep_last_n = keep_last_n

    def summarize(self, messages: list[dict]) -> SummaryResult:
        if not messages:
            return SummaryResult(summary="", topics=[], key_points=[], token_count=0, original_message_count=0)
        if len(messages) <= self.keep_last_n:
            return SummaryResult(summary="", topics=[], key_points=[], token_count=0, original_message_count=len(messages))
        to_summarize = messages[:-self.keep_last_n]
        combined = "\n".join(
            f"{m.get('role', '')}: {(m.get('content', '') or '')[:300]}" for m in to_summarize
        )
        topics = self._extract_topics(combined)
        key_points = self._extract_key_points(combined)
        summary = self._summarize(combined, topics=topics, key_points=key_points)
        return SummaryResult(
            summary=summary,
            topics=topics,
            key_points=key_points,
            token_count=max(1, len(summary) // 4),
            original_message_count=len(to_summarize),
        )

    def compact(self, messages: list[dict]) -> list[dict]:
        result = self.summarize(messages)
        if not result.summary:
            return messages[-self.keep_last_n:]
        summary_msg = {
            "role": "system",
            "content": f"[Summary of earlier conversation: {result.summary}]",
        }
        return [summary_msg] + messages[-self.keep_last_n:]

    def _extract_topics(self, text: str) -> list[str]:
        words = re.findall(r"\b[A-Za-z]{4,}\b", text.lower())
        freq: dict[str, int] = {}
        for w in words:
            freq[w] = freq.get(w, 0) + 1
        stop = {"that", "this", "have", "would", "could", "should", "there", "their", "about", "which", "when", "what", "with"}
        top = sorted([(c, w) for w, c in freq.items() if w not in stop], reverse=True)[:5]
        return [w for _, w in top]

    def _extract_key_points(self, text: str) -> list[str]:
        sentences = re.split(r"(?<=[.!?])\s+", text)
        scored = []
        for s in sentences:
            score = sum(1 for word in ["important", "decided", "agreed", "key", "must", "need", "should", "action"] if word in s.lower())
            scored.append((score, s.strip()))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [s for _, s in scored[:5] if s]

    def _summarize(self, text: str, topics: Optional[list[str]] = None, key_points: Optional[list[str]] = None) -> str:
        if self.llm_client:
            try:
                prompt = (
                    "Summarize the following conversation concisely. "
                    "Preserve key facts, decisions, and context.\n\n"
                    f"{text}\n\nSummary:"
                )
                result = self.llm_client.call_llm(prompt, system="You are a summarization assistant.", timeout=30)
                return result.get("text", "")
            except Exception as e:
                logger.error("LLM summarization failed: %s", e)
        parts = []
        if key_points:
            parts.append("Key points: " + "; ".join(key_points[:3]))
        if topics:
            parts.append("Topics: " + ", ".join(topics))
        return ". ".join(parts) if parts else text[:500]
