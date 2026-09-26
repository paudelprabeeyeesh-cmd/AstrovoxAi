from typing import Optional, Dict, Any, List
import torch
import torch.nn as nn
import logging

logger = logging.getLogger(__name__)


class DebateRuntime:
    def __init__(self, model: nn.Module, num_rounds: int = 3):
        self.model = model
        self.num_rounds = num_rounds

    def run_debate(self, topic: str, positions: List[str]) -> List[Dict[str, Any]]:
        debate_history = []
        for round_idx in range(self.num_rounds):
            round_responses = []
            for position in positions:
                prompt = f"Debate round {round_idx + 1}. Position: {position}. Topic: {topic}"
                response = self._generate(prompt, position)
                round_responses.append({"position": position, "response": response, "round": round_idx})
            debate_history.append(round_responses)
        return debate_history

    def _generate(self, prompt: str, position: str) -> str:
        inputs = self.model.tokenizer(prompt, return_tensors='pt')
        with torch.no_grad():
            outputs = self.model.generate(**inputs, max_new_tokens=256, temperature=0.7)
        return self.model.tokenizer.decode(outputs[0], skip_special_tokens=True)

    def evaluate_debate(self, debate_history: List[Dict[str, Any]], judge_model: nn.Module) -> Dict[str, float]:
        scores = {}
        for round_data in debate_history:
            for entry in round_data:
                prompt = f"Evaluate this debate response: {entry['response']}"
                inputs = judge_model.tokenizer(prompt, return_tensors='pt')
                with torch.no_grad():
                    score = judge_model(**inputs).logits.softmax(dim=-1)[:, -1].mean().item()
                scores[entry['position']] = scores.get(entry['position'], 0) + score
        return {k: v / self.num_rounds for k, v in scores.items()}
