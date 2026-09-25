#!/usr/bin/env python3
"""
Code Duplication Finder - Detects duplicated code blocks across the project.
"""
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

Path("code-quality-reports").mkdir(exist_ok=True)


def tokenize(text: str) -> list[str]:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    return [line for line in lines if not line.startswith("#") and not line.startswith("//")]


def find_duplicates(files: list[Path], min_lines: int = 6) -> list[dict[str, Any]]:
    hashes: dict[str, list[dict[str, Any]]] = {}
    for path in files:
        text = path.read_text(errors="ignore")
        tokens = tokenize(text)
        if len(tokens) < min_lines:
            continue
        for i in range(len(tokens) - min_lines + 1):
            block = tuple(tokens[i : i + min_lines])
            block_hash = hashlib.md5("|".join(block).encode()).hexdigest()
            hashes.setdefault(block_hash, []).append({
                "file": str(path),
                "start_line": i + 1,
                "block": list(block)[:10],
            })
    duplicates = []
    for h, occurrences in hashes.items():
        if len(occurrences) > 1:
            files_in = sorted({o["file"] for o in occurrences})
            if len(files_in) > 1:
                duplicates.append({"hash": h, "occurrences": occurrences, "files": files_in})
    return duplicates


if __name__ == "__main__":
    extensions = ["*.py", "*.ts", "*.tsx", "*.js", "*.jsx"]
    files: list[Path] = []
    for ext in extensions:
        files.extend(Path(".").rglob(ext))
    files = [f for f in files if "node_modules" not in str(f) and "dist" not in str(f)]
    dups = find_duplicates(files)
    Path("code-quality-reports/code-duplication-report.json").write_text(json.dumps(dups, indent=2))
    if dups:
        print(f"Found {len(dups)} duplicated code blocks")
        sys.exit(1)
    print("No significant code duplication found")
    sys.exit(0)
