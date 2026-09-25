import os
import logging
import re

from ...config import settings

logger = logging.getLogger(__name__)


class ContextCompressor:
    def __init__(self):
        self._client = None

    def _get_client(self):
        if self._client is None:
            import openai
            self._client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
        return self._client

    def compress(self, context: str, max_tokens: int) -> str:
        estimated = self.estimate_tokens(context)
        if estimated <= max_tokens:
            return context
        return self._llm_compress(context, max_tokens)

    def extract_important(self, context: str, query: str) -> str:
        try:
            client = self._get_client()
            response = client.chat.completions.create(
                model=os.getenv("COMPRESSION_MODEL", "gpt-4o-mini-2024-07-18"),
                messages=[
                    {"role": "system", "content": "Extract only the sentences most relevant to the query. Return them verbatim separated by newlines."},
                    {"role": "user", "content": f"Query: {query}\n\nContext:\n{context}"},
                ],
                max_tokens=512,
                temperature=0.0,
            )
            return response.choices[0].message.content or context
        except Exception as e:
            logger.error(f"LLM extraction failed: {e}")
            return self._heuristic_extract(context, query)

    def estimate_tokens(self, text: str) -> int:
        try:
            import tiktoken
            encoding = tiktoken.get_encoding("cl100k_base")
            return len(encoding.encode(text))
        except Exception:
            return max(1, len(text) // 4)

    def _llm_compress(self, context: str, max_tokens: int) -> str:
        try:
            client = self._get_client()
            response = client.chat.completions.create(
                model=os.getenv("COMPRESSION_MODEL", "gpt-4o-mini-2024-07-18"),
                messages=[
                    {"role": "system", "content": f"Compress the following context to under {max_tokens} tokens while preserving key facts. Return only the compressed text."},
                    {"role": "user", "content": context},
                ],
                max_tokens=max_tokens,
                temperature=0.0,
            )
            return response.choices[0].message.content or context
        except Exception as e:
            logger.error(f"LLM compression failed: {e}")
            return self._heuristic_compress(context, max_tokens)

    def _heuristic_extract(self, context: str, query: str) -> str:
        terms = set(query.lower().split())
        sentences = re.split(r'(?<=[.!?])\s+', context)
        scored = []
        for sentence in sentences:
            score = sum(1 for t in terms if t in sentence.lower())
            scored.append((score, sentence))
        scored.sort(key=lambda x: x[0], reverse=True)
        return " ".join(s for _, s in scored[:10])

    def _heuristic_compress(self, context: str, max_tokens: int) -> str:
        tokens_estimate = self.estimate_tokens(context)
        ratio = max_tokens / max(tokens_estimate, 1)
        keep = max(1, int(len(context) * ratio))
        return context[:keep]
