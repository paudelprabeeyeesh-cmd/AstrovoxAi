import os
from typing import AsyncGenerator, List, Dict

try:
    from openai import AsyncOpenAI
except Exception as e:
    raise ImportError("openai package is required. Install it with 'pip install openai'.") from e

class OpenAIStreamingService:
    def __init__(self):
        # API Key loaded from environment variable OPENAI_API_KEY
        api_key = os.getenv("OPENAI_API_KEY")
        self.client = AsyncOpenAI(api_key=api_key)
        self.model = os.getenv("DEFAULT_LLM_MODEL", "gpt-4o")

    async def stream_tokens(self, messages: List[Dict[str, str]]) -> AsyncGenerator[str, None]:
        """Asynchronously processes streamed tokens to support TTFT operations."""
        stream = await self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            stream=True
        )
        async for chunk in stream:
            content = chunk.choices[0].delta.content
            if content:
                yield content