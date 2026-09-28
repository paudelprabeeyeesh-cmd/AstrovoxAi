#!/usr/bin/env python3
"""
Auto-generate model cards from registry metadata.
"""

import argparse
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT))

from models.registry.cards import save_model_card
from models.registry.registry import get_model, list_models


def _render_template(template_path: Path, context: dict[str, Any]) -> str:
    template = template_path.read_text()
    for key, value in context.items():
        placeholder = "{" + key + "}"
        template = template.replace(placeholder, str(value) if value is not None else "")
    return template


def generate_from_registry(name: str, version: str | None = None) -> str:
    model = get_model(name, version)
    metadata = model.get("metadata", {})
    evaluation = model.get("evaluation", {})

    template_path = REPO_ROOT / "templates" / "model_card.md"
    if not template_path.exists():
        raise FileNotFoundError(f"Template not found: {template_path}")

    context = {
        "model_name": model["name"],
        "version": model["version"],
        "license": metadata.get("license", "MIT"),
        "tags": "\n".join(f"  - {tag}" for tag in metadata.get("tags", [])),
        "description": metadata.get("description", ""),
        "architecture": metadata.get("architecture", ""),
        "model_size": metadata.get("model_size", "Unknown"),
        "language": metadata.get("language", "English"),
        "framework": metadata.get("framework", "PyTorch"),
        "last_updated": model.get("updated_at", model.get("registered_at", "")),
        "training_data": metadata.get("training_data", ""),
        "dataset_size": metadata.get("dataset_size", "Unknown"),
        "compute": metadata.get("compute", "Unknown"),
        "duration": metadata.get("duration", "Unknown"),
        "optimizer": metadata.get("optimizer", "adamw"),
        "learning_rate": metadata.get("learning_rate", "3e-4"),
        "batch_size": metadata.get("batch_size", "32"),
        "epochs": metadata.get("epochs", "3"),
        "seed": metadata.get("seed", "42"),
        "hyperparameters_table": "\n".join(
            f"| {k} | {v} |" for k, v in metadata.get("hyperparameters", {}).items()
        ),
        "evaluation_table": "\n".join(
            f"| {k} | {v} |" for k, v in evaluation.items()
        ),
        "intended_use": metadata.get("intended_use", ""),
        "limitations": metadata.get("limitations", ""),
        "ethical_considerations": metadata.get("ethical_considerations", ""),
        "how_to_use": metadata.get("how_to_use", ""),
        "citation": metadata.get("citation", ""),
        "generated_at": __import__("datetime").datetime.utcnow().isoformat() + "Z",
        "model_sha256": model.get("sha256", ""),
        "model_status": model.get("status", "unknown"),
    }

    content = _render_template(template_path, context)
    save_model_card(model["name"], model["version"], content)
    return content


def main():
    parser = argparse.ArgumentParser(description="Generate model card from registry")
    parser.add_argument("--name", required=True, help="Model name")
    parser.add_argument("--version", help="Model version (latest if omitted)")
    parser.add_argument("--all", action="store_true", help="Generate cards for all models")
    parser.add_argument("--output", help="Output file path (default: print to stdout)")
    args = parser.parse_args()

    if args.all:
        models = list_models()
        for m in models:
            try:
                content = generate_from_registry(m["name"], m["latest_version"])
                print(f"Generated card for {m['name']}:{m['latest_version']}")
            except Exception as e:
                print(f"Failed for {m['name']}: {e}")
    else:
        content = generate_from_registry(args.name, args.version)
        if args.output:
            Path(args.output).write_text(content)
            print(f"Model card written to {args.output}")
        else:
            print(content)


if __name__ == "__main__":
    main()
