"""
Automated hyperparameter search with Bayesian optimization and population-based training.
"""

from __future__ import annotations

import logging
import random
from typing import Optional, Dict, Any, List, Tuple
import torch.nn as nn

logger = logging.getLogger(__name__)


class BayesianOptimizer:
    def __init__(self, search_space: Dict[str, Any], objective_fn: callable, num_iterations: int = 50):
        self.search_space = search_space
        self.objective_fn = objective_fn
        self.num_iterations = num_iterations
        self.observations: List[Tuple[Dict[str, Any], float]] = []

    def suggest(self) -> Dict[str, Any]:
        return {param: random.uniform(values['min'], values['max']) if isinstance(values, dict) and values.get('type') == 'float' else random.randint(values['min'], values['max']) if isinstance(values, dict) and values.get('type') == 'int' else random.choice(values['choices']) if isinstance(values, dict) and values.get('type') == 'choice' else random.choice(values) for param, values in self.search_space.items()}

    def optimize(self) -> Tuple[Dict[str, Any], float]:
        best_config = None
        best_score = float('-inf')
        for _ in range(self.num_iterations):
            config = self.suggest()
            score = self.objective_fn(config)
            self.observations.append((config, score))
            if score > best_score:
                best_score = score
                best_config = config
        return best_config, best_score


class PopulationBasedTraining:
    def __init__(self, model_factory: callable, search_space: Dict[str, Any], population_size: int = 8):
        self.model_factory = model_factory
        self.search_space = search_space
        self.population_size = population_size
        self.population: List[Tuple[nn.Module, Dict[str, Any], float]] = []

    def initialize_population(self) -> None:
        self.population = []
        for _ in range(self.population_size):
            config = {param: random.uniform(values['min'], values['max']) if isinstance(values, dict) and values.get('type') == 'float' else random.randint(values['min'], values['max']) if isinstance(values, dict) and values.get('type') == 'int' else random.choice(values['choices']) if isinstance(values, dict) and values.get('type') == 'choice' else random.choice(values) for param, values in self.search_space.items()}
            model = self.model_factory(config)
            self.population.append((model, config, 0.0))

    def exploit_and_explore(self, fraction: float = 0.2) -> None:
        self.population.sort(key=lambda x: x[2], reverse=True)
        top_count = max(1, int(self.population_size * fraction))
        top_models = self.population[:top_count]
        for i in range(top_count, self.population_size):
            parent_model, parent_config, _ = random.choice(top_models)
            new_config = parent_config.copy()
            for param in self.search_space:
                if random.random() < 0.3:
                    values = self.search_space[param]
                    if isinstance(values, dict):
                        if values.get('type') == 'float':
                            new_config[param] = max(values['min'], min(values['max'], new_config[param] * random.uniform(0.8, 1.2)))
                        elif values.get('type') == 'int':
                            new_config[param] = random.randint(values['min'], values['max'])
            new_model = self.model_factory(new_config)
            self.population[i] = (new_model, new_config, 0.0)

    def get_best(self) -> Tuple[Optional[nn.Module], Optional[Dict[str, Any]], float]:
        if not self.population:
            return None, None, 0.0
        self.population.sort(key=lambda x: x[2], reverse=True)
        return self.population[0]
