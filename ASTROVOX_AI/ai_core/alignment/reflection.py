from typing import Dict, Any, List, Tuple
import torch
import torch.nn as nn
import logging

logger = logging.getLogger(__name__)


class ReflectionTrainer:
    def __init__(self, model: nn.Module, reflection_model: nn.Module):
        self.model = model
        self.reflection_model = reflection_model

    def reflect(self, prompt: str, response: str) -> Dict[str, Any]:
        reflection_prompt = f"Reflect on the following response.\nPrompt: {prompt}\nResponse: {response}\nReflection:"
        inputs = self.reflection_model.tokenizer(reflection_prompt, return_tensors='pt')
        with torch.no_grad():
            outputs = self.reflection_model.generate(**inputs, max_new_tokens=256)
        reflection = self.reflection_model.tokenizer.decode(outputs[0], skip_special_tokens=True)
        return {"reflection": reflection, "prompt": prompt, "response": response}

    def improved_response(self, prompt: str, response: str, reflection: str) -> str:
        improved_prompt = f"Using the reflection, generate an improved response.\nPrompt: {prompt}\nOriginal: {response}\nReflection: {reflection}\nImproved:"
        inputs = self.model.tokenizer(improved_prompt, return_tensors='pt')
        with torch.no_grad():
            outputs = self.model.generate(**inputs, max_new_tokens=256)
        return self.model.tokenizer.decode(outputs[0], skip_special_tokens=True)

    def run_reflection_loop(self, prompt: str, max_iterations: int = 3) -> Tuple[str, List[str]]:
        response = self._generate(prompt)
        reflections = []
        for _ in range(max_iterations):
            reflection_result = self.reflect(prompt, response)
            reflections.append(reflection_result['reflection'])
            improved = self.improved_response(prompt, response, reflection_result['reflection'])
            if improved.strip().lower() == response.strip().lower():
                break
            response = improved
        return response, reflections

    def _generate(self, prompt: str) -> str:
        inputs = self.model.tokenizer(prompt, return_tensors='pt')
        with torch.no_grad():
            outputs = self.model.generate(**inputs, max_new_tokens=256)
        return self.model.tokenizer.decode(outputs[0], skip_special_tokens=True)
