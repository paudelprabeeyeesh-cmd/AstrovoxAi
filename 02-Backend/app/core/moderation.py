import logging
from typing import Optional
import openai

logger = logging.getLogger(__name__)

MODERATION_CATEGORIES = [
    "hate", "hate/threatening", "self-harm", "sexual", "sexual/minors",
    "violence", "violence/graphic"
]


def check_moderation(text: str) -> tuple[bool, Optional[str]]:
    try:
        client = openai.OpenAI()
        response = client.moderations.create(input=text)
        result = response.results[0]
        
        for category in MODERATION_CATEGORIES:
            if getattr(result.categories, category.replace("/", "_"), False):
                flagged = category.replace("_", "/")
                logger.warning(f"Content moderated: {flagged}")
                return True, flagged
        return False, None
    except Exception as e:
        logger.error(f"Moderation check failed: {e}")
        return False, None


def is_safe(text: str) -> bool:
    flagged, _ = check_moderation(text)
    return not flagged
