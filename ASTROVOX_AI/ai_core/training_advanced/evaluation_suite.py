from typing import Optional, Dict, Any, List, Callable
import torch
import torch.nn as nn
from ASTROVOX_AI.ai_core.distributed.distributed_scheduler import DistributedScheduler, DistributedTask


class EvaluationSuite:
    def __init__(self, model: nn.Module, tokenizer, device: str = 'cuda'):
        self.model = model
        self.tokenizer = tokenizer
        self.device = device
        self.suites: Dict[str, List[Dict[str, Any]]] = {}
        self.results: Dict[str, List[Dict[str, Any]]] = {}

    def register_suite(self, name: str, tasks: List[Dict[str, Any]]) -> None:
        self.suites[name] = tasks

    def add_task(self, suite_name: str, task_name: str, dataset, metric_fn: Callable, max_new_tokens: int = 100) -> None:
        if suite_name not in self.suites:
            self.suites[suite_name] = []
        self.suites[suite_name].append({'name': task_name, 'dataset': dataset, 'metric_fn': metric_fn, 'max_new_tokens': max_new_tokens})

    def run_suite(self, suite_name: str) -> List[Dict[str, Any]]:
        if suite_name not in self.suites:
            return []
        results = []
        for task in self.suites[suite_name]:
            result = self._run_task(task)
            results.append(result)
        self.results[suite_name] = results
        return results

    def _run_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        predictions = []
        references = []
        self.model.eval()
        with torch.no_grad():
            for sample in task['dataset']:
                input_ids = sample['input_ids'].unsqueeze(0).to(self.device)
                output = self.model(input_ids)
                pred = self.tokenizer.decode(output[0].tolist())
                predictions.append(pred)
                references.append(sample.get('target', ''))
        score = task['metric_fn'](predictions, references)
        return {'task_name': task['name'], 'score': score, 'num_samples': len(predictions)}

    def compare(self, suite_name: str, previous_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        current = self.results.get(suite_name, [])
        comparison = {}
        for curr, prev in zip(current, previous_results):
            diff = curr.get('score', 0) - prev.get('score', 0)
            comparison[curr['task_name']] = {'current': curr.get('score'), 'previous': prev.get('score'), 'delta': diff}
        return comparison
