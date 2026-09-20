import logging
from typing import Any

from .memory_pipeline import get_relevant_memories
from .knowledge import search_docs
from .cost import count_tokens
from .database import get_db
from .core.llm import LLMClient
from .tools import get_builtin_tools

logger = logging.getLogger(__name__)


class ContextBuilder:
    def __init__(self, llm_client: LLMClient | None = None):
        self.llm_client = llm_client or LLMClient()

    def estimate_tokens(self, text: str) -> int:
        return count_tokens(text)

    def get_system_prompt(self, user_id: str) -> str:
        return (
            "You are AstrovoxAI, a helpful, harmless, and honest AI assistant. "
            "Be concise and accurate. Use tools when needed."
        )

    def get_tool_schemas(self) -> list[dict[str, Any]]:
        tools = []
        for t in get_builtin_tools():
            schema = t.to_openai_schema()
            tools.append(schema)
        return tools

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
        total = sum(self.estimate_tokens(m.get("content", "") or "") for m in messages)
        if total <= max_tokens:
            return messages
        truncated = list(messages)
        while truncated and total > max_tokens:
            removed = truncated.pop(0)
            total -= self.estimate_tokens(removed.get("content", "") or "")
        return truncated

    def build_context(
        self,
        user_id: str,
        current_prompt: str,
        max_tokens: int = 128000,
        include_tools: bool = True,
    ) -> dict[str, Any]:
        system_prompt = self.get_system_prompt(user_id)
        recent = self.get_recent_messages(user_id, limit=20)
        memories = self.get_relevant_memories(user_id, current_prompt, limit=5)
        docs = self.get_relevant_documents(user_id, current_prompt, limit=3)
        tools = self.get_tool_schemas() if include_tools else []

        system_tokens = self.estimate_tokens(system_prompt)
        tools_tokens = self.estimate_tokens(str(tools)) if tools else 0
        reserved = system_tokens + tools_tokens + 200
        available = max(0, max_tokens - reserved)

        messages = [{"role": m["role"], "content": m["content"]} for m in recent]
        messages.append({"role": "user", "content": current_prompt})
        truncated = self.truncate_to_fit(messages, available)

        memory_context = ""
        if memories:
            memory_lines = [f"- {m['key']}: {m['value']}" for m in memories]
            memory_context = "\n".join(memory_lines)

        doc_context = ""
        if docs:
            doc_lines = [f"[{d.get('title') or 'doc'}]: {(d.get('content') or '')[:500]}" for d in docs]
            doc_context = "\n".join(doc_lines)

        context_parts = [f"System: {system_prompt}"]
        if memory_context:
            context_parts.append(f"Memories:\n{memory_context}")
        if doc_context:
            context_parts.append(f"Knowledge:\n{doc_context}")
        if truncated:
            for m in truncated:
                context_parts.append(f"{m['role']}: {m['content']}")

        full_context = "\n\n".join(context_parts)

        return {
            "prompt": full_context,
            "system_prompt": system_prompt,
            "recent_messages": truncated,
            "memories": memories,
            "documents": docs,
            "tools": tools,
            "token_count": self.estimate_tokens(full_context) + tools_tokens,
            "max_tokens": max_tokens,
        }
