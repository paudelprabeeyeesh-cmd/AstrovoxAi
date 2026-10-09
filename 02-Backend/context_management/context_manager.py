from typing import List, Dict, Optional


class ContextManager:
    def __init__(self, max_tokens: int = 4000):
        if max_tokens < 1:
            raise ValueError("max_tokens must be at least 1")
        self.max_tokens = max_tokens
        self.turns: List[Dict[str, str]] = []
        self.system_prompt: Optional[str] = None

    def set_system_prompt(self, prompt: str) -> None:
        self.system_prompt = prompt

    def add_turn(self, role: str, content: str) -> Dict[str, str]:
        turn = {"role": role, "content": content}
        self.turns.append(turn)
        return turn

    def get_context(self) -> List[Dict[str, str]]:
        context: List[Dict[str, str]] = []
        if self.system_prompt:
            context.append({"role": "system", "content": self.system_prompt})
        context.extend(self.turns)
        return context

    def clear(self) -> None:
        self.turns.clear()

    def token_count(self) -> int:
        return sum(len(turn.get("content", "").split()) for turn in self.get_context())

    def truncate(self) -> None:
        while self.token_count() > self.max_tokens and len(self.turns) > 0:
            self.turns.pop(0)
