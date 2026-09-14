import logging

logger = logging.getLogger(__name__)


class ContextManager:
    def __init__(self, max_tokens: int = 128000):
        self.max_tokens = max_tokens

    def summarize_context(self, context: str, max_length: int = 4000) -> str:
        if len(context) <= max_length:
            return context

        sentences = context.split(". ")
        summarized = []
        current_length = 0

        for sentence in sentences:
            if current_length + len(sentence) > max_length:
                break
            summarized.append(sentence)
            current_length += len(sentence)

        return ". ".join(summarized) + "..."

    def sliding_window(self, messages: list[dict], window_size: int = 10) -> list[dict]:
        if len(messages) <= window_size:
            return messages

        recent = messages[-window_size:]
        older = messages[:-window_size]

        older_summary = self._summarize_messages(older)

        return [
            {
                "role": "system",
                "content": f"Previous conversation summary: {older_summary}",
            }
        ] + recent

    def _summarize_messages(self, messages: list[dict]) -> str:
        if not messages:
            return ""

        combined = " ".join([m.get("content", "") for m in messages])
        return self.summarize_context(combined, max_length=1000)

    def fit_to_window(self, prompt: str, context: str, tokenizer_fn) -> tuple[str, str]:
        total_tokens = tokenizer_fn(prompt) + tokenizer_fn(context)

        if total_tokens <= self.max_tokens:
            return prompt, context

        overflow = total_tokens - self.max_tokens
        context_tokens = tokenizer_fn(context)

        if context_tokens > overflow:
            ratio = (context_tokens - overflow) / context_tokens
            keep_length = int(len(context) * ratio)
            context = context[:keep_length] + "..."

        return prompt, context
