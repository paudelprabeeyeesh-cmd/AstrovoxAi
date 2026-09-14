import os
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class OpenAIClient:
    def __init__(self, api_key: Optional[str] = None, model: str = "gpt-4o-mini-2024-07-18"):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY", "")
        self.model = model
        self._client = None
    
    def _get_client(self):
        if self._client is None:
            try:
                import openai
                self._client = openai.OpenAI(api_key=self.api_key)
            except Exception as e:
                logger.error(f"Failed to initialize OpenAI client: {e}")
                raise
        return self._client
    
    def generate(self, prompt: str) -> str:
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY is not configured")
        client = self._get_client()
        response = client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=1024,
            temperature=0.7,
        )
        return response.choices[0].message.content or ""


class MockLLMClient:
    def __init__(self, model: str = "mock"):
        self.model = model
    
    def generate(self, prompt: str) -> str:
        return f"[MOCK RESPONSE to: {prompt[:50]}...]"
