import logging

from .router import call_llm

logger = logging.getLogger(__name__)


class LLMClient:
    def __init__(self):
        self._active_providers = self._check_providers()

    def _check_providers(self) -> list[str]:
        from .providers import get_active_providers

        active = get_active_providers()
        if active:
            names = [p.name for p in active]
            logger.info(f"Active LLM providers: {names}")
            return names
        logger.error(
            "No AI provider configured. Set at least one of: "
            "GROQ_API_KEY, GEMINI_API_KEY, MISTRAL_API_KEY, "
            "OPENROUTER_API_KEY, HF_API_KEY."
        )
        return []

    def generate(self, prompt: str, system: str = "") -> str:
        if not self._active_providers:
            raise RuntimeError(
                "No AI provider configured. Set at least one of: "
                "GROQ_API_KEY, GEMINI_API_KEY, MISTRAL_API_KEY, "
                "OPENROUTER_API_KEY, HF_API_KEY."
            )
        result = call_llm(prompt, system=system)
        return result["text"]

    def call_llm(self, prompt: str, system: str = "") -> dict:
        if not self._active_providers:
            raise RuntimeError(
                "No AI provider configured. Set at least one of: "
                "GROQ_API_KEY, GEMINI_API_KEY, MISTRAL_API_KEY, "
                "OPENROUTER_API_KEY, HF_API_KEY."
            )
        return call_llm(prompt, system=system)
