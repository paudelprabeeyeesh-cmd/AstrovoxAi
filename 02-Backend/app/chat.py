import json
import uuid
import logging
import asyncio
from datetime import datetime, timezone
from typing import Optional

from fastapi import WebSocket

from .database import get_db
from .schemas import MessageOut, ConversationOut, ConversationSearchOut
from .auth import get_current_user, require_verified_email
from .websocket_scaler import WebSocketScaler
from .core.llm import LLMClient
from .memory import search_memories
from .knowledge import search_docs
from .context_builder import ContextBuilder
from .cost import count_tokens
from .interactions import create_interaction
from .usage import record_usage
from .core.grounding import ground_answer
from .core.guardrails import sanitize_input, redact_pii, validate_output, add_canary
from .core.moderation import check_moderation
from .ab_runner import get_variant, record_result as record_ab_result
from .core.budget import cost_circuit_breaker
from .core.suggestions import SuggestionEngine
from .citations import create_citation, get_sources
from .circuit_breaker import llm_circuit_breaker
from .retry import retry_with_backoff

logger = logging.getLogger(__name__)


class ChatService:
    def __init__(self):
        self.llm = LLMClient()
        self.context_builder = ContextBuilder()
        self.ws_scaler = WebSocketScaler()

    async def create_conversation(self, user_id: str, title: Optional[str] = None) -> dict:
        conv_id = str(uuid.uuid4())
        with get_db() as conn:
            conn.execute(
                "INSERT INTO conversations (id, user_id, title) VALUES (?, ?, ?)",
                (conv_id, user_id, title),
            )
            conn.commit()
        return {
            "id": conv_id,
            "title": title,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

    async def add_message(self, conversation_id: str, role: str, content: str, user_id: str) -> dict:
        with get_db() as conn:
            row = conn.execute(
                "SELECT id FROM conversations WHERE id = ? AND user_id = ?",
                (conversation_id, user_id),
            ).fetchone()
            if not row:
                raise ValueError("Conversation not found")
            msg_id = str(uuid.uuid4())
            conn.execute(
                "INSERT INTO messages (id, conversation_id, role, content) VALUES (?, ?, ?, ?)",
                (msg_id, conversation_id, role, content),
            )
            conn.commit()
        return {
            "id": msg_id,
            "role": role,
            "content": content,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

    async def get_conversation_history(self, conversation_id: str, user_id: str) -> list[dict]:
        with get_db() as conn:
            row = conn.execute(
                "SELECT id FROM conversations WHERE id = ? AND user_id = ?",
                (conversation_id, user_id),
            ).fetchone()
            if not row:
                raise ValueError("Conversation not found")
            rows = conn.execute(
                "SELECT m.id, m.role, m.content, m.created_at FROM messages m WHERE m.conversation_id = ? ORDER BY m.created_at ASC",
                (conversation_id,),
            ).fetchall()
            return [
                {
                    "id": r["id"],
                    "role": r["role"],
                    "content": r["content"],
                    "created_at": r["created_at"],
                }
                for r in rows
            ]

    async def list_conversations(self, user_id: str) -> list[dict]:
        with get_db() as conn:
            rows = conn.execute(
                "SELECT id, title, created_at FROM conversations WHERE user_id = ? ORDER BY created_at DESC",
                (user_id,),
            ).fetchall()
            return [
                {
                    "id": r["id"],
                    "title": r["title"],
                    "created_at": r["created_at"],
                }
                for r in rows
            ]

    async def search_conversations(self, user_id: str, query: str) -> list[dict]:
        q = query.lower()
        with get_db() as conn:
            rows = conn.execute(
                """
                SELECT c.id, c.title, c.created_at, COUNT(m.id) as message_count
                FROM conversations c
                LEFT JOIN messages m ON m.conversation_id = c.id
                WHERE c.user_id = ? AND (c.title LIKE ? OR EXISTS (
                    SELECT 1 FROM messages WHERE conversation_id = c.id AND content LIKE ?
                ))
                GROUP BY c.id
                ORDER BY c.created_at DESC
            """,
                (user_id, f"%{q}%", f"%{q}%"),
            ).fetchall()
            return [
                {
                    "id": r["id"],
                    "title": r["title"],
                    "created_at": r["created_at"],
                    "message_count": r["message_count"],
                }
                for r in rows
            ]

    async def send_message(self, user_id: str, text: str, conversation_id: Optional[str] = None) -> dict:
        from ..database import init_db
        init_db()

        sanitized, injection_detected = sanitize_input(text)
        if injection_detected:
            from ..audit import log_action
            log_action(
                user_id, "injection_attempt", json.dumps({"query": text[:100]})
            )

        moderated, flagged_category = check_moderation(sanitized)
        if moderated:
            return {
                "refused": True,
                "response": "Content was moderated.",
                "conversation_id": conversation_id,
                "provider": "moderation",
                "model": "moderation",
                "confidence": 0.0,
            }

        redacted = redact_pii(sanitized)
        prompt_with_canary = add_canary(redacted)

        memories = search_memories(user_id, text, limit=3)
        docs = search_docs(user_id, text, limit=3)
        full_prompt = self.context_builder.build_context(user_id, prompt_with_canary, max_tokens=128000)

        try:
            llm_result = llm_circuit_breaker.call(
                retry_with_backoff(self.llm.call_llm, max_retries=3, base_delay=1),
                full_prompt,
                timeout=30,
            )
            response_text = llm_result.get("text", "")
            provider = llm_result.get("provider", "unknown")
            model = llm_result.get("model", "unknown")
            tokens = llm_result.get("tokens", count_tokens(full_prompt, model=model))
        except Exception as e:
            logger.error(f"LLM call failed: {e}")
            response_text = "I encountered an error processing your request."
            provider = "error"
            model = "error"
            tokens = 0

        cleaned_response, canary_detected = validate_output(response_text)
        grounded_response, refused, confidence = ground_answer(cleaned_response, docs, text)

        if not conversation_id:
            conv = await self.create_conversation(user_id, title=text[:50])
            conversation_id = conv["id"]

        user_msg = await self.add_message(conversation_id, "user", text, user_id)
        bot_msg = await self.add_message(conversation_id, "assistant", grounded_response, user_id)

        cost = round(tokens * 0.00001, 6)
        record_usage(user_id, tokens, cost, model, False)

        ab_variant = get_variant("model-comparison", user_id)
        if ab_variant:
            record_ab_result("model-comparison", ab_variant, "cost", cost)

        prompt_hash = __import__("app.core.tracing", fromlist=["get_prompt_hash"]).get_prompt_hash(full_prompt)
        log_llm_call = __import__("app.core.tracing", fromlist=["log_llm_call"]).log_llm_call
        log_llm_call(
            prompt_hash=prompt_hash,
            model=model,
            tokens=tokens,
            cost=cost,
            latency_ms=0,
            cached=False,
        )

        cost_circuit_breaker.record_cost(user_id, cost)

        create_interaction(
            user_id=user_id,
            prompt=text,
            response=grounded_response,
            model=model,
            tokens=tokens,
            cost=cost,
            latency_ms=0,
        )

        return {
            "conversation_id": conversation_id,
            "message_id": bot_msg["id"],
            "response": grounded_response,
            "provider": provider,
            "model": model,
            "refused": refused,
            "confidence": confidence,
        }

    async def stream_message(self, user_id: str, text: str, conversation_id: Optional[str] = None):
        sanitized, injection_detected = sanitize_input(text)
        if injection_detected:
            from ..audit import log_action
            log_action(
                user_id, "injection_attempt", json.dumps({"query": text[:100]})
            )

        moderated, flagged_category = check_moderation(sanitized)
        if moderated:
            yield {"token": "", "error": "moderated", "flagged_category": flagged_category}
            return

        redacted = redact_pii(sanitized)
        prompt_with_canary = add_canary(redacted)

        memories = search_memories(user_id, text, limit=3)
        docs = search_docs(user_id, text, limit=3)
        full_prompt = self.context_builder.build_context(user_id, prompt_with_canary, max_tokens=128000)

        async for item in self.llm.stream_llm(full_prompt, timeout=60):
            yield item


chat_service = ChatService()
