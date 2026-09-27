#!/usr/bin/env python3
"""Validate all YAML configs have required fields and correct types."""
import argparse
import os
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from model.model_scaling import count_parameters, load_config


def _cast_value(value):
    if isinstance(value, str):
        try:
            return int(value)
        except ValueError:
            pass
        try:
            return float(value)
        except ValueError:
            pass
        if value.lower() in ("true", "false"):
            return value.lower() == "true"
    return value


def load_config(path):
    with open(path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
    if isinstance(config, dict):
        for key, value in config.items():
            config[key] = _cast_value(value)
    return config


REQUIRED_FIELDS = {
    "vocab_size": int,
    "hidden_size": int,
    "num_hidden_layers": int,
    "num_attention_heads": int,
    "intermediate_size": int,
    "max_position_embeddings": int,
    "batch_size": int,
    "epochs": int,
    "lr": (int, float),
    "gradient_accumulation_steps": int,
    "gradient_checkpointing": bool,
    "mixed_precision": str,
    "train_file": str,
    "tokenizer_path": str,
    "output_dir": str,
    "checkpoint_dir": str,
    "log_dir": str,
    "checkpoint_every_steps": int,
    "max_val_batches": int,
    "gradient_clip_norm": (int, float),
    "warmup_steps": int,
    "min_lr": (int, float),
    "lr_scheduler": str,
    "optimizer": str,
    "seed": int,
    "dropout": (int, float),
    "layer_norm_epsilon": (int, float),
    "attention_bias": bool,
    "mlp_bias": bool,
    "tie_weights": bool,
    "activation": str,
    "rope_theta": (int, float),
}

OPTIONAL_FIELDS = {
    "resume_from": str,
}

TARGET_PARAMS = {
    "config_50m.yaml": 49_947_648,
    "config_100m.yaml": 100_087_296,
    "config_300m.yaml": 301_238_272,
    "config_700m.yaml": 696_386_560,
}


def find_configs(base_dir="models/llm/configs"):
    base = Path(base_dir)
    if not base.exists():
        return []
    return sorted([p for p in base.glob("config_*.yaml")])


def validate_types(config, path):
    errors = []
    for field, expected_type in REQUIRED_FIELDS.items():
        if field not in config:
            errors.append(f"Missing required field: {field}")
            continue
        value = config[field]
        if isinstance(expected_type, tuple):
            if not isinstance(value, expected_type):
                errors.append(f"Field '{field}' has type {type(value).__name__}, expected {expected_type}")
        else:
            if not isinstance(value, expected_type):
                errors.append(f"Field '{field}' has type {type(value).__name__}, expected {expected_type.__name__}")
    for field, value in OPTIONAL_FIELDS.items():
        if field in config:
            expected_type = OPTIONAL_FIELDS[field]
            if isinstance(expected_type, tuple):
                if not isinstance(value, expected_type):
                    errors.append(f"Optional field '{field}' has type {type(value).__name__}, expected {expected_type}")
            else:
                if not isinstance(value, expected_type):
                    errors.append(f"Optional field '{field}' has type {type(value).__name__}, expected {expected_type.__name__}")
    return errors


def validate_model_scaling(config, path):
    errors = []
    try:
        num_params = count_parameters(
            vocab_size=int(config["vocab_size"]),
            hidden_size=int(config["hidden_size"]),
            num_hidden_layers=int(config["num_hidden_layers"]),
            num_attention_heads=int(config["num_attention_heads"]),
            intermediate_size=int(config["intermediate_size"]),
            max_position_embeddings=int(config.get("max_position_embeddings", 2048)),
            attention_bias=bool(config.get("attention_bias", False)),
            mlp_bias=bool(config.get("mlp_bias", False)),
            tie_weights=bool(config.get("tie_weights", True)),
            activation=str(config.get("activation", "swiglu")),
        )
        config["_computed_params"] = num_params
        name = Path(path).name
        if name in TARGET_PARAMS:
            target = TARGET_PARAMS[name]
            if num_params != target:
                errors.append(f"Parameter count mismatch: got {num_params:,}, expected {target:,}")
    except Exception as e:
        errors.append(f"Parameter count computation failed: {e}")
    return errors


def validate_consistency(config, path):
    errors = []
    if config.get("num_attention_heads", 0) > 0:
        if int(config["hidden_size"]) % int(config["num_attention_heads"]) != 0:
            errors.append(f"hidden_size ({config['hidden_size']}) must be divisible by num_attention_heads ({config['num_attention_heads']})")
    if config.get("intermediate_size", 0) < config.get("hidden_size", 0):
        errors.append(f"intermediate_size ({config['intermediate_size']}) should be >= hidden_size ({config['hidden_size']})")
    if config.get("lr", 0) <= 0:
        errors.append(f"lr must be positive, got {config['lr']}")
    if config.get("epochs", 0) < 1:
        errors.append(f"epochs must be >= 1, got {config['epochs']}")
    if config.get("batch_size", 0) < 1:
        errors.append(f"batch_size must be >= 1, got {config['batch_size']}")
    if config.get("gradient_accumulation_steps", 0) < 1:
        errors.append(f"gradient_accumulation_steps must be >= 1, got {config['gradient_accumulation_steps']}")
    if config.get("mixed_precision") not in ("none", "fp16", "bf16", "bfloat16"):
        errors.append(f"mixed_precision must be one of 'none', 'fp16', 'bf16', 'bfloat16', got '{config.get('mixed_precision')}'")
    if config.get("optimizer") not in ("adamw", "8bit-adamw"):
        errors.append(f"optimizer must be one of 'adamw', '8bit-adamw', got '{config.get('optimizer')}'")
    if config.get("lr_scheduler") not in ("cosine", "linear", "constant"):
        errors.append(f"lr_scheduler must be one of 'cosine', 'linear', 'constant', got '{config.get('lr_scheduler')}'")
    if config.get("activation") not in ("swiglu", "gelu"):
        errors.append(f"activation must be one of 'swiglu', 'gelu', got '{config.get('activation')}'")
    return errors


def validate_all(base_dir="models/llm/configs"):
    configs = find_configs(base_dir)
    if not configs:
        print(f"No config files found in {base_dir}")
        return 1

    all_ok = True
    for path in configs:
        print(f"\nValidating {path}...")
        try:
            config = load_config(path)
        except Exception as e:
            print(f"  FAILED to parse: {e}")
            all_ok = False
            continue

        if not isinstance(config, dict):
            print(f"  FAILED: config is not a dictionary")
            all_ok = False
            continue

        type_errors = validate_types(config, path)
        scaling_errors = validate_model_scaling(config, path)
        consistency_errors = validate_consistency(config, path)
        errors = type_errors + scaling_errors + consistency_errors

        if errors:
            all_ok = False
            print(f"  FAILED with {len(errors)} error(s):")
            for err in errors:
                print(f"    - {err}")
        else:
            num_params = config.get("_computed_params", "?")
            print(f"  OK - params={num_params:,}")

    print("\n" + "=" * 60)
    if all_ok:
        print("All configs passed validation.")
    else:
        print("Some configs failed validation.")
    return 0 if all_ok else 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Validate LLM training configs")
    parser.add_argument("--base-dir", default="models/llm/configs", help="Directory containing config YAML files")
    args = parser.parse_args()
    sys.exit(validate_all(base_dir=args.base_dir))
