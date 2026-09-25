from typing import Optional, Dict, Any, List, Callable
import random
import json
from datetime import datetime


class HyperparameterSearch:
    def __init__(self, model_fn: Callable, search_space: Dict[str, List[Any], objective_fn: Callable, strategy: str = 'random'):
        self.model_fn = model_fn
        self.search_space = search_space
        self.objective_fn = objective_fn
        self.strategy = strategy
        self.results: List[Dict[str, Any]] = []
        self.best_params: Optional[Dict[str, Any]] = None
        self.best_score: float = float('-inf')

    def sample_config(self) -> Dict[str, Any]:
        config = {}
        for param, values in self.search_space.items():
            if isinstance(values, list):
                config[param] = random.choice(values)
            elif isinstance(values, dict) and 'min' in values and 'max' in values:
                import math
                if values.get('type') == 'log':
                    config[param] = math.exp(random.uniform(math.log(values['min']), math.log(values['max'])))
                else:
                    config[param] = random.uniform(values['min'], values['max'])
        return config

    def step(self, num_trials: int = 10) -> List[Dict[str, Any]]:
        trials = []
        for _ in range(num_trials):
            config = self.sample_config()
            model = self.model_fn(**config)
            score = self.objective_fn(model, config)
            trial = {'config': config, 'score': score, 'timestamp': datetime.now().isoformat()}
            trials.append(trial)
            self.results.append(trial)
            if score > self.best_score:
                self.best_score = score
                self.best_params = config
        return trials

    def get_best(self) -> Optional[Dict[str, Any]]:
        if not self.results:
            return None
        best = max(self.results, key=lambda x: x['score'])
        return {'config': best['config'], 'score': best['score']}

    def save_results(self, path: str) -> None:
        with open(path, 'w', encoding='utf-8') as f:
            json.dump({'best_params': self.best_params, 'best_score': self.best_score, 'results': self.results}, f, indent=2)
