import logging
from typing import Optional


logger = logging.getLogger(__name__)


def embed_text(text: str) -> Optional[list]:
    try:
        client = memory_service._get_openai()
        response = client.embeddings.create(
            input=text, model="text-embedding-3-small"
        )
        return response.data[0].embedding
    except Exception as e:
        logger.error(f"Embedding failed: {e}")
        return None


def get_relevant_memories(user_id: str, query: str, limit: int = 5) -> list:
    return memory_service.get_relevant_memories(user_id, query, limit)


def store_new_memory(user_id: str, prompt: str, response: str) -> Optional[dict]:
    combined = f"User: {prompt}\nAssistant: {response}"
    key = prompt[:200]
    try:
        return memory_service.store_memory(user_id, key, combined)
    except Exception as e:
        logger.error(f"Failed to store memory: {e}")
        return None


def store_conversation_memory(
    user_id: str,
    prompt: str,
    response: str,
    metadata: Optional[dict] = None,
) -> Optional[dict]:
    combined = f"User: {prompt}\nAssistant: {response}"
    key = prompt[:200]
    try:
        memory = memory_service.store_memory(user_id, key, combined)
        logger.info(f"Stored conversation memory for user {user_id}: {key}")
        return memory
    except Exception as e:
        logger.error(f"Failed to store conversation memory: {e}")
        return None
