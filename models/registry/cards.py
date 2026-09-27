import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

REGISTRY_DIR = Path(__file__).resolve().parent.parent.parent / "models" / "registry"
CARDS_DIR = REGISTRY_DIR / "cards"


def _ensure_dirs() -> None:
    CARDS_DIR.mkdir(parents=True, exist_ok=True)


def generate_model_card(
    name: str,
    version: str,
    description: str,
    architecture: str,
    training_data: str,
    training_details: Dict[str, Any],
    evaluation: Dict[str, Any],
    limitations: str = "",
    ethical_considerations: str = "",
    citation: str = "",
    license: str = "MIT",
    tags: Optional[List[str]] = None,
) -> str:
    card = f"""---
name: {name}
version: {version}
license: {license}
tags:
"""
    if tags:
        for tag in tags:
            card += f"  - {tag}\n"

    card += f"""
# {name} v{version}

## Model Details

**Description:** {description}

**Architecture:** {architecture}

**License:** {license}

**Model Size:** {training_details.get('model_size', 'Unknown')}

**Language(s):** {training_details.get('language', 'English')}

## Training Details

**Training Data:** {training_data}

**Dataset Size:** {training_details.get('dataset_size', 'Unknown')}

**Training Compute:** {training_details.get('compute', 'Unknown')}

**Training Duration:** {training_details.get('duration', 'Unknown')}

**Framework:** {training_details.get('framework', 'PyTorch')}

### Training Hyperparameters

| Parameter | Value |
|-----------|-------|
"""
    for k, v in training_details.get("hyperparameters", {}).items():
        card += f"| {k} | {v} |\n"

    card += f"""
## Evaluation

| Metric | Value |
|--------|-------|
"""
    for k, v in evaluation.items():
        card += f"| {k} | {v} |\n"

    card += f"""
## Limitations

{limitations}

## Ethical Considerations

{ethical_considerations}

## Citation

```
{citation}
```

## Card Information

**Generated:** {datetime.utcnow().isoformat()}Z
**Registry:** models/registry
**Model Path:** models/registry/versions/{name}/{version}
"""
    return card


def save_model_card(name: str, version: str, content: str) -> Path:
    _ensure_dirs()
    path = CARDS_DIR / f"{name}_v{version}.md"
    path.write_text(content)
    return path


def get_model_card(name: str, version: str) -> Optional[str]:
    path = CARDS_DIR / f"{name}_v{version}.md"
    if path.exists():
        return path.read_text()
    return None


def list_model_cards() -> List[Dict[str, Any]]:
    _ensure_dirs()
    result = []
    for path in CARDS_DIR.glob("*.md"):
        parts = path.stem.split("_v")
        if len(parts) == 2:
            result.append({
                "name": parts[0],
                "version": parts[1],
                "path": str(path),
            })
    return result
