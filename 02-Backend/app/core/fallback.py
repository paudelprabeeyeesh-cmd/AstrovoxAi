import logging

logger = logging.getLogger(__name__)


class OSSFallback:
    def __init__(self, model_name: str = "ollama/llama2"):
        self.model_name = model_name
        self.available = False

    def generate(self, prompt: str) -> str | None:
        try:
            import requests

            response = requests.post(
                "http://localhost:11434/api/generate",
                json={"model": self.model_name, "prompt": prompt, "stream": False},
                timeout=30,
            )
            if response.status_code == 200:
                return response.json().get("response", "")
        except Exception as e:
            logger.error(f"OSS fallback failed: {e}")
        return None


class GracefulDegradationChain:
    def __init__(self, primary_client, oss_fallback: OSSFallback, cache_client=None):
        self.primary = primary_client
        self.oss = oss_fallback
        self.cache = cache_client

    def generate(self, prompt: str, user_id: str) -> tuple[str, str]:
        try:
            response = self.primary.generate(prompt)
            if response:
                return response, "primary"
        except Exception as e:
            logger.warning(f"Primary LLM failed: {e}")

        try:
            response = self.oss.generate(prompt)
            if response:
                return response, "oss"
        except Exception as e:
            logger.warning(f"OSS fallback failed: {e}")

        if self.cache:
            cached = self.cache.get(user_id, prompt, "fallback")
            if cached:
                return cached.get("response", ""), "cache"

        return "Service temporarily unavailable. Please try again later.", "queue"
