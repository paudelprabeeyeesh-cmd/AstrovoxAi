from typing import Optional, Dict, List
import torch
import torch.nn as nn


class SyntheticDataGenerator:
    def __init__(self, model: nn.Module, tokenizer, device: str = 'cuda'):
        self.model = model
        self.tokenizer = tokenizer
        self.device = device
        self.model.to(device)
        self.model.eval()

    def generate(self, prompt: str, max_new_tokens: int = 100, temperature: float = 0.8, top_p: float = 0.9, num_return_sequences: int = 1) -> List[str]:
        inputs = torch.tensor(self.tokenizer.encode(prompt)).unsqueeze(0).to(self.device)
        with torch.no_grad():
            outputs = self.model.generate(inputs, max_new_tokens=max_new_tokens, temperature=temperature, top_p=top_p, do_sample=True, num_return_sequences=num_return_sequences, pad_token_id=self.tokenizer.pad_id())
        return [self.tokenizer.decode(output.tolist()) for output in outputs]

    def generate_with_filter(self, prompt: str, filter_fn: callable, max_new_tokens: int = 100, max_attempts: int = 10) -> Optional[str]:
        for _ in range(max_attempts):
            text = self.generate(prompt, max_new_tokens=max_new_tokens)[0]
            if filter_fn(text):
                return text
        return None

    def generate_dataset(self, prompts: List[str], num_per_prompt: int = 1, **kwargs) -> List[Dict[str, str]]:
        dataset = []
        for prompt in prompts:
            generated = self.generate(prompt, num_return_sequences=num_per_prompt, **kwargs)
            for text in generated:
                dataset.append({'prompt': prompt, 'completion': text})
        return dataset
