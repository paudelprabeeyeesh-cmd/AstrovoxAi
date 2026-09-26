from typing import Optional, List, Dict
import re


class PromptInjectionDefense:
    def __init__(self):
        self.blocked_patterns = [
            r'ignore previous instructions',
            r'ignore all previous',
            r'pretend you are',
            r'act as if',
            r'you are now',
            r'forget your instructions',
            r'override',
            r'bypass',
            r'jailbreak',
            r'developer mode',
            r'DAN mode',
        ]
        self.compiled_patterns = [re.compile(p, re.IGNORECASE) for p in self.blocked_patterns]

    def detect_injection(self, text: str) -> Tuple[bool, Optional[str]]:
        for pattern in self.compiled_patterns:
            match = pattern.search(text)
            if match:
                return True, match.group()
        return False, None

    def sanitize(self, text: str) -> str:
        for pattern in self.compiled_patterns:
            text = pattern.sub('[REDACTED]', text)
        return text

    def filter_messages(self, messages: List[Dict[str, str]]) -> List[Dict[str, str]]:
        filtered = []
        for msg in messages:
            content = msg.get('content', '')
            is_injected, _ = self.detect_injection(content)
            if not is_injected:
                filtered.append(msg)
            else:
                filtered.append({'role': msg['role'], 'content': '[Content blocked due to injection attempt]'})
        return filtered
