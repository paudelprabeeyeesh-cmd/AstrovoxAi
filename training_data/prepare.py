import os
import json
import argparse
from datasets import load_dataset


def prepare_wiki(path="data/wiki", split="train"):
    ds = load_dataset("wikimedia/wikipedia", "20231101.en", split=split, streaming=True)
    os.makedirs(path, exist_ok=True)
    with open(os.path.join(path, "wiki.txt"), "w", encoding="utf-8") as f:
        for example in ds:
            f.write(example["text"] + "\n\n")


def prepare_c4(path="data/c4", split="train"):
    ds = load_dataset("allenai/c4", "en", split=split, streaming=True)
    os.makedirs(path, exist_ok=True)
    with open(os.path.join(path, "c4.txt"), "w", encoding="utf-8") as f:
        for i, example in enumerate(ds):
            if i > 100000:
                break
            f.write(example["text"] + "\n\n")


def prepare_instructions(path="data/instructions.jsonl"):
    os.makedirs(os.path.dirname(path) if os.path.dirname(path) else ".", exist_ok=True)
    sample = [
        {"prompt": "What is the capital of France?", "completion": "The capital of France is Paris."},
        {"prompt": "Explain gravity.", "completion": "Gravity is the force that attracts objects with mass toward each other."},
    ]
    with open(path, "w", encoding="utf-8") as f:
        for item in sample:
            f.write(json.dumps(item) + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", choices=["wiki", "c4", "instructions"], required=True)
    args = parser.parse_args()
    if args.dataset == "wiki":
        prepare_wiki()
    elif args.dataset == "c4":
        prepare_c4()
    elif args.dataset == "instructions":
        prepare_instructions()
