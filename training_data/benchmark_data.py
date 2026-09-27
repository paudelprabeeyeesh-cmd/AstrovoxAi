import os
from typing import Optional


def prepare_mmlu(split: str = "test", limit: Optional[int] = None):
    from datasets import load_dataset
    ds = load_dataset("cais/mmlu", "all", split=split, streaming=True)
    os.makedirs("training_data/benchmarks", exist_ok=True)
    path = "training_data/benchmarks/mmlu.jsonl"
    with open(path, "w", encoding="utf-8") as f:
        for i, example in enumerate(ds):
            if limit is not None and i >= limit:
                break
            f.write(__import__("json").dumps(example) + "\n")
    return path


def prepare_hellaswag(split: str = "validation", limit: Optional[int] = None):
    from datasets import load_dataset
    ds = load_dataset("Rowan/hellaswag", split=split, streaming=True)
    os.makedirs("training_data/benchmarks", exist_ok=True)
    path = "training_data/benchmarks/hellaswag.jsonl"
    with open(path, "w", encoding="utf-8") as f:
        for i, example in enumerate(ds):
            if limit is not None and i >= limit:
                break
            f.write(__import__("json").dumps(example) + "\n")
    return path


def prepare_winogrande(split: str = "validation", limit: Optional[int] = None):
    from datasets import load_dataset
    ds = load_dataset("winogrande", "winogrande_xl", split=split, streaming=True)
    os.makedirs("training_data/benchmarks", exist_ok=True)
    path = "training_data/benchmarks/winogrande.jsonl"
    with open(path, "w", encoding="utf-8") as f:
        for i, example in enumerate(ds):
            if limit is not None and i >= limit:
                break
            f.write(__import__("json").dumps(example) + "\n")
    return path


def prepare_truthfulqa(split: str = "validation", limit: Optional[int] = None):
    from datasets import load_dataset
    ds = load_dataset("truthful_qa", "generation", split=split, streaming=True)
    os.makedirs("training_data/benchmarks", exist_ok=True)
    path = "training_data/benchmarks/truthfulqa.jsonl"
    with open(path, "w", encoding="utf-8") as f:
        for i, example in enumerate(ds):
            if limit is not None and i >= limit:
                break
            f.write(__import__("json").dumps(example) + "\n")
    return path


def prepare_perplexity_corpus(path: str = "training_data/benchmarks/perplexity_corpus.txt", limit: Optional[int] = None):
    from datasets import load_dataset
    ds = load_dataset("wikimedia/wikipedia", "20231101.en", split="train", streaming=True)
    os.makedirs(os.path.dirname(path) if os.path.dirname(path) else ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for i, example in enumerate(ds):
            if limit is not None and i >= limit:
                break
            f.write(example["text"] + "\n\n")
    return path


PREPARE_FUNCTIONS = {
    "mmlu": prepare_mmlu,
    "hellaswag": prepare_hellaswag,
    "winogrande": prepare_winogrande,
    "truthfulqa": prepare_truthfulqa,
    "perplexity": prepare_perplexity_corpus,
}


def prepare_benchmark(name: str, **kwargs):
    if name not in PREPARE_FUNCTIONS:
        raise KeyError(f"Unknown benchmark dataset: {name}. Available: {list(PREPARE_FUNCTIONS.keys())}")
    return PREPARE_FUNCTIONS[name](**kwargs)


def prepare_all(limit: Optional[int] = 500):
    results = {}
    for name in PREPARE_FUNCTIONS:
        results[name] = prepare_benchmark(name, limit=limit)
    return results
