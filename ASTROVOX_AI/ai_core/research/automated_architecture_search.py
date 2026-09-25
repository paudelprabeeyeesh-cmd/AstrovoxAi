from typing import Optional, Dict, Any, List, Tuple
import torch
import torch.nn as nn
import random
import numpy as np


class AutomatedArchitectureSearch:
    def __init__(self, search_space: Dict[str, List[Any]], eval_fn: callable, population_size: int = 10, num_generations: int = 5):
        self.search_space = search_space
        self.eval_fn = eval_fn
        self.population_size = population_size
        self.num_generations = num_generations
        self.population: List[Dict[str, Any]] = []
        self.best_architecture: Optional[Dict[str, Any]] = None
        self.best_score: float = float('-inf')

    def sample_architecture(self) -> Dict[str, Any]:
        arch = {}
        for param, values in self.search_space.items():
            if isinstance(values, list):
                arch[param] = random.choice(values)
            elif isinstance(values, dict):
                if values.get('type') == 'int':
                    arch[param] = random.randint(values['min'], values['max'])
                elif values.get('type') == 'float':
                    arch[param] = random.uniform(values['min'], values['max'])
                elif values.get('type') == 'choice':
                    arch[param] = random.choice(values['choices'])
        return arch

    def build_model(self, arch: Dict[str, Any]) -> nn.Module:
        hidden_size = arch.get('hidden_size', 768)
        num_layers = arch.get('num_layers', 12)
        num_heads = arch.get('num_heads', 12)
        vocab_size = arch.get('vocab_size', 50257)
        config = type('Config', (), {**arch, 'hidden_size': hidden_size, 'num_layers': num_layers, 'num_heads': num_heads, 'vocab_size': vocab_size})()
        from ASTROVOX_AI.ai_core.transformers.transformer_from_scratch import TransformerFromScratch, TransformerConfig
        cfg = TransformerConfig(**{k: v for k, v in arch.items() if k in TransformerConfig.__init__.__code__.co_varnames})
        return TransformerFromScratch(cfg)

    def evaluate_population(self) -> List[Tuple[Dict[str, Any], float]]:
        scored = []
        for arch in self.population:
            model = self.build_model(arch)
            score = self.eval_fn(model, arch)
            scored.append((arch, score))
            if score > self.best_score:
                self.best_score = score
                self.best_architecture = arch
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored

    def evolve(self) -> Optional[Dict[str, Any]]:
        self.population = [self.sample_architecture() for _ in range(self.population_size)]
        for _ in range(self.num_generations):
            scored = self.evaluate_population()
            top_half = [arch for arch, score in scored[:self.population_size // 2]]
            self.population = top_half + [self.mutate(arch) for arch in top_half[:self.population_size // 2]]
        return self.best_architecture

    def mutate(self, arch: Dict[str, Any]) -> Dict[str, Any]:
        mutated = arch.copy()
        param = random.choice(list(mutated.keys()))
        values = self.search_space[param]
        if isinstance(values, list):
            mutated[param] = random.choice(values)
        elif isinstance(values, dict):
            if values.get('type') == 'int':
                mutated[param] = random.randint(values['min'], values['max'])
            elif values.get('type') == 'float':
                mutated[param] = random.uniform(values['min'], values['max'])
        return mutated
