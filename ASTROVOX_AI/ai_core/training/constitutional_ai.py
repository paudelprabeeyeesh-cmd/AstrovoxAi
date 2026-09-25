from typing import Optional, Dict, Any, List
import torch
import torch.nn as nn


class ConstitutionalAI:
    def __init__(self, model: nn.Module, principles: List[str], critic_model: Optional[nn.Module] = None):
        self.model = model
        self.principles = principles
        self.critic_model = critic_model

    def critique(self, text: str) -> Optional[str]:
        if self.critic_model is None:
            return None
        inputs = self._tokenize(text)
        with torch.no_grad():
            outputs = self.critic_model(inputs)
        return self._parse_critique(outputs)

    def revise(self, text: str, critique: Optional[str] = None) -> str:
        if critique:
            prompt = f"Original: {text}\nCritique: {critique}\nRevised:"
        else:
            prompt = f"Original: {text}\nRevised (adhering to principles {self.principles}):"
        inputs = self._tokenize(prompt)
        with torch.no_grad():
            outputs = self.model.generate(inputs, max_new_tokens=128)
        return self._decode(outputs)

    def _tokenize(self, text: str) -> torch.Tensor:
        return torch.tensor([[ord(c) for c in text]], dtype=torch.long)

    def _decode(self, tokens: torch.Tensor) -> str:
        return ''.join([chr(t) for t in tokens[0].tolist() if t < 256])
