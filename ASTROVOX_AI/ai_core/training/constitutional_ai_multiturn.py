from typing import Optional, Dict, List, Tuple
import torch
import torch.nn as nn


class MultiTurnConstitutionalAI:
    def __init__(self, model: nn.Module, principles: List[str], critic_model: Optional[nn.Module] = None, max_turns: int = 3, safety_threshold: float = 0.7):
        self.model = model
        self.principles = principles
        self.critic_model = critic_model
        self.max_turns = max_turns
        self.safety_threshold = safety_threshold
        self.conversation_history: List[Dict[str, str]] = []

    def critique(self, text: str, turn: int = 0) -> Optional[str]:
        if self.critic_model is None:
            return None
        principle = self.principles[turn % len(self.principles)]
        critique_prompt = f"Principle: {principle}\n\nResponse: {text}\n\nCritique: Does this response violate the principle? If so, explain how."
        inputs = self._tokenize(critique_prompt)
        with torch.no_grad():
            outputs = self.critic_model(inputs)
        return self._parse_critique(outputs)

    def revise(self, text: str, critique: Optional[str] = None, turn: int = 0) -> str:
        principle = self.principles[turn % len(self.principles)]
        if critique:
            prompt = f"Principle: {principle}\nOriginal: {text}\nCritique: {critique}\nRevised (adhering to principle):"
        else:
            prompt = f"Principle: {principle}\nOriginal: {text}\nRevised (adhering to principle):"
        inputs = self._tokenize(prompt)
        with torch.no_grad():
            outputs = self.model.generate(inputs, max_new_tokens=256)
        return self._decode(outputs)

    def run_multi_turn_pipeline(self, prompt: str, initial_response: str) -> Tuple[str, List[Dict[str, str]]]:
        current_response = initial_response
        self.conversation_history = []
        for turn in range(self.max_turns):
            critique = self.critique(current_response, turn)
            revised = self.revise(current_response, critique, turn)
            turn_record = {'turn': turn, 'prompt': prompt, 'response': current_response, 'critique': critique or '', 'revised': revised}
            self.conversation_history.append(turn_record)
            safety_score = self._compute_safety_score(revised)
            if safety_score >= self.safety_threshold:
                current_response = revised
            else:
                break
        return current_response, self.conversation_history

    def _compute_safety_score(self, text: str) -> float:
        if self.critic_model is None:
            return 1.0
        inputs = self._tokenize(text)
        with torch.no_grad():
            outputs = self.critic_model(inputs)
        score = torch.sigmoid(outputs[:, -1, :].mean()).item()
        return score

    def _tokenize(self, text: str) -> torch.Tensor:
        return torch.tensor([[ord(c) for c in text[:1024]]], dtype=torch.long)

    def _decode(self, tokens: torch.Tensor) -> str:
        return ''.join([chr(t) for t in tokens[0].tolist() if 0 < t < 256])
