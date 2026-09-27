# Evaluation API Reference

## `models.llm.evaluation.benchmarks.EvaluationHarness`

Run benchmarks against a model.

```python
EvaluationHarness(model, tokenizer, model_name="model", device="cpu")
```

### Methods

#### `run_benchmark(name: str, max_samples=1000) -> BenchmarkResult`

Run a single benchmark by name.

#### `evaluate(benchmark_names, max_samples=1000, output_path=None) -> dict`

Run multiple benchmarks and return a report.

#### `quick_eval(output_path=None) -> dict`

Run a standard quick evaluation suite.

## Built-in Benchmarks

| Name | Class | Type |
|------|-------|------|
| `mmlu` | `MMLUBenchmark` | Multiple choice |
| `hellaswag` | `HellaSwagBenchmark` | Multiple choice |
| `arc` | `ARCBenchmark` | Multiple choice |
| `gsm8k` | `GSM8KBenchmark` | Math reasoning |
| `humaneval` | `HumanEvalBenchmark` | Code generation |
| `mbpp` | `MBPPBenchmark` | Code generation |
| `piqa` | `PIQABenchmark` | Physical reasoning |
| `boolq` | `BoolQBenchmark` | Reading comprehension |
| `winogrande` | `WinograndeBenchmark` | Coreference resolution |

## Synthetic Benchmarks

| Name | Description |
|------|-------------|
| `synthetic_mmlu` | Offline MMLU-style questions |
| `synthetic_hellaswag` | Offline HellaSwag-style questions |
| `synthetic_gsm8k` | Offline GSM8K-style math problems |

## Data Classes

### `BenchmarkResult`

```python
BenchmarkResult(
    name: str,
    score: float,
    stderr: float,
    metadata: Dict[str, Any] = {}
)
```

## Helper Functions

#### `get_benchmark(name: str, **kwargs) -> BaseBenchmark`

Instantiate a benchmark by registry name.
