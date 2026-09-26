"""History summarization for long conversations."""

from typing import List, Dict, Optional
from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass
class Summary:
    conversation_id: str
    summary_text: str
    message_count: int
    original_tokens: int
    summary_tokens: int
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class HistorySummarizer:
    _summaries: Dict[str, Summary] = {}

    @classmethod
    def summarize(cls, conversation_id: str, messages: List[Dict[str, str]]) -> Summary:
        message_count = len(messages)
        original_tokens = sum(len(m.get("content", "")) // 4 for m in messages)
        roles = [m.get("role", "unknown") for m in messages]
        contents = [m.get("content", "")[:200] for m in messages[:20]]
        summary_parts = [f"{roles[i]}: {contents[i]}" for i in range(min(len(roles), len(contents)))]
        summary_text = f"Conversation with {message_count} messages.\n" + "\n".join(summary_parts[:10])
        summary_tokens = len(summary_text) // 4
        summary = Summary(
            conversation_id=conversation_id,
            summary_text=summary_text,
            message_count=message_count,
            original_tokens=original_tokens,
            summary_tokens=summary_tokens,
        )
        cls._summaries[conversation_id] = summary
        return summary

    @classmethod
    def get_summary(cls, conversation_id: str) -> Optional[Summary]:
        return cls._summaries.get(conversation_id)
