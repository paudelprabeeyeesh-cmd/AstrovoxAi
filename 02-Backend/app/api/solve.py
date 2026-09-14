import logging

from app.core.grounding import ground_answer
from app.core.guardrails import add_canary, sanitize_input, validate_output
from app.core.moderation import check_moderation
from app.core.pii import redact_pii, restore_pii
from app.core.tracing import get_prompt_hash, log_llm_call, start_trace

logger = logging.getLogger(__name__)


class Solver:
    def __init__(self, llm_client, cache_client=None):
        self.llm = llm_client
        self.cache = cache_client

    def solve(self, user_id: str, text: str, contexts: list[dict] = None) -> dict:
        with start_trace("solve", user_id, {"query_length": len(text)}):
            sanitized, injection_detected = sanitize_input(text)
            if injection_detected:
                logger.warning(f"Injection attempt from user {user_id}")

            moderated, flagged_category = check_moderation(sanitized)
            if moderated:
                return {
                    "result": "Request blocked by moderation.",
                    "model": "moderation",
                    "cached": False,
                    "flagged": True,
                    "category": flagged_category,
                }

            redacted = redact_pii(sanitized)
            prompt_with_canary = add_canary(redacted)

            response = self.llm.generate(prompt_with_canary)

            cleaned_response, canary_detected = validate_output(response)
            if canary_detected:
                logger.warning(f"Canary detected in response for user {user_id}")

            restored_response = restore_pii(cleaned_response)

            grounded_response, refused, confidence = ground_answer(
                restored_response, contexts or [], text
            )

            prompt_hash = get_prompt_hash(prompt_with_canary)
            log_llm_call(
                prompt_hash=prompt_hash,
                model=getattr(self.llm, "model", "unknown"),
                tokens=len(prompt_with_canary.split()),
                cost=0.0,
                latency_ms=0,
                cached=False,
            )

            return {
                "result": grounded_response,
                "model": getattr(self.llm, "model", "unknown"),
                "cached": False,
                "confidence": confidence,
                "refused": refused,
                "prompt_hash": prompt_hash,
            }
