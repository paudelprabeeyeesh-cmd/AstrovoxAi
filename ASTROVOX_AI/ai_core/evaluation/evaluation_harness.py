from typing import Dict, Any, List, Optional, Callable
import torch
import torch.nn as nn
import time


class EvaluationHarness:
    def __init__(self, model: nn.Module, tokenizer, device: str = 'cuda'):
        self.model = model
        self.tokenizer = tokenizer
        self.device = device
        self.results: Dict[str, Any] = {}

    def evaluate_task(self, task_name: str, dataset, metric_fn: Callable, max_new_tokens: int = 100) -> Dict[str, Any]:
        self.model.eval()
        predictions = []
        references = []
        start_time = time.time()
        with torch.no_grad():
            for sample in dataset:
                input_ids = sample['input_ids'].unsqueeze(0).to(self.device)
                output = self.model.generate(input_ids, max_new_tokens=max_new_tokens) if hasattr(self.model, 'generate') else self.model(input_ids)
                pred = self.tokenizer.decode(output[0].tolist())
                predictions.append(pred)
                references.append(sample.get('target', ''))
        latency = time.time() - start_time
        score = metric_fn(predictions, references)
        self.results[task_name] = {'score': score, 'latency': latency, 'num_samples': len(predictions)}
        return self.results[task_name]

    def run_benchmark(self, benchmarks: Dict[str, Any]) -> Dict[str, Any]:
        for name, config in benchmarks.items():
            self.evaluate_task(name, config['dataset'], config['metric_fn'], config.get('max_new_tokens', 100))
        return self.results

    def summarize(self) -> str:
        lines = ['Evaluation Summary']
        for task, result in self.results.items():
            lines.append(f"{task}: score={result['score']:.4f}, latency={result['latency']:.2f}s")
        return '\n'.join(lines)
