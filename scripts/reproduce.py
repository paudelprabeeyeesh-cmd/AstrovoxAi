#!/usr/bin/env python3
"""
Phase 15 Production Reproducibility Script
Complete one-click reproduction with version locking, deterministic training,
and full pipeline verification.
"""

import argparse
import hashlib
import json
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
CONFIG_DIR = REPO_ROOT / "configs" / "versioned"
MANIFEST_PATH = CONFIG_DIR / "manifest.json"
LOCK_FILE = REPO_ROOT / "repro_lock.json"
EXPECTED_METRICS_PATH = REPO_ROOT / "repro_expected_metrics.json"
REPRO_METRICS_PATH = REPO_ROOT / "repro_metrics.json"


def run_cmd(cmd, cwd=REPO_ROOT, check=True, capture=False):
    print(f"[repro] {' '.join(str(c) for c in cmd)}")
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


def lock_versions(config_name: str) -> dict[str, Any]:
    manifest = json.loads(MANIFEST_PATH.read_text()) if MANIFEST_PATH.exists() else {}
    config_path = CONFIG_DIR / config_name
    if not config_path.exists():
        raise FileNotFoundError(f"Config not found: {config_path}")

    config_sha = compute_file_sha256(config_path)
    lock = {
        "locked_at": datetime.utcnow().isoformat() + "Z",
        "config": {
            "name": config_name,
            "sha256": config_sha,
            "path": str(config_path.relative_to(REPO_ROOT)),
        },
        "python_version": sys.version.split()[0],
        "torch_version": __import__("torch").__version__,
        "cuda_available": __import__("torch").cuda.is_available(),
        "seed": 42,
        "deterministic": True,
        "files": {},
    }

    for root, dirs, files in os.walk(REPO_ROOT):
        dirs[:] = [d for d in dirs if d not in {".git", "__pycache__", ".pytest_cache", "node_modules", "logs"}]
        for file in files:
            file_path = Path(root) / file
            rel = file_path.relative_to(REPO_ROOT)
            if any(rel.match(p) for p in ["*.pyc", "*.pyo", "*.pt", "*.bin", "*.onnx", "*.safetensors"]):
                continue
            if file_path.stat().st_size > 10 * 1024 * 1024:
                continue
            try:
                lock["files"][str(rel)] = compute_file_sha256(file_path)
            except Exception:
                pass

    LOCK_FILE.write_text(json.dumps(lock, indent=2, default=str))
    print(f"[repro] Versions locked to {LOCK_FILE}")
    return lock


def validate_lock() -> bool:
    if not LOCK_FILE.exists():
        print("[repro] No lock file found. Run with --lock to create one.")
        return False
    current = json.loads(LOCK_FILE.read_text())
    config_name = current["config"]["name"]
    config_path = REPO_ROOT / current["config"]["path"]
    if not config_path.exists() or compute_file_sha256(config_path) != current["config"]["sha256"]:
        print("[repro] FAIL: Config file has changed since lock.")
        return False
    print(f"[repro] Lock validated for {config_name}")
    return True


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


def validate_config(config_name: str) -> dict[str, Any]:
    config_path = CONFIG_DIR / config_name
    assert config_path.exists(), f"Config not found: {config_path}"
    with open(config_path) as f:
        cfg = yaml.safe_load(f)
    required = ["vocab_size", "hidden_size", "num_hidden_layers", "batch_size", "epochs", "output_dir"]
    for k in required:
        assert k in cfg, f"Missing config key: {k}"
    print(f"[repro] Config OK: {config_path}")
    return cfg


def train_model(config_name: str):
    print("\n[repro] Training model (fresh)...")
    train_script = REPO_ROOT / "phase1_train.py"
    assert train_script.exists(), f"Training script not found: {train_script}"
    run_cmd([sys.executable, str(train_script), "--config", str(CONFIG_DIR / config_name)])


def resume_training(config_name: str):
    print("\n[repro] Resuming training from checkpoint...")
    cfg = validate_config(config_name)
    ckpt_dir = REPO_ROOT / cfg.get("checkpoint_dir", "phase1_checkpoints")
    ckpts = sorted(ckpt_dir.glob("*.pt")) if ckpt_dir.exists() else []
    assert ckpts, f"No checkpoints found in {ckpt_dir}"
    resume_ckpt = ckpts[-1]
    run_cmd([
        sys.executable,
        str(REPO_ROOT / "phase1_train.py"),
        "--config", str(CONFIG_DIR / config_name),
        "--resume", str(resume_ckpt),
    ])
    print(f"[repro] Resume complete from {resume_ckpt}")


def evaluate_model(config_name: str) -> str:
    print("\n[repro] Evaluating model...")
    cfg = validate_config(config_name)
    ckpt_dir = REPO_ROOT / cfg.get("checkpoint_dir", "phase1_checkpoints")
    output = run_cmd([
        sys.executable,
        str(REPO_ROOT / "phase1_evaluate.py"),
        "--config", str(CONFIG_DIR / config_name),
        "--checkpoint-dir", str(ckpt_dir),
    ], capture=True)
    print(output)
    return output


def export_model(config_name: str):
    print("\n[repro] Exporting model...")
    cfg = validate_config(config_name)
    export_script = REPO_ROOT / "models" / "llm" / "export.py"
    if not export_script.exists():
        print("[repro] Export module not found, skipping export.")
        return None
    run_cmd([sys.executable, str(export_script)], check=False)


def run_inference(config_name: str) -> dict[str, str]:
    print("\n[repro] Running inference...")
    cfg = validate_config(config_name)
    generations = {}
    prompts = [
        "Astrovox is",
        "The model learns",
        "Phase one focuses on",
        "Transformers use attention",
        "Gradient descent optimizes",
    ]
    for prompt in prompts:
        try:
            output = run_cmd([
                sys.executable,
                str(REPO_ROOT / "models" / "llm" / "inference" / "generate.py"),
                "--config", str(CONFIG_DIR / config_name),
                "--prompt", prompt,
                "--max-new-tokens", "40",
            ], capture=True)
            generations[prompt] = output
        except Exception as e:
            generations[prompt] = f"[gen_error] {e}"
        print(f"  Prompt: {prompt!r} -> {generations[prompt][:80]}")
    return generations


def verify_reproducibility(cfg: dict[str, Any], generations: dict[str, str]) -> bool:
    print("\n[repro] Verifying reproducibility...")
    expected = {
        "phase1_final_train_loss_max": 3.0,
        "phase1_val_accuracy_min": 0.01,
        "inference_min_length": 10,
        "convergence_required": True,
    }

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
    parser = argparse.ArgumentParser(description="Phase 15 Reproducibility Script")
    parser.add_argument("--config", default="config_phase1_v1.yaml", help="Config YAML filename in configs/versioned/")
    parser.add_argument("--lock", action="store_true", help="Lock versions before running")
    parser.add_argument("--validate-lock", action="store_true", help="Validate existing lock")
    parser.add_argument("--skip-install", action="store_true", help="Skip dependency installation")
    parser.add_argument("--skip-train", action="store_true", help="Skip training")
    parser.add_argument("--skip-resume", action="store_true", help="Skip resume")
    parser.add_argument("--skip-eval", action="store_true", help="Skip evaluation")
    parser.add_argument("--skip-export", action="store_true", help="Skip export")
    parser.add_argument("--skip-inference", action="store_true", help="Skip inference")
    args = parser.parse_args()

    torch = __import__("torch")
    torch.manual_seed(42)
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False
    torch.use_deterministic_algorithms(True, warn_only=True)

    print("=" * 60)
    print("Phase 15 Production Reproducibility - Full Reproduction")
    print("=" * 60)
    start = time.time()

    if args.lock:
        lock_versions(args.config)
    if args.validate_lock:
        if not validate_lock():
            sys.exit(1)

    if not args.skip_install:
        install_dependencies()

    cfg = validate_config(args.config)

    if not args.skip_train:
        train_model(args.config)
    if not args.skip_resume:
        resume_training(args.config)
    if not args.skip_eval:
        evaluate_model(args.config)
    if not args.skip_export:
        export_model(args.config)
    if not args.skip_inference:
        generations = run_inference(args.config)
    else:
        generations = {}

    passed = verify_reproducibility(cfg, generations)
    elapsed = time.time() - start
    print(f"\n[repro] Reproduction completed in {elapsed:.1f}s")
    print("=" * 60)
    sys.exit(0 if passed else 1)


if __name__ == "__main__":
    main()
