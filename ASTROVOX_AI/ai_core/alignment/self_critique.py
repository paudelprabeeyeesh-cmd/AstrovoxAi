from typing import List, Tuple
import torch
import torch.nn as nn
import logging

logger = logging.getLogger(__name__)


class SelfCritique:
    def __init__(self, model: nn.Module, critique_model: nn.Module):
        self.model = model
        self.critique_model = critique_model

    def generate_critique(self, prompt: str, response: str) -> str:
        critique_prompt = f"Critique the following response to the prompt: {prompt}\nResponse: {response}\nCritique:"
        inputs = self.critique_model.tokenizer(critique_prompt, return_tensors='pt')
        with torch.no_grad():
            outputs = self.critique_model.generate(**inputs, max_new_tokens=256)
        return self.critique_model.tokenizer.decode(outputs[0], skip_special_tokens=True)

    def revise_response(self, prompt: str, original_response: str, critique: str) -> str:
        revision_prompt = f"Given the critique, revise your response.\nPrompt: {prompt}\nOriginal: {original_response}\nCritique: {critique}\nRevised:"
        inputs = self.model.tokenizer(revision_prompt, return_tensors='pt')
        with torch.no_grad():
            outputs = self.model.generate(**inputs, max_new_tokens=256)
        return self.model.tokenizer.decode(outputs[0], skip_special_tokens=True)

    def run_critique_loop(self, prompt: str, max_iterations: int = 3) -> Tuple[str, List[str]]:
        response = self._generate(prompt)
        critiques = []
        for _ in range(max_iterations):
            critique = self.generate_critique(prompt, response)
            critiques.append(critique)
            revised = self.revise_response(prompt, response, critique)
            if revised.strip().lower() == response.strip().lower():
                break
            response = revised
        return response, critiques

    def _generate(self, prompt: str) -> str:
        inputs = self.model.tokenizer(prompt, return_tensors='pt')
        with torch.no_grad():
            outputs = self.model.generate(**inputs, max_new_tokens=256)
        return self.model.tokenizer.decode(outputs[0], skip_special_tokens=True)
