from typing import List, Dict, Optional


class HistorySummarizer:
    def __init__(self, recent_threshold: int = 4, summary_max_length: int = 500):
        if recent_threshold < 1:
            raise ValueError("recent_threshold must be at least 1")
        if summary_max_length < 1:
            raise ValueError("summary_max_length must be at least 1")
        self.recent_threshold = recent_threshold
        self.summary_max_length = summary_max_length
        self.summaries: List[Dict] = []

    def _summarize_text(self, text: str, max_length: int) -> str:
        if len(text) <= max_length:
            return text
        sentences = text.replace("? ", "?|").replace("! ", "!|").replace(". ", ".|").split("|")
        summarized = []
        current_length = 0
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
            if current_length + len(sentence) + 1 > max_length:
                break
            summarized.append(sentence)
            current_length += len(sentence) + 1
        return " ".join(summarized) + "..."

    def summarize(self, turns: List[Dict[str, str]]) -> List[Dict[str, str]]:
        if len(turns) <= self.recent_threshold:
            return list(turns)
        older = turns[:-self.recent_threshold]
        recent = turns[-self.recent_threshold:]
        combined = " ".join([f"{t.get('role', '')}: {t.get('content', '')}" for t in older])
        summary = self._summarize_text(combined, self.summary_max_length)
        result: List[Dict[str, str]] = [{"role": "system", "content": f"Summary: {summary}"}]
        result.extend(recent)
        self.summaries.append({"summary": summary, "turns": len(older)})
        return result

    def get_summary_count(self) -> int:
        return len(self.summaries)
