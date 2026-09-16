import logging
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)


class SuggestionEngine:
    def __init__(self):
        self.suggestion_templates = [
            "Review flashcards on {topic}",
            "Continue studying {topic}",
            "Practice quiz on {topic}",
            "Revisit {topic} from last week",
            "Try a harder problem in {topic}",
        ]

    def generate(self, user_id: str, recent_topics: list[str], hour: int | None = None) -> list[str]:
        if hour is None:
            hour = datetime.now(timezone.utc).hour
        suggestions = []
        for topic in recent_topics[:3]:
            import random
            template = random.choice(self.suggestion_templates)
            suggestions.append(template.format(topic=topic))
        if 6 <= hour <= 9:
            suggestions.insert(0, "Start your day with a quick review")
        elif 20 <= hour <= 23:
            suggestions.insert(0, "Wind down with a summary quiz")
        return suggestions[:5]

    def analyze_struggle_patterns(self, interactions: list[dict]) -> list[str]:
        struggles = []
        for item in interactions:
            prompt = item.get("prompt", "").lower()
            if any(kw in prompt for kw in ["error", "wrong", "fail", "stuck"]):
                struggles.append(item.get("prompt", "")[:100])
        return struggles
