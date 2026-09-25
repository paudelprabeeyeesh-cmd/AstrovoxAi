from typing import Optional, List, Dict, Any, Tuple
import re


class JailbreakDetector:
    def __init__(self):
        self.jailbreak_patterns = [
            r'DAN\s*\(',
            r'evil mode',
            r'without any moral',
            r'ignore all rules',
            r'act as if you have no',
            r'pretend you are an AI',
            r'bypass all',
            r'no restrictions',
            r'do anything now',
            r'developer mode enabled',
        ]
        self.compiled_patterns = [re.compile(p, re.IGNORECASE) for p in self.jailbreak_patterns]
        self.threshold = 0.5

    def detect(self, text: str) -> Tuple[bool, float, List[str]]:
        matches = []
        for pattern in self.compiled_patterns:
            if pattern.search(text):
                matches.append(pattern.pattern)
        score = len(matches) / len(self.compiled_patterns) if self.compiled_patterns else 0.0
        return score >= self.threshold, score, matches

    def classify_request(self, request: Dict[str, str]) -> Dict[str, Any]:
        text = request.get('content', '') or request.get('prompt', '')
        is_jailbreak, score, matches = self.detect(text)
        return {'is_jailbreak': is_jailbreak, 'score': score, 'matched_patterns': matches, 'action': 'block' if is_jailbreak else 'allow'}
