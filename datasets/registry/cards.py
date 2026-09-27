import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

REGISTRY_DIR = Path(__file__).resolve().parent.parent.parent / "datasets" / "registry"
CARDS_DIR = REGISTRY_DIR / "cards"


def _ensure_dirs() -> None:
    CARDS_DIR.mkdir(parents=True, exist_ok=True)


def generate_dataset_card(
    name: str,
    version: str,
    description: str,
    source: str,
    size: str,
    splits: Dict[str, int],
    preprocessing: str,
    license: str = "MIT",
    tags: Optional[List[str]] = None,
    known_issues: str = "",
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
# Dataset Card: {name} v{version}

## Dataset Details

**Description:** {description}

**Source:** {source}

**License:** {license}

**Size:** {size}

## Dataset Structure

| Split | Size |
|-------|------|
"""
    for split, count in splits.items():
        card += f"| {split} | {count} |\n"

    card += f"""
## Preprocessing

{preprocessing}

## Known Issues

{known_issues}

## Card Information

**Generated:** {datetime.utcnow().isoformat()}Z
**Registry:** datasets/registry
**Dataset Path:** datasets/registry/versions/{name}/{version}
"""
    return card


def save_dataset_card(name: str, version: str, content: str) -> Path:
    _ensure_dirs()
    path = CARDS_DIR / f"{name}_v{version}.md"
    path.write_text(content)
    return path


def get_dataset_card(name: str, version: str) -> Optional[str]:
    path = CARDS_DIR / f"{name}_v{version}.md"
    if path.exists():
        return path.read_text()
    return None


def list_dataset_cards() -> List[Dict[str, Any]]:
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
