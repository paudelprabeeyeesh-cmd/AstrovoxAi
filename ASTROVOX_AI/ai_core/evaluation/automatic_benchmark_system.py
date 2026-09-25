from typing import Dict, Any, Optional, Callable
import time
import json


class AutomaticBenchmarkSystem:
    def __init__(self, model_name: str, model, tokenizer, tasks: Optional[Dict[str, Any]] = None):
        self.model_name = model_name
        self.model = model
        self.tokenizer = tokenizer
        self.tasks = tasks or {}
        self.results: Dict[str, Any] = {}

    def register_task(self, name: str, dataset, metric_fn: Callable, max_new_tokens: int = 100) -> None:
        self.tasks[name] = {'dataset': dataset, 'metric_fn': metric_fn, 'max_new_tokens': max_new_tokens}

    def run(self) -> Dict[str, Any]:
        for task_name, config in self.tasks.items():
            start = time.time()
            predictions = []
            references = []
            for sample in config['dataset']:
                input_ids = sample['input_ids'].unsqueeze(0)
                if hasattr(self.model, 'generate'):
                    output = self.model.generate(input_ids, max_new_tokens=config['max_new_tokens'])
                else:
                    output = self.model(input_ids)
                pred = self.tokenizer.decode(output[0].tolist())
                predictions.append(pred)
                references.append(sample.get('target', ''))
            latency = time.time() - start
            score = config['metric_fn'](predictions, references)
            self.results[task_name] = {'score': score, 'latency': latency, 'num_samples': len(predictions)}
        return self.results

    def save_results(self, path: str) -> None:
        with open(path, 'w', encoding='utf-8') as f:
            json.dump({'model': self.model_name, 'results': self.results}, f, indent=2)

    def compare(self, other_results: Dict[str, Any]) -> str:
        lines = [f"Comparison: {self.model_name}"]
        for task in self.results:
            if task in other_results:
                diff = self.results[task]['score'] - other_results[task]['score']
                lines.append(f"{task}: {self.results[task]['score']:.4f} vs {other_results[task]['score']:.4f} ({diff:+.4f})")
        return '\n'.join(lines)
