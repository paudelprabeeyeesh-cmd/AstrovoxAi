import logging
from datetime import datetime, timedelta, timezone
from typing import Any

logger = logging.getLogger(__name__)


class ContextManager:
    def __init__(self, max_tokens: int = 128000, max_memories: int = 100, memory_ttl_days: int = 30):
        self.max_tokens = max_tokens
        self.max_memories = max_memories
        self.memory_ttl_days = memory_ttl_days

    def summarize_context(self, context: str, max_length: int = 4000) -> str:
        if len(context) <= max_length:
            return context
        sentences = context.split(". ")
        summarized = []
        current_length = 0
        for sentence in sentences:
            if current_length + len(sentence) > max_length:
                break
            summarized.append(sentence)
            current_length += len(sentence)
        return ". ".join(summarized) + "..."

    def sliding_window(self, messages: list[dict], window_size: int = 10) -> list[dict]:
        if len(messages) <= window_size:
            return messages
        recent = messages[-window_size:]
        older = messages[:-window_size]
        older_summary = self._summarize_messages(older)
        return [{"role": "system", "content": f"Previous conversation summary: {older_summary}"}] + recent

    def _summarize_messages(self, messages: list[dict]) -> str:
        if not messages:
            return ""
        combined = " ".join([m.get("content", "") for m in messages])
        return self.summarize_context(combined, max_length=1000)

    def fit_to_window(self, prompt: str, context: str, tokenizer_fn) -> tuple[str, str]:
        total_tokens = tokenizer_fn(prompt) + tokenizer_fn(context)
        if total_tokens <= self.max_tokens:
            return prompt, context
        overflow = total_tokens - self.max_tokens
        context_tokens = tokenizer_fn(context)
        if context_tokens > overflow:
            ratio = (context_tokens - overflow) / context_tokens
            keep_length = int(len(context) * ratio)
            context = context[:keep_length] + "..."
        return prompt, context

    def prune_memories(self, memories: list[Any], query: str = "") -> list[Any]:
        cutoff = datetime.now(timezone.utc) - timedelta(days=self.memory_ttl_days)
        recent = [m for m in memories if getattr(m, "created_at", None) and m.created_at >= cutoff]
        scored = []
        query_terms = set(query.lower().split())
        for m in recent:
            text = f"{m.key} {m.value}".lower()
            overlap = len(query_terms & set(text.split()))
            age_days = (datetime.now(timezone.utc) - m.created_at).days if m.created_at else 0
            score = overlap * 10 - age_days * 0.1
            scored.append((score, m))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [m for _, m in scored[: self.max_memories]]

    def semantic_recall(self, memories: list[Any], query: str, top_k: int = 5) -> list[Any]:
        query_terms = set(query.lower().split())
        scored = []
        for m in memories:
            text = f"{m.key} {m.value}".lower()
            overlap = len(query_terms & set(text.split()))
            scored.append((overlap, m))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [m for _, m in scored[:top_k]]

    def summarize_conversation(self, messages: list[dict], max_length: int = 500) -> str:
        if not messages:
            return ""
        combined = "\n".join([f"{m.get('role', '')}: {m.get('content', '')}" for m in messages])
        return self.summarize_context(combined, max_length=max_length)
