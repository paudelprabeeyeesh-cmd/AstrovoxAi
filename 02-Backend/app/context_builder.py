import logging

from .memory_pipeline import get_relevant_memories
from .knowledge import search_docs
from .cost import count_tokens
from .database import get_db
from .core.llm import LLMClient

logger = logging.getLogger(__name__)


class ContextBuilder:
    def __init__(self, llm_client: LLMClient | None = None):
        self.llm_client = llm_client or LLMClient()

    def estimate_tokens(self, text: str) -> int:
        return count_tokens(text)

    def get_system_prompt(self, user_id: str) -> str:
        return "You are a helpful AI assistant. Be concise, accurate, and safe."

    def get_recent_messages(self, user_id: str, limit: int = 20) -> list[dict]:
        with get_db() as conn:
            rows = conn.execute(
                """
                SELECT m.role, m.content
                FROM messages m
                JOIN conversations c ON c.id = m.conversation_id
                WHERE c.user_id = ?
                ORDER BY m.created_at DESC
                LIMIT ?
                """,
                (user_id, limit),
            ).fetchall()
        rows = list(reversed(rows))
        return [{"role": r["role"], "content": r["content"]} for r in rows]

    def get_relevant_memories(self, user_id: str, prompt: str, limit: int = 5) -> list[dict]:
        return get_relevant_memories(user_id, prompt, limit)

    def get_relevant_documents(self, user_id: str, prompt: str, limit: int = 3) -> list[dict]:
        docs = search_docs(user_id, prompt, limit)
        return [{"id": d.id, "title": d.title, "content": d.content} for d in docs]

    def truncate_to_fit(self, messages: list[dict], max_tokens: int) -> list[dict]:
        total = sum(self.estimate_tokens(m.get("content", "")) for m in messages)
        if total <= max_tokens:
            return messages
        truncated = list(messages)
        while truncated and total > max_tokens:
            removed = truncated.pop(0)
            total -= self.estimate_tokens(removed.get("content", ""))
        return truncated

    def build_context(self, user_id: str, current_prompt: str, max_tokens: int = 128000) -> str:
        system_prompt = self.get_system_prompt(user_id)
        recent = self.get_recent_messages(user_id, limit=20)
        memories = self.get_relevant_memories(user_id, current_prompt, limit=5)
        docs = self.get_relevant_documents(user_id, current_prompt, limit=3)

        context_parts = [f"System: {system_prompt}"]

        if recent:
            formatted_recent = []
            for m in recent:
                formatted_recent.append(f"{m['role']}: {m['content']}")
            context_parts.append("Conversation:\n" + "\n".join(formatted_recent))

        if memories:
            memory_context = "\n".join([f"- {m['key']}: {m['value']}" for m in memories])
            context_parts.append(f"Memories:\n{memory_context}")

        if docs:
            doc_context = "\n".join([f"[{d['title'] or 'doc'}]: {d['content'][:500]}" for d in docs])
            context_parts.append(f"Knowledge:\n{doc_context}")

        context_parts.append(f"User: {current_prompt}")
        full_context = "\n\n".join(context_parts)

        token_count = self.estimate_tokens(full_context)
        if token_count > max_tokens:
            recent_msgs = [{"role": m["role"], "content": m["content"]} for m in recent]
            recent_msgs.append({"role": "user", "content": current_prompt})
            truncated = self.truncate_to_fit(recent_msgs, max_tokens - self.estimate_tokens(system_prompt) - 200)
            parts = [f"System: {system_prompt}"]
            if memories:
                memory_context = "\n".join([f"- {m['key']}: {m['value']}" for m in memories])
                parts.append(f"Memories:\n{memory_context}")
            if docs:
                doc_context = "\n".join([f"[{d['title'] or 'doc'}]: {d['content'][:500]}" for d in docs])
                parts.append(f"Knowledge:\n{doc_context}")
            parts.extend([f"{m['role']}: {m['content']}" for m in truncated])
            full_context = "\n\n".join(parts)

        return full_context

