import logging

from .core.llm import LLMClient

logger = logging.getLogger(__name__)


class ConversationSummarizer:
    def __init__(self, llm_client: LLMClient | None = None, keep_last_n: int = 6):
        self.llm_client = llm_client or LLMClient()
        self.keep_last_n = keep_last_n

    def summarize_conversation(self, messages: list[dict]) -> str:
        if not messages:
            return ""
        if len(messages) <= self.keep_last_n:
            return ""
        to_summarize = messages[:-self.keep_last_n]
        combined = "\n".join([f"{m.get('role', '')}: {m.get('content', '')}" for m in to_summarize])
        prompt = (
            "Summarize the following conversation concisely, preserving key facts, decisions, and context:\n\n"
            f"{combined}\n\nSummary:"
        )
        try:
            result = self.llm_client.call_llm(prompt, system="You are a summarization assistant.", timeout=30)
            return result.get("text", "")
        except Exception as e:
            logger.error(f"Summarization failed: {e}")
            return ""

