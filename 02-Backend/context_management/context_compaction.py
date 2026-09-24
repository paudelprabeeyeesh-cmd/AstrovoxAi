from typing import List, Dict, Optional
from .history_summarization import HistorySummarizer


class ContextCompactor:
    def __init__(self, checkpoint_interval: int = 10, max_context_tokens: int = 4000):
        if checkpoint_interval < 1:
            raise ValueError("checkpoint_interval must be at least 1")
        if max_context_tokens < 1:
            raise ValueError("max_context_tokens must be at least 1")
        self.checkpoint_interval = checkpoint_interval
        self.max_context_tokens = max_context_tokens
        self.checkpoints: List[Dict] = []
        self.turn_count = 0
        self.summarizer = HistorySummarizer(recent_threshold=2, summary_max_length=500)

    def add_turn(self, turn: Dict[str, str]) -> Optional[Dict]:
        self.turn_count += 1
        result = None
        if self.turn_count % self.checkpoint_interval == 0:
            result = self._create_checkpoint()
        return result

    def _create_checkpoint(self) -> Dict:
        checkpoint = {
            "turn": self.turn_count,
            "tokens": self._estimate_tokens(self.current_context),
            "summary": self.summarizer._summarize_text(self.current_context, self.max_context_tokens // 2),
        }
        self.checkpoints.append(checkpoint)
        return checkpoint

    def __init__(self, checkpoint_interval: int = 10, max_context_tokens: int = 4000):
        if checkpoint_interval < 1:
            raise ValueError("checkpoint_interval must be at least 1")
        if max_context_tokens < 1:
            raise ValueError("max_context_tokens must be at least 1")
        self.checkpoint_interval = checkpoint_interval
        self.max_context_tokens = max_context_tokens
        self.checkpoints: List[Dict] = []
        self.turn_count = 0
        self.current_context = ""
        self.summarizer = HistorySummarizer(recent_threshold=2, summary_max_length=500)

    def add_turn(self, turn: Dict[str, str]) -> Optional[Dict]:
        self.turn_count += 1
        role = turn.get("role", "user")
        content = turn.get("content", "")
        self.current_context += f" {role}: {content}"
        result = None
        if self.turn_count % self.checkpoint_interval == 0:
            result = self._create_checkpoint()
        return result

    def _estimate_tokens(self, text: str) -> int:
        return max(1, len(text.split()))

    def _create_checkpoint(self) -> Dict:
        checkpoint = {
            "turn": self.turn_count,
            "tokens": self._estimate_tokens(self.current_context),
            "summary": self.summarizer._summarize_text(self.current_context, self.max_context_tokens // 2),
        }
        self.checkpoints.append(checkpoint)
        return checkpoint

    def compact(self, turns: List[Dict[str, str]]) -> List[Dict[str, str]]:
        if len(turns) <= self.checkpoint_interval:
            return list(turns)
        return self.summarizer.summarize(turns)

    def get_checkpoint_count(self) -> int:
        return len(self.checkpoints)
