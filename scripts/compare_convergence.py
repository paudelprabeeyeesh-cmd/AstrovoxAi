#!/usr/bin/env python3
"""Compare training convergence curves across model sizes."""

import argparse
import csv
import json
import math
import os
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


def find_log_dirs(base_dir="models/llm/logs"):
    base = Path(base_dir)
    if not base.exists():
        return []
    dirs = sorted([d for d in base.iterdir() if d.is_dir()])
    return dirs


def read_csv(path):
    rows = []
    if not os.path.exists(path):
        return rows
    with open(path, "r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)
    return rows


def load_model_info(config_path):
    try:
        sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
        from model.model_scaling import count_parameters, load_config

        cfg = load_config(config_path)
        num_params = count_parameters(
            vocab_size=int(cfg["vocab_size"]),
            hidden_size=int(cfg["hidden_size"]),
            num_hidden_layers=int(cfg["num_hidden_layers"]),
            num_attention_heads=int(cfg["num_attention_heads"]),
            intermediate_size=int(cfg["intermediate_size"]),
            max_position_embeddings=int(cfg.get("max_position_embeddings", 1024)),
            attention_bias=bool(cfg.get("attention_bias", False)),
            mlp_bias=bool(cfg.get("mlp_bias", False)),
            tie_weights=bool(cfg.get("tie_weights", True)),
            activation=str(cfg.get("activation", "swiglu")),
        )
        return {
            "params": num_params,
            "hidden": int(cfg["hidden_size"]),
            "layers": int(cfg["num_hidden_layers"]),
            "heads": int(cfg["num_attention_heads"]),
            "ffn": int(cfg["intermediate_size"]),
        }
    except Exception as e:
        return {"params": 0, "error": str(e)}


def compare_convergence(log_dirs, output_dir="models/llm/logs"):
    results = []
    for log_dir in log_dirs:
        name = log_dir.name
        train_csv = log_dir / "training_metrics.csv"
        val_csv = log_dir / "validation_metrics.csv"
        train_rows = read_csv(train_csv)
        val_rows = read_csv(val_csv)

        config_path = None
        for candidate in [
            f"models/llm/configs/config_{name}.yaml",
            f"models/llm/configs/config_{name.replace('m', 'M')}.yaml",
            f"models/llm/configs/config_{name.lower()}.yaml",
        ]:
            if os.path.exists(candidate):
                config_path = candidate
                break

        info = load_model_info(config_path) if config_path else {"params": 0}

        train_steps = []
        train_losses = []
        for row in train_rows:
            try:
                train_steps.append(int(row["step"]))
                train_losses.append(float(row["train_loss"]))
            except ValueError, KeyError:
                pass

        val_steps = []
        val_losses = []
        for row in val_rows:
            try:
                val_steps.append(int(row["step"]))
                val_losses.append(float(row["val_loss"]))
            except ValueError, KeyError:
                pass

        results.append(
            {
                "name": name,
                "config_path": config_path,
                "train_steps": train_steps,
                "train_losses": train_losses,
                "val_steps": val_steps,
                "val_losses": val_losses,
                **info,
            }
        )

    if not results:
        print("No training logs found.")
        return

    p_label = lambda n: f"{n/1e6:.0f}M" if n < 1e9 else f"{n/1e9:.1f}B"

    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    fig.suptitle("Training Convergence Comparison", fontsize=14)

    ax_train = axes[0, 0]
    ax_val = axes[0, 1]
    ax_ppl = axes[1, 0]
    ax_tps = axes[1, 1]

    colors = plt.cm.tab10(np.linspace(0, 1, len(results)))

    for idx, res in enumerate(results):
        label = f"{res['name']} ({p_label(res.get('params', 0))})"
        c = colors[idx]
        if res["train_steps"]:
            ax_train.plot(
                res["train_steps"], res["train_losses"], label=label, color=c, linewidth=1.5
            )
        if res["val_steps"] and res["val_losses"]:
            ax_val.plot(
                res["val_steps"],
                res["val_losses"],
                label=label,
                color=c,
                linewidth=1.5,
                marker="o",
                markersize=3,
            )
        if res["val_steps"] and res["val_losses"]:
            ppls = [min(math.exp(min(vl, 80)), 1e6) for vl in res["val_losses"]]
            ax_ppl.plot(
                res["val_steps"],
                ppls,
                label=label,
                color=c,
                linewidth=1.5,
                marker="s",
                markersize=3,
            )
        if res["train_steps"]:
            tps = []
            train_csv_path = Path(log_dirs[idx]) / "training_metrics.csv"
            train_rows_full = read_csv(train_csv_path)
            for row in train_rows_full:
                try:
                    tps.append(float(row["tokens_per_sec"]))
                except ValueError, KeyError:
                    tps.append(None)
            valid = [(s, t) for s, t in zip(res["train_steps"], tps) if t is not None]
            if valid:
                xs, ys = zip(*valid)
                ax_tps.plot(xs, ys, label=label, color=c, linewidth=1.5)

    ax_train.set_title("Training Loss")
    ax_train.set_xlabel("Step")
    ax_train.set_ylabel("Loss")
    ax_train.legend(fontsize=8)
    ax_train.grid(True, alpha=0.3)

    ax_val.set_title("Validation Loss")
    ax_val.set_xlabel("Step")
    ax_val.set_ylabel("Loss")
    ax_val.legend(fontsize=8)
    ax_val.grid(True, alpha=0.3)

    ax_ppl.set_title("Validation Perplexity")
    ax_ppl.set_xlabel("Step")
    ax_ppl.set_ylabel("Perplexity")
    ax_ppl.set_yscale("log")
    ax_ppl.legend(fontsize=8)
    ax_ppl.grid(True, alpha=0.3)

    ax_tps.set_title("Training Throughput")
    ax_tps.set_xlabel("Step")
    ax_tps.set_ylabel("Tokens/sec")
    ax_tps.legend(fontsize=8)
    ax_tps.grid(True, alpha=0.3)

    plt.tight_layout()
    os.makedirs(output_dir, exist_ok=True)
    plot_path = os.path.join(output_dir, "convergence_comparison.png")
    plt.savefig(plot_path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"Convergence plot saved to {plot_path}")

    report_path = os.path.join(output_dir, "convergence_report.md")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("# Convergence Comparison Report\n\n")
        f.write(
            "| Model | Params | Init Train Loss | Final Train Loss | Best Val Loss | Final Val PPL | Train Steps |\n"
        )
        f.write(
            "|-------|--------|-----------------|------------------|---------------|---------------|-------------|\n"
        )
        for res in results:
            init_loss = res["train_losses"][0] if res["train_losses"] else float("nan")
            final_loss = res["train_losses"][-1] if res["train_losses"] else float("nan")
            best_val = min(res["val_losses"]) if res["val_losses"] else float("nan")
            final_ppl = (
                min(math.exp(min(res["val_losses"][-1], 80)), 1e6)
                if res["val_losses"]
                else float("nan")
            )
            steps = res["train_steps"][-1] if res["train_steps"] else 0
            p_label_str = p_label(res.get("params", 0))
            f.write(
                f"| {res['name']} | {p_label_str} | {init_loss:.4f} | {final_loss:.4f} | {best_val:.4f} | {final_ppl:.2f} | {steps} |\n"
            )
        f.write("\n")
        f.write("## Notes\n\n")
        f.write("- Lower loss and perplexity indicate better convergence.\n")
        f.write("- Higher tokens/sec indicates better training efficiency.\n")
        f.write("- All models use the same synthetic dataset for comparability.\n")
    print(f"Convergence report saved to {report_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Compare training convergence across model sizes")
    parser.add_argument(
        "--log-dir",
        default="models/llm/logs",
        help="Base directory containing model log subdirectories",
    )
    parser.add_argument(
        "--output-dir", default="models/llm/logs", help="Directory to save comparison outputs"
    )
    args = parser.parse_args()
    log_dirs = find_log_dirs(args.log_dir)
    compare_convergence(log_dirs, output_dir=args.output_dir)
