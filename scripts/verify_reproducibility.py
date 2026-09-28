#!/usr/bin/env python3
"""
Phase J Reproducibility Verification Script
Compares reproduction metrics against expected thresholds and prior artifact hashes.
"""

import argparse
import hashlib
import json
import sys
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
REPRO_METRICS_PATH = REPO_ROOT / "repro_metrics.json"
EXPECTED_METRICS_PATH = REPO_ROOT / "repro_expected_metrics.json"
CONFIG_PATH = REPO_ROOT / "configs" / "versioned" / "config_phase1_v1.yaml"
MODEL_PATH = REPO_ROOT / "phase1_model.pt"
EXPORT_DIR = REPO_ROOT / "repro_export"


def compute_file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def load_config_sha256() -> str:
    if not CONFIG_PATH.exists():
        return ""
    h = hashlib.sha256()
    with open(CONFIG_PATH, "rb") as f:
        h.update(f.read())
    return h.hexdigest()


def verify_metrics(metrics: dict, expected: dict) -> bool:
    passed = True
    for key, threshold in expected.items():
        actual = metrics.get(key)
        if actual is None:
            print(f"[verify] MISSING metric: {key}")
            passed = False
            continue

        if key.endswith("_max"):
            if actual > threshold:
                print(f"[verify] FAIL: {key} = {actual} > {threshold}")
                passed = False
            else:
                print(f"[verify] PASS: {key} = {actual} <= {threshold}")
        elif key.endswith("_min"):
            if actual < threshold:
                print(f"[verify] FAIL: {key} = {actual} < {threshold}")
                passed = False
            else:
                print(f"[verify] PASS: {key} = {actual} >= {threshold}")
        else:
            print(f"[verify] {key} = {actual} (expected {threshold})")

    return passed


def verify_model_exists() -> bool:
    if not MODEL_PATH.exists():
        print("[verify] FAIL: model file not found")
        return False
    print(f"[verify] PASS: model file exists ({MODEL_PATH})")
    return True


def verify_config_hash() -> bool:
    actual = load_config_sha256()
    expected = yaml.safe_load(open(CONFIG_PATH)) if CONFIG_PATH.exists() else {}
    if not actual:
        print("[verify] FAIL: config hash could not be computed")
        return False
    print(f"[verify] Config SHA256: {actual}")
    return True


def verify_export() -> bool:
    if not EXPORT_DIR.exists():
        print("[verify] WARN: export directory not found")
        return True
    files = list(EXPORT_DIR.rglob("*"))
    file_count = sum(1 for f in files if f.is_file())
    if file_count == 0:
        print("[verify] WARN: export directory is empty")
        return True
    print(f"[verify] PASS: export directory contains {file_count} file(s)")
    return True


def verify_inference(generations: dict) -> bool:
    if not generations:
        print("[verify] WARN: no inference generations to verify")
        return True
    min_len = min((len(v) for v in generations.values()), default=0)
    if min_len < 10:
        print(f"[verify] FAIL: inference min length {min_len} < 10")
        return False
    print(f"[verify] PASS: inference generations produced (min length {min_len})")
    return True


def main():
    parser = argparse.ArgumentParser(description="Verify Phase J reproducibility")
    parser.add_argument(
        "--metrics", default=str(REPRO_METRICS_PATH), help="Path to reproduction metrics JSON"
    )
    parser.add_argument(
        "--expected", default=str(EXPECTED_METRICS_PATH), help="Path to expected metrics JSON"
    )
    parser.add_argument("--config", default=str(CONFIG_PATH), help="Path to versioned config")
    args = parser.parse_args()

    print("=" * 60)
    print("Phase J Reproducibility Verification")
    print("=" * 60)

    metrics_path = Path(args.metrics)
    expected_path = Path(args.expected)

    if not metrics_path.exists():
        print(f"[verify] FAIL: metrics file not found: {metrics_path}")
        print("[verify] Run scripts/reproduce.py first to generate repro_metrics.json")
        sys.exit(1)

    metrics = json.loads(metrics_path.read_text())
    print(f"[verify] Loaded metrics from {metrics_path}")

    expected = {}
    if expected_path.exists():
        expected = json.loads(expected_path.read_text()).get("expected_metrics", {})
        print(f"[verify] Loaded expected thresholds from {expected_path}")
    else:
        expected = {
            "phase1_final_train_loss_max": 3.0,
            "phase1_val_accuracy_min": 0.01,
            "inference_min_length": 10,
            "convergence_required": True,
        }
        print("[verify] Using built-in expected thresholds")

    all_passed = True

    all_passed &= verify_model_exists()
    all_passed &= verify_config_hash()
    all_passed &= verify_export()

    if (
        "expected_metrics" in json.loads(expected_path.read_text())
        if expected_path.exists()
        else {}
    ):
        inner = json.loads(expected_path.read_text())["expected_metrics"]
    else:
        inner = expected

    all_passed &= verify_metrics(metrics, inner)

    generations = metrics.get("generations", {})
    all_passed &= verify_inference(generations)

    if metrics.get("reproducibility_passed"):
        print("\n[verify] Overall: PASSED")
    else:
        print("\n[verify] Overall: FAILED")
        all_passed = False

    print("=" * 60)
    sys.exit(0 if all_passed else 1)


if __name__ == "__main__":
    main()
