import argparse
import csv
import json
import math
import os
import random
import sys
from pathlib import Path

import torch
import torch.nn.functional as F
from torch.utils.data import Subset, DataLoader

from models.llm.model.model import LLM
from models.llm.tokenizer.train_tokenizer import load_tokenizer, TextDataset, collate_fn
from models.llm.utils.helpers import load_config, get_device, set_cpu_threads
from models.llm.inference.generate import generate

try:
    sys.stdout.reconfigure(errors="replace")
except Exception:
    pass


def ensure_determinism(seed: int = 42):
    random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False
    torch.use_deterministic_algorithms(True, warn_only=True)


@torch.no_grad()
def evaluate(model, dataloader, device):
    model.eval()
    total_loss = 0.0
    total_tokens = 0
    correct = 0
    for batch in dataloader:
        input_ids = batch["input_ids"].to(device, non_blocking=True)
        labels = batch["labels"].to(device, non_blocking=True)
        outputs = model(input_ids, labels=labels, use_gradient_checkpointing=False)
        loss = outputs["loss"].item()
        logits = outputs["logits"]
        total_loss += loss * labels.numel()
        total_tokens += labels.numel()
        preds = logits.argmax(dim=-1)
        mask = labels != -100
        correct += (preds[mask] == labels[mask]).sum().item()
    avg_loss = total_loss / max(total_tokens, 1)
    accuracy = correct / max(total_tokens, 1)
    try:
        ppl = math.exp(min(avg_loss, 80))
    except OverflowError:
        ppl = float("inf")
    return avg_loss, ppl, accuracy


def load_latest_checkpoint(model, checkpoint_dir, device):
    ckpts = []
    if os.path.isdir(checkpoint_dir):
        for f in os.listdir(checkpoint_dir):
            if f.endswith(".pt"):
                ckpts.append(os.path.join(checkpoint_dir, f))
    if not ckpts:
        raise FileNotFoundError(f"No checkpoints found in {checkpoint_dir}")
    ckpts.sort(key=lambda p: os.path.getmtime(p))
    latest = ckpts[-1]
    print(f"Loading checkpoint: {latest}")
    state = torch.load(latest, map_location=device, weights_only=False)
    model.load_state_dict(state["model_state_dict"])
    return state


def main(config_path="models/llm/configs/config_100m.yaml", checkpoint_dir=None, output_dir=None):
    ensure_determinism(seed=42)
    config = load_config(config_path)
    device = get_device()
    if device == "cpu":
        set_cpu_threads(min(4, os.cpu_count() or 2))

    dtype = torch.float32
    mp = config.get("mixed_precision", "none")
    if mp == "bf16" and hasattr(torch, "bfloat16"):
        dtype = torch.bfloat16
    elif mp == "fp16" and device == "cuda":
        dtype = torch.float16

    output_dir = output_dir or config.get("output_dir", "model.pt")
    checkpoint_dir = checkpoint_dir or os.path.join(os.path.dirname(output_dir) if os.path.dirname(output_dir) else ".", "phase1_checkpoints")

    model = LLM(config, device=torch.device(device), dtype=dtype)
    load_latest_checkpoint(model, checkpoint_dir, device)

    tokenizer_path = config.get("tokenizer_path", "tokenizer.json")
    tokenizer = load_tokenizer(tokenizer_path)
    pad_token_id = tokenizer.token_to_id("<pad>") or 0

    train_file = config.get("train_file", "data/train.txt")
    block_size = config.get("max_position_embeddings", 1024)
    dataset = TextDataset(train_file, tokenizer, block_size=block_size)
    n = len(dataset)
    g = torch.Generator().manual_seed(42)
    indices = torch.randperm(n, generator=g).tolist()
    split = int(n * 0.9)
    train_dataset = Subset(dataset, indices[:split])
    val_dataset = Subset(dataset, indices[split:])
    train_loader = DataLoader(train_dataset, batch_size=max(1, config.get("batch_size", 2)//2), shuffle=False, num_workers=0, collate_fn=lambda b: collate_fn(b, pad_token_id), drop_last=False)
    val_loader = DataLoader(val_dataset, batch_size=max(1, config.get("batch_size", 2)//2), shuffle=False, num_workers=0, collate_fn=lambda b: collate_fn(b, pad_token_id), drop_last=False)

    train_loss, train_ppl, train_acc = evaluate(model, train_loader, device)
    val_loss, val_ppl, val_acc = evaluate(model, val_loader, device)

    print("=" * 60)
    print(f"Train loss:      {train_loss:.4f}")
    print(f"Train perplexity:{train_ppl:.2f}")
    print(f"Train accuracy:  {train_acc:.4f}")
    print(f"Val loss:        {val_loss:.4f}")
    print(f"Val perplexity:  {val_ppl:.2f}")
    print(f"Val accuracy:    {val_acc:.4f}")
    print("=" * 60)

    log_dir = os.path.join(os.path.dirname(output_dir) if os.path.dirname(output_dir) else ".", "phase1_logs")
    train_csv = os.path.join(log_dir, "training_metrics.csv")
    if os.path.exists(train_csv):
        with open(train_csv, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        if rows:
            initial = float(rows[0]["train_loss"])
            final = float(rows[-1]["train_loss"])
            print(f"Initial training loss from log: {initial:.4f}")
            print(f"Final training loss from log:   {final:.4f}")
            if final < initial:
                print("Convergence check: PASSED")
            else:
                print("Convergence check: FAILED")

    print("\nGenerating 5 samples:")
    prompts = [
        "Astrovox is",
        "The model learns",
        "Phase one focuses on",
        "Transformers use attention",
        "Gradient descent optimizes",
    ]
    generations = []
    for p in prompts:
        try:
            out = generate(model, tokenizer, p, max_new_tokens=60, temperature=0.8, top_k=40, device=device)
        except Exception as e:
            out = f"[gen_error] {e}"
        generations.append(out)
        print(f"Prompt: {p}")
        print(f"Gen:    {out}\n")

    # Memorization check: evaluate on training data vs shuffled nonsense
    dummy_text = " ".join(["token" + str(i % 1000) for i in range(block_size * 40)])
    dummy_path = os.path.join(os.path.dirname(output_dir) if os.path.dirname(output_dir) else ".", "phase1_dummy_eval.txt")
    with open(dummy_path, "w", encoding="utf-8") as f:
        f.write(dummy_text)
    dummy_dataset = TextDataset(dummy_path, tokenizer, block_size=block_size)
    dummy_loader = DataLoader(dummy_dataset, batch_size=max(1, config.get("batch_size", 2)//2), shuffle=False, num_workers=0, collate_fn=lambda b: collate_fn(b, pad_token_id), drop_last=False)
    dummy_loss, dummy_ppl, _ = evaluate(model, dummy_loader, device)
    print(f"Dummy eval loss:   {dummy_loss:.4f}")
    print(f"Dummy eval ppl:    {dummy_ppl:.2f}")
    ratio = train_ppl / max(dummy_ppl, 1e-6)
    print(f"Train ppl / Dummy ppl ratio: {ratio:.2f}")
    if ratio < 5.0:
        print("Memorization check: FAILED (model assigns similar perplexity to nonsense)")
    else:
        print("Memorization check: PASSED (model strongly prefers real text over nonsense)")

    if os.path.exists(dummy_path):
        os.remove(dummy_path)

    print("\nEvaluation complete.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Phase 1 evaluation harness")
    parser.add_argument("--config", default="models/llm/configs/config_phase1.yaml")
    parser.add_argument("--checkpoint-dir", default=None)
    parser.add_argument("--output-dir", default=None)
    args = parser.parse_args()
    main(config_path=args.config, checkpoint_dir=args.checkpoint_dir, output_dir=args.output_dir)
