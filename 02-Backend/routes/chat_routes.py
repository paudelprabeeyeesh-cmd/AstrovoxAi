"""
Astravox AI — routes/chat_routes.py
Stable conversational API with prompt assembly, memory, and streaming support.
Enhanced with logging, validation, and error handling.
"""
import os
import sys
import traceback
from functools import wraps
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime

from flask import Blueprint, request, jsonify, session, Response, stream_with_context

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_ROOT = os.path.dirname(BASE_DIR)
PROJECT_ROOT = os.path.dirname(BACKEND_ROOT)
AI_LOGIC_PATH = os.path.join(PROJECT_ROOT, "AI-Integration")

if AI_LOGIC_PATH not in sys.path:
    sys.path.insert(0, AI_LOGIC_PATH)

sys.path.insert(0, BACKEND_ROOT)

from database.database import (
    save_chat_message,
    check_limit,
    increment_usage,
    get_user_usage,
    get_conversation_history,
)
from utils.logger import chat_logger, app_logger
from utils.validators import require_json, require_fields, sanitize_string, ValidationError

try:
    import ai_logic.ai_router as ai_router
except ImportError:
    ai_router = None

try:
    import ai_logic.memory as ai_memory
except ImportError:
    ai_memory = None

chat_bp = Blueprint("chat", __name__, url_prefix="/chat")

get_history = getattr(ai_memory, "get_history", None)
save_message_pair = getattr(ai_memory, "save_message_pair", None)
get_ai_stream = getattr(ai_router, "get_ai_stream", None)
get_ai_response = getattr(ai_router, "get_ai_response", None)
build_prompt = getattr(ai_router, "build_prompt", None)


def _ai_stream(user_message: str, conversation_history: List[Dict[str, Any]], memory_history: List[Dict[str, Any]] = None, **kwargs):
    """Stream AI responses with fallback."""
    if get_ai_stream:
        try:
            yield from get_ai_stream(user_message, conversation_history, memory_history, **kwargs)
            return
        except Exception as e:
            chat_logger.error(f"AI streaming error: {e}", exc_info=True)
    yield "[AI service unavailable. Please ensure GEMINI_API_KEY is configured and google-generativeai is installed.]"


def _ai_response(user_message: str, conversation_history: List[Dict[str, Any]], memory_history: List[Dict[str, Any]] = None, **kwargs) -> str:
    """Get complete AI response with error handling."""
    if get_ai_response:
        try:
            return get_ai_response(user_message, conversation_history, memory_history, **kwargs)
        except Exception as e:
            chat_logger.error(f"AI response error: {e}", exc_info=True)
    return "".join(_ai_stream(user_message, conversation_history, memory_history, **kwargs))


def _resolve_user() -> Tuple[Optional[str], str, str, bool]:
    """Resolve user from session or demo mode."""
    demo_mode = os.getenv("DEMO_MODE", "0") == "1"
    demo_header = str(request.headers.get("X-DEMO-MODE", "0")) == "1"
    is_local = request.remote_addr in ("127.0.0.1", "::1", "::ffff:127.0.0.1")
    demo_mode = demo_mode or (demo_header and is_local)
    user_id = session.get("user_id") or ("demo_user" if demo_mode else None)
    username = session.get("username", "Anonymous")
    subscription = session.get("subscription", "free")
    
    chat_logger.debug(f"User resolved: {user_id} (demo={demo_mode}, sub={subscription})")
    return user_id, username, subscription, demo_mode


def _save_history(conversation_id: str, user_id: str, user_message: str, assistant_message: str) -> None:
    """Save conversation to both memory systems."""
    try:
        if save_message_pair:
            save_message_pair(conversation_id, user_message, assistant_message)
            chat_logger.debug(f"Saved to AI memory: {conversation_id}")
    except Exception as e:
        chat_logger.warning(f"Failed to save to AI memory: {e}")
    
    try:
        save_chat_message(conversation_id, user_id, "user", user_message)
        save_chat_message(conversation_id, user_id, "assistant", assistant_message)
        chat_logger.debug(f"Saved to database: {conversation_id}")
    except Exception as e:
        chat_logger.warning(f"Failed to save to database: {e}")


# Route handlers below


@chat_bp.route("/message", methods=["POST"])
@require_json
@require_fields("message", "conversation_id")
def message() -> Tuple[Dict[str, Any], int]:
    """Send a message and get a complete response."""
    data = request.get_json() or {}
    
    try:
        user_message = sanitize_string(data.get("message", ""), max_length=5000).strip()
        conversation_id = sanitize_string(data.get("conversation_id", ""), max_length=100).strip()
        
        if not user_message:
            chat_logger.warning("Empty message received")
            return jsonify({
                "status": "ERROR",
                "error": "Message cannot be empty.",
                "code": "EMPTY_MESSAGE"
            }), 400
        
        if not conversation_id:
            chat_logger.warning("Missing conversation_id")
            return jsonify({
                "status": "ERROR",
                "error": "conversation_id is required.",
                "code": "MISSING_CONVERSATION_ID"
            }), 400

        user_id, username, subscription, _ = _resolve_user()
        if not user_id:
            chat_logger.warning("Unauthenticated message attempt")
            return jsonify({
                "status": "ERROR",
                "error": "Authentication required.",
                "code": "AUTH_REQUIRED"
            }), 401

        can_ask, used, limit = check_limit(user_id, subscription, "questions")
        if not can_ask:
            chat_logger.warning(f"Rate limit exceeded for {user_id}: {used}/{limit}")
            return jsonify({
                "status": "ERROR",
                "error": f"Daily limit reached ({used}/{limit}).",
                "code": "RATE_LIMIT",
                "limit_reached": True,
                "usage": {"used": used, "limit": limit}
            }), 429

        chat_logger.info(f"📨 Message from {username}: {conversation_id} [{len(user_message)} chars]")

        conversation_history = get_conversation_history(conversation_id)
        memory_history = get_history(conversation_id) if get_history else []
        
        try:
            final_response = _ai_response(user_message, conversation_history, memory_history)
        except Exception as exc:
            chat_logger.error(f"AI response error: {exc}", exc_info=True)
            final_response = f"[Error generating response: {str(exc)[:100]}]"

        _save_history(conversation_id, user_id, user_message, final_response)
        increment_usage(user_id, "questions")

        chat_logger.info(f"💬 Response sent: {conversation_id} [{len(final_response)} chars]")

        return jsonify({
            "status": "OK",
            "conversation_id": conversation_id,
            "response": final_response,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "usage": {"used": used + 1, "limit": limit}
        }), 200
        
    except ValidationError as ve:
        chat_logger.warning(f"Validation error: {ve}")
        return jsonify({
            "status": "ERROR",
            "error": str(ve),
            "code": "VALIDATION_ERROR"
        }), 400
    except Exception as exc:
        chat_logger.error(f"Message route error: {exc}", exc_info=True)
        return jsonify({
            "status": "ERROR",
            "error": "Internal server error",
            "detail": str(exc)
        }), 500


@chat_bp.route("/stream", methods=["POST"])
@require_json
@require_fields("message", "conversation_id")
def stream_message() -> Response:
    """Stream AI response in real-time."""
    data = request.get_json() or {}
    
    try:
        user_message = sanitize_string(data.get("message", ""), max_length=5000).strip()
        conversation_id = sanitize_string(data.get("conversation_id", ""), max_length=100).strip()

        if not user_message or not conversation_id:
            chat_logger.warning("Stream: Invalid request (empty message or conv_id)")
            return jsonify({
                "status": "ERROR",
                "error": "Message and conversation_id are required.",
                "code": "INVALID_REQUEST"
            }), 400

        user_id, username, subscription, _ = _resolve_user()
        if not user_id:
            chat_logger.warning("Stream: Unauthenticated attempt")
            return jsonify({
                "status": "ERROR",
                "error": "Authentication required.",
                "code": "AUTH_REQUIRED"
            }), 401

        can_ask, used, limit = check_limit(user_id, subscription, "questions")
        if not can_ask:
            chat_logger.warning(f"Stream: Rate limit exceeded for {user_id}: {used}/{limit}")
            return jsonify({
                "status": "ERROR",
                "error": f"Daily limit reached ({used}/{limit}).",
                "code": "RATE_LIMIT",
                "limit_reached": True,
                "usage": {"used": used, "limit": limit}
            }), 429

        chat_logger.info(f"🔴 Streaming from {username}: {conversation_id}")

        conversation_history = get_conversation_history(conversation_id)
        memory_history = get_history(conversation_id) if get_history else []

        def generate():
            chunks = []
            try:
                for chunk in _ai_stream(user_message, conversation_history, memory_history):
                    if chunk:
                        chunks.append(chunk)
                        yield chunk
            except Exception as exc:
                chat_logger.error(f"Stream error: {exc}", exc_info=True)
                yield f"\n\n[Streaming error: {str(exc)[:100]}]"
            finally:
                combined = "".join(chunks).strip()
                if combined:
                    try:
                        _save_history(conversation_id, user_id, user_message, combined)
                        increment_usage(user_id, "questions")
                        chat_logger.info(f"✅ Stream complete: {conversation_id} [{len(combined)} chars]")
                    except Exception as e:
                        chat_logger.error(f"Failed to save stream: {e}")

        return Response(stream_with_context(generate()), content_type="text/plain; charset=utf-8")
        
    except ValidationError as ve:
        chat_logger.warning(f"Stream: Validation error: {ve}")
        return jsonify({
            "status": "ERROR",
            "error": str(ve),
            "code": "VALIDATION_ERROR"
        }), 400
    except Exception as exc:
        chat_logger.error(f"Stream route error: {exc}", exc_info=True)
        return jsonify({
            "status": "ERROR",
            "error": "Internal server error",
            "detail": str(exc)
        }), 500


@chat_bp.route('/history/<conversation_id>', methods=['GET'])
def history(conversation_id: str) -> Tuple[Dict[str, Any], int]:
    """Get conversation history."""
    try:
        conversation_id = sanitize_string(conversation_id, max_length=100)
        
        if not conversation_id:
            return jsonify({
                "status": "ERROR",
                "error": "conversation_id is required.",
                "code": "MISSING_CONVERSATION_ID"
            }), 400

        conversation_history = get_conversation_history(conversation_id)
        chat_logger.debug(f"History retrieved: {conversation_id} [{len(conversation_history)} messages]")
        
        return jsonify({
            "status": "OK",
            "conversation_id": conversation_id,
            "history": conversation_history,
            "message_count": len(conversation_history)
        }), 200
        
    except Exception as exc:
        chat_logger.error(f"History retrieval error: {exc}", exc_info=True)
        return jsonify({
            "status": "ERROR",
            "error": "Failed to retrieve history",
            "detail": str(exc)
        }), 500


@chat_bp.route('/health', methods=['GET'])
def health() -> Tuple[Dict[str, Any], int]:
    """Health check for chat service."""
    try:
        from database.database import get_db
        conn = get_db()
        conn.execute("SELECT 1")
        conn.close()
        
        ai_available = get_ai_response is not None
        memory_available = get_history is not None
        
        chat_logger.debug("Health check passed")
        
        return jsonify({
            "status": "OK",
            "service": "astravox-chat",
            "alive": True,
            "ai_available": ai_available,
            "memory_available": memory_available,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }), 200
    except Exception as exc:
        chat_logger.error(f"Health check failed: {exc}", exc_info=True)
        return jsonify({
            "status": "ERROR",
            "service": "astravox-chat",
            "error": str(exc)
        }), 503
