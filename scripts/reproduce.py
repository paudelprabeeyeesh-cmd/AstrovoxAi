#!/usr/bin/env python3
"""
Phase J Reproduction Script
One-click reproduction of the full training → resume → evaluate → export → inference → verify pipeline.
"""

import argparse
import hashlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path

import torch
import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
CONFIG_PATH = REPO_ROOT / "configs" / "versioned" / "config_phase1_v1.yaml"
RESUME_CHECKPOINT = REPO_ROOT / "phase1_checkpoints" / "ckpt_step_50.pt"
FINAL_MODEL = REPO_ROOT / "phase1_model.pt"
EXPORT_DIR = REPO_ROOT / "repro_export"
EXPECTED_METRICS_PATH = REPO_ROOT / "repro_expected_metrics.json"
REPRO_METRICS_PATH = REPO_ROOT / "repro_metrics.json"


def run_cmd(cmd, cwd=REPO_ROOT, check=True, capture=False):
    print(f"[run] {' '.join(str(c) for c in cmd)}")
    result = subprocess.run(
        cmd,
        cwd=str(cwd),
        check=check,
        capture_output=capture,
        text=True,
        shell=isinstance(cmd, str),
    )
    if capture:
        return result.stdout.strip()
    return result


def compute_file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def install_dependencies():
    print("\n[repro] Installing dependencies...")
    req = REPO_ROOT / "requirements.txt"
    if req.exists():
        run_cmd([sys.executable, "-m", "pip", "install", "--upgrade", "pip"])
        run_cmd([sys.executable, "-m", "pip", "install", "--no-deps", "-r", str(req)])
        run_cmd([sys.executable, "-m", "pip", "install", "pytest", "pyyaml"])
    else:
        run_cmd([sys.executable, "-m", "pip", "install", "torch", "pyyaml", "pytest"])
    print("[repro] Dependencies installed.")


def validate_config():
    print("\n[repro] Validating config...")
    assert CONFIG_PATH.exists(), f"Config not found: {CONFIG_PATH}"
    with open(CONFIG_PATH) as f:
        cfg = yaml.safe_load(f)
    required = ["vocab_size", "hidden_size", "num_hidden_layers", "batch_size", "epochs", "output_dir"]
    for k in required:
        assert k in cfg, f"Missing config key: {k}"
    print(f"[repro] Config OK: {CONFIG_PATH}")
    return cfg


def train_model(cfg):
    print("\n[repro] Training model (fresh)...")
    train_script = REPO_ROOT / "phase1_train.py"
    assert train_script.exists(), f"Training script not found: {train_script}"
    run_cmd([
        sys.executable, str(train_script),
        "--config", str(CONFIG_PATH),
    ])
    assert FINAL_MODEL.exists(), f"Final model not created: {FINAL_MODEL}"
    print(f"[repro] Training complete. Model at {FINAL_MODEL}")


def resume_training(cfg):
    print("\n[repro] Resuming training from checkpoint...")
    ckpt_dir = REPO_ROOT / cfg.get("checkpoint_dir", "phase1_checkpoints")
    ckpts = sorted(ckpt_dir.glob("*.pt")) if ckpt_dir.exists() else []
    assert ckpts, f"No checkpoints found in {ckpt_dir}"
    resume_ckpt = ckpts[-1]
    train_script = REPO_ROOT / "phase1_train.py"
    run_cmd([
        sys.executable, str(train_script),
        "--config", str(CONFIG_PATH),
        "--resume", str(resume_ckpt),
    ])
    print(f"[repro] Resume complete from {resume_ckpt}")


def evaluate_model(cfg):
    print("\n[repro] Evaluating model...")
    eval_script = REPO_ROOT / "phase1_evaluate.py"
    assert eval_script.exists(), f"Evaluation script not found: {eval_script}"
    ckpt_dir = REPO_ROOT / cfg.get("checkpoint_dir", "phase1_checkpoints")
    output = run_cmd([
        sys.executable, str(eval_script),
        "--config", str(CONFIG_PATH),
        "--checkpoint-dir", str(ckpt_dir),
        "--output-dir", str(FINAL_MODEL),
    ], capture=True)
    print(output)
    return output


def export_model(cfg):
    print("\n[repro] Exporting model...")
    export_script = REPO_ROOT / "models" / "llm" / "export.py"
    if not export_script.exists():
        print("[repro] Export module not found, skipping export.")
        return None
    EXPORT_DIR.mkdir(exist_ok=True)
    run_cmd([
        sys.executable, str(export_script),
    ], check=False)
    # Use export via direct Python API
    sys.path.insert(0, str(REPO_ROOT / "models" / "llm"))
    try:
        from export import export_model, ExportFormat
        from model.model import LLM
        from utils.helpers import load_config, get_device

        device = get_device()
        dtype = torch.float32
        model = LLM(cfg, device=torch.device(device), dtype=dtype)
        if FINAL_MODEL.exists():
            state = torch.load(str(FINAL_MODEL), map_location=device, weights_only=False)
            if isinstance(state, dict) and "model_state_dict" in state:
                state = state["model_state_dict"]
            model.load_state_dict(state, strict=False)
        model.eval()
        meta = export_model(model, cfg, EXPORT_DIR, format=ExportFormat.SAFETENSORS)
        print(f"[repro] Export complete: {EXPORT_DIR}  status={meta.validation_status}")
        return meta
    except Exception as e:
        print(f"[repro] Export skipped or failed: {e}")
        return None


def run_inference(cfg):
    print("\n[repro] Running inference...")
    inference_script = REPO_ROOT / "models" / "llm" / "inference" / "generate.py"
    if not inference_script.exists():
        print("[repro] Inference script not found, using inline generation.")
        sys.path.insert(0, str(REPO_ROOT / "models" / "llm"))
        from inference.generate import generate
        from tokenizer.train_tokenizer import load_tokenizer, create_dummy_tokenizer
        from utils.helpers import load_config as lc, get_device

        tokenizer_path = cfg.get("tokenizer_path", "tokenizer.json")
        if not Path(tokenizer_path).exists():
            create_dummy_tokenizer(save_dir=str(REPO_ROOT), vocab_size=cfg.get("vocab_size", 1000))
        tokenizer = load_tokenizer(tokenizer_path)
        device = get_device()
        dtype = torch.float32
        model = LLM(cfg, device=torch.device(device), dtype=dtype)
        if FINAL_MODEL.exists():
            state = torch.load(str(FINAL_MODEL), map_location=device, weights_only=False)
            if isinstance(state, dict) and "model_state_dict" in state:
                state = state["model_state_dict"]
            model.load_state_dict(state, strict=False)
        model.eval()

        prompts = [
            "Astrovox is",
            "The model learns",
            "Phase one focuses on",
            "Transformers use attention",
            "Gradient descent optimizes",
        ]
        generations = {}
        for p in prompts:
            try:
                out = generate(model, tokenizer, p, max_new_tokens=40, temperature=0.8, top_k=40, device=device)
            except Exception as e:
                out = f"[gen_error] {e}"
            generations[p] = out
            print(f"  Prompt: {p!r}")
            print(f"  Gen:    {out[:120]}")
        return generations

    output = run_cmd([
        sys.executable, str(inference_script),
        "--config", str(CONFIG_PATH),
        "--checkpoint", str(FINAL_MODEL),
        "--prompt", "Astrovox is",
    ], capture=True)
    print(output)
    return {"inline": output}


def verify_reproducibility(cfg, generations):
    print("\n[repro] Verifying reproducibility...")
    expected = {
        "phase1_final_train_loss_max": 3.0,
        "phase1_val_accuracy_min": 0.01,
        "inference_min_length": 10,
    }

    # Read training logs if available
    log_dir = REPO_ROOT / cfg.get("log_dir", "phase1_logs")
    train_csv = log_dir / "training_metrics.csv"
    val_csv = log_dir / "validation_metrics.csv"

    train_rows = []
    val_rows = []
    if train_csv.exists():
        import csv
        with open(train_csv, newline="", encoding="utf-8") as f:
            train_rows = list(csv.DictReader(f))
    if val_csv.exists():
        import csv
        with open(val_csv, newline="", encoding="utf-8") as f:
            val_rows = list(csv.DictReader(f))

    metrics = {
        "train_rows": len(train_rows),
        "val_rows": len(val_rows),
        "initial_train_loss": float(train_rows[0]["train_loss"]) if train_rows else None,
        "final_train_loss": float(train_rows[-1]["train_loss"]) if train_rows else None,
        "convergence_passed": False,
        "best_val_loss": float(val_rows[-1]["val_loss"]) if val_rows else None,
        "val_accuracy": float(val_rows[-1]["val_accuracy"]) if val_rows else None,
        "model_file_sha256": compute_file_sha256(FINAL_MODEL) if FINAL_MODEL.exists() else None,
        "config_sha256": compute_file_sha256(CONFIG_PATH),
        "generations": generations,
        "inference_min_length": min((len(v) for v in generations.values()), default=0) if generations else 0,
        "reproducibility_passed": False,
    }

    if metrics["initial_train_loss"] is not None and metrics["final_train_loss"] is not None:
        metrics["convergence_passed"] = metrics["final_train_loss"] < metrics["initial_train_loss"]

    passed = True
    if metrics["final_train_loss"] is not None and metrics["final_train_loss"] > expected["phase1_final_train_loss_max"]:
        print(f"[repro] FAIL: final train loss {metrics['final_train_loss']:.4f} > {expected['phase1_final_train_loss_max']}")
        passed = False
    if metrics["val_accuracy"] is not None and metrics["val_accuracy"] < expected["phase1_val_accuracy_min"]:
        print(f"[repro] FAIL: val accuracy {metrics['val_accuracy']:.4f} < {expected['phase1_val_accuracy_min']}")
        passed = False
    if not metrics["convergence_passed"]:
        print("[repro] FAIL: convergence check failed")
        passed = False
    if metrics["inference_min_length"] < expected["inference_min_length"]:
        print(f"[repro] FAIL: inference min length {metrics['inference_min_length']} < {expected['inference_min_length']}")
        passed = False

    metrics["reproducibility_passed"] = passed
    REPRO_METRICS_PATH.write_text(json.dumps(metrics, indent=2, default=str))
    print(f"[repro] Metrics written to {REPRO_METRICS_PATH}")
    if passed:
        print("[repro] Reproducibility check: PASSED")
    else:
        print("[repro] Reproducibility check: FAILED")
    return passed


def main():
    parser = argparse.ArgumentParser(description="Phase J Reproduction Script")
    parser.add_argument("--skip-install", action="store_true", help="Skip dependency installation")
    parser.add_argument("--skip-train", action="store_true", help="Skip training (use existing model)")
    parser.add_argument("--skip-resume", action="store_true", help="Skip resume step")
    parser.add_argument("--skip-eval", action="store_true", help="Skip evaluation")
    parser.add_argument("--skip-export", action="store_true", help="Skip export")
    parser.add_argument("--skip-inference", action="store_true", help="Skip inference")
    parser.add_argument("--config", default=str(CONFIG_PATH), help="Path to config YAML")
    args = parser.parse_args()

    global CONFIG_PATH
    CONFIG_PATH = Path(args.config)
    if not CONFIG_PATH.exists():
        print(f"Config not found: {CONFIG_PATH}")
        sys.exit(1)

    torch.manual_seed(42)
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False
    torch.use_deterministic_algorithms(True, warn_only=True)

    print("=" * 60)
    print("Phase J Reproducibility Package - Full Reproduction")
    print("=" * 60)
    start = time.time()

    if not args.skip_install:
        install_dependencies()
    else:
        print("\n[repro] Skipping dependency installation.")

    cfg = validate_config()

    if not args.skip_train:
        train_model(cfg)
    else:
        print("\n[repro] Skipping training (using existing model).")

    if not args.skip_resume:
        resume_training(cfg)
    else:
        print("\n[repro] Skipping resume step.")

    if not args.skip_eval:
        eval_output = evaluate_model(cfg)
    else:
        print("\n[repro] Skipping evaluation.")
        eval_output = ""

    if not args.skip_export:
        export_model(cfg)
    else:
        print("\n[repro] Skipping export.")

    if not args.skip_inference:
        generations = run_inference(cfg)
    else:
        print("\n[repro] Skipping inference.")
        generations = {}

    passed = verify_reproducibility(cfg, generations)
    elapsed = time.time() - start
    print(f"\n[repro] Reproduction completed in {elapsed:.1f}s")
    print("=" * 60)
    sys.exit(0 if passed else 1)


if __name__ == "__main__":
    main()
