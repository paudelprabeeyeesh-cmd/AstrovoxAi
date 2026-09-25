import logging
from typing import Any

from app.services.memory.memory_pipeline import get_relevant_memories
from app.services.knowledge.knowledge import search_docs
from .cost import count_tokens
from app.repositories.database.client import get_db
from .core.llm import LLMClient
from ...tools import get_builtin_tools
from .thinking import ThinkingConfig

logger = logging.getLogger(__name__)


class ContextBuilder:
    def __init__(self, llm_client: LLMClient | None = None):
        self.llm_client = llm_client or LLMClient()

    def estimate_tokens(self, text: str) -> int:
        return count_tokens(text)

    def get_system_prompt(self, user_id: str, include_canary: bool = True) -> str:
        base = (
            "You are AstrovoxAI, a helpful, harmless, and honest AI assistant. "
            "Be concise and accurate. Use tools when needed."
        )
        if include_canary:
            from .core.guardrails import add_canary
            base = add_canary(base)
        return base

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

    def summarize_if_needed(self, messages: list[dict], max_tokens: int) -> list[dict]:
        total = sum(self.estimate_tokens(m.get("content", "") or "") for m in messages)
        if total <= max_tokens:
            return messages
        keep = messages[-8:]
        summary_input = "\n".join([f"{m['role']}: {m['content'][:200]}" for m in messages[:-8]])
        try:
            summary_text = self.llm_client.call_llm(
                prompt=f"Summarize this conversation history concisely:\n{summary_input}",
                timeout=30,
            ).get("text", summary_input[:500])
        except Exception:
            summary_text = summary_input[:500]
        return [{"role": "system", "content": f"[Summary of earlier conversation: {summary_text}]"}] + keep

    def build_context(
        self,
        user_id: str,
        current_prompt: str,
        max_tokens: int = 128000,
        include_tools: bool = True,
        thinking: Optional[ThinkingConfig] = None,
        compact: bool = False,
    ) -> dict[str, Any]:
        system_prompt = self.get_system_prompt(user_id, include_canary=True)
        recent = self.get_recent_messages(user_id, limit=20)
        memories = self.get_relevant_memories(user_id, current_prompt, limit=5)
        docs = self.get_relevant_documents(user_id, current_prompt, limit=3)
        tools = self.get_tool_schemas() if include_tools else []

        system_tokens = self.estimate_tokens(system_prompt)
        tools_tokens = self.estimate_tokens(str(tools)) if tools else 0
        thinking_budget = 0
        if thinking and thinking.enabled:
            thinking_budget = thinking.budget_tokens or 4096
        reserved = system_tokens + tools_tokens + thinking_budget + 200
        available = max(0, max_tokens - reserved)

        messages = [{"role": m["role"], "content": m["content"]} for m in recent]
        messages.append({"role": "user", "content": current_prompt})

        if compact:
            messages = self.summarize_if_needed(messages, available)
        else:
            messages = self.truncate_to_fit(messages, available)

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
        if messages:
            for m in messages:
                context_parts.append(f"{m['role']}: {m['content']}")

        full_context = "\n\n".join(context_parts)
        token_count = self.estimate_tokens(full_context) + tools_tokens + thinking_budget

        return {
            "prompt": full_context,
            "system_prompt": system_prompt,
            "recent_messages": messages,
            "memories": memories,
            "documents": docs,
            "tools": tools,
            "token_count": token_count,
            "max_tokens": max_tokens,
            "thinking": thinking.to_anthropic_params() if thinking else {},
        }
