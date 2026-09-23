"""Google Gemini provider implementation."""

import os
from typing import Optional, AsyncIterator

from .base import AIProvider, ChatMessage, ChatResponse, ProviderConfig, EmbeddingVector


class GeminiProvider(AIProvider):
    """Google Gemini provider."""

    name = "gemini"
    supports_streaming = True

    def __init__(self, config: Optional[ProviderConfig] = None):
        if config is None:
            config = ProviderConfig(
                api_key=os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY"),
                timeout=120,
                max_retries=2,
            )
        super().__init__(config)
        self._client = None

    @property
    def client(self):
        if self._client is None:
            import google.generativeai as genai
            genai.configure(api_key=self.config.api_key)
            self._client = genai
        return self._client

    @property
    def is_configured(self) -> bool:
        return bool(self.config.api_key)

    def validate_model(self, model: str) -> bool:
        from .models import MODELS
        info = MODELS.get(model)
        return info is not None and info.provider == "gemini"

    async def chat(
        self,
        messages: list[ChatMessage],
        model: str,
        temperature: float = 0.7,
        max_tokens: int = 2000,
        system_prompt: Optional[str] = None,
    ) -> ChatResponse:
        if not self.is_configured:
            raise RuntimeError("Google API key not configured")

        genai = self.client

        history = []
        system_content = system_prompt

        for msg in messages:
            if msg.role == "system":
                system_content = msg.content
                continue
            role = "user" if msg.role == "user" else "model"
            history.append({"role": role, "parts": [msg.content]})

        generation_config = {
            "temperature": temperature,
            "max_output_tokens": max_tokens,
        }

        model_obj = genai.GenerativeModel(
            model_name=model,
            generation_config=generation_config,
            system_instruction=system_content,
        )

        chat = model_obj.start_chat(history=history[:-1] if history else [])
        last_message = history[-1]["parts"][0] if history else ""

        response = chat.send_message(last_message)

        return ChatResponse(
            content=response.text,
            model=model,
            tokens_used=None,
            finish_reason="stop",
            provider=self.name,
        )

    async def stream(
        self,
        messages: list[ChatMessage],
        model: str,
        temperature: float = 0.7,
        max_tokens: int = 2000,
        system_prompt: Optional[str] = None,
    ) -> AsyncIterator[str]:
        """Stream chat completion tokens from Gemini."""
        if not self.is_configured:
            raise RuntimeError("Google API key not configured")

        genai = self.client

        history = []
        system_content = system_prompt

        for msg in messages:
            if msg.role == "system":
                system_content = msg.content
                continue
            role = "user" if msg.role == "user" else "model"
            history.append({"role": role, "parts": [msg.content]})

        generation_config = {
            "temperature": temperature,
            "max_output_tokens": max_tokens,
        }

        model_obj = genai.GenerativeModel(
            model_name=model,
            generation_config=generation_config,
            system_instruction=system_content,
        )

        chat = model_obj.start_chat(history=history[:-1] if history else [])
        last_message = history[-1]["parts"][0] if history else ""

        response = chat.send_message(last_message, stream=True)

        for chunk in response:
            if chunk.text:
                yield chunk.text

    async def embed(
        self,
        texts: list[str],
        model: str = "models/embedding-001",
    ) -> list[EmbeddingVector]:
        """Generate embeddings using the Gemini Embedding API.

        Supports batch embedding with retry and timeout handling.
        """
        if not self.is_configured:
            raise RuntimeError("Google API key not configured")

        genai = self.client
        results: list[EmbeddingVector] = []

        for i in range(0, len(texts), 100):
            batch = texts[i : i + 100]
            try:
                response = genai.embed_content(
                    model=model,
                    content=batch if len(batch) > 1 else batch[0],
                )
                embedding = response["embedding"]
                if isinstance(embedding[0], list):
                    results.extend(
                        EmbeddingVector(vector=v, model=model) for v in embedding
                    )
                else:
                    results.append(EmbeddingVector(vector=embedding, model=model))
            except Exception as e:
                raise RuntimeError(f"Gemini embedding error: {self.sanitize_error(e)}") from e

        return results
