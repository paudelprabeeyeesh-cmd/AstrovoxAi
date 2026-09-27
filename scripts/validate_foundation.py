#!/usr/bin/env python3
"""Foundation validation: YAML configs, dead code, missing type hints, duplicate code."""

from __future__ import annotations

import ast
import hashlib
import json
import os
import sys
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any

import yaml


REPORT_PATH = Path("foundation_report.json")


@dataclass
class ValidationIssue:
    category: str
    file: str
    message: str
    severity: str = "error"


@dataclass
class FoundationReport:
    generated_at: str = ""
    yaml_configs_checked: int = 0
    python_files_checked: int = 0
    issues: list[ValidationIssue] = field(default_factory=list)
    dead_code: list[dict[str, Any]] = field(default_factory=list)
    missing_type_hints: list[dict[str, Any]] = field(default_factory=list)
    duplicate_code: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["issues"] = [asdict(i) for i in self.issues]
        return data

    def save(self, path: Path) -> None:
        path.write_text(json.dumps(self.to_dict(), indent=2), encoding="utf-8")

    def print_summary(self) -> None:
        counts: dict[str, int] = {}
        for issue in self.issues:
            counts[issue.category] = counts.get(issue.category, 0) + 1
        print("=" * 60)
        print("Foundation Validation Summary")
        print("=" * 60)
        print(f"YAML configs checked: {self.yaml_configs_checked}")
        print(f"Python files checked: {self.python_files_checked}")
        print(f"Dead code items:      {len(self.dead_code)}")
        print(f"Missing type hints:   {len(self.missing_type_hints)}")
        print(f"Duplicate code blocks:{len(self.duplicate_code)}")
        if counts:
            print("Issues by category:")
            for category, count in sorted(counts.items()):
                print(f"  {category}: {count}")
        else:
            print("No issues found.")


report = FoundationReport()


def _record(category: str, file: str, message: str, severity: str = "error") -> None:
    report.issues.append(ValidationIssue(category=category, file=file, message=message, severity=severity))


# ------------------------------------------------------------------
# YAML validation
# ------------------------------------------------------------------
YAML_DIRECTORIES = [
    Path("configs"),
    Path("models") / "llm" / "configs",
    Path("configs") / "versioned",
]

REQUIRED_YAML_FIELDS = {
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

OPTIONAL_YAML_FIELDS = {"resume_from": str}


def _yaml_type_name(expected: type | tuple[type, ...]) -> str:
    if isinstance(expected, tuple):
        return " | ".join(t.__name__ for t in expected)
    return expected.__name__


def validate_yaml_file(path: Path) -> None:
    if not path.is_file():
        return
    report.yaml_configs_checked += 1
    try:
        with path.open("r", encoding="utf-8") as fh:
            data = yaml.safe_load(fh)
    except Exception as exc:  # noqa: BLE001
        _record("yaml", str(path), f"Failed to parse YAML: {exc}")
        return

    if not isinstance(data, dict):
        _record("yaml", str(path), "Config is not a dictionary")
        return

    for field_name, expected in REQUIRED_YAML_FIELDS.items():
        if field_name not in data:
            _record("yaml", str(path), f"Missing required field: {field_name}")
            continue
        value = data[field_name]
        if not isinstance(value, expected):
            _record(
                "yaml",
                str(path),
                f"Field '{field_name}' has type {type(value).__name__}, expected {_yaml_type_name(expected)}",
            )

    for field_name, expected in OPTIONAL_YAML_FIELDS.items():
        if field_name in data:
            value = data[field_name]
            if not isinstance(value, expected):
                _record(
                    "yaml",
                    str(path),
                    f"Optional field '{field_name}' has type {type(value).__name__}, expected {expected.__name__}",
                )

    if "hidden_size" in data and "num_attention_heads" in data:
        hidden = int(data["hidden_size"])
        heads = int(data["num_attention_heads"])
        if heads > 0 and hidden % heads != 0:
            _record("yaml", str(path), f"hidden_size ({hidden}) must be divisible by num_attention_heads ({heads})")

    if "mixed_precision" in data and str(data["mixed_precision"]).lower() not in {"none", "fp16", "bf16", "bfloat16"}:
        _record("yaml", str(path), f"mixed_precision must be one of none/fp16/bf16/bfloat16, got {data['mixed_precision']}")

    if "optimizer" in data and str(data["optimizer"]).lower() not in {"adamw", "8bit-adamw"}:
        _record("yaml", str(path), f"optimizer must be one of adamw/8bit-adamw, got {data['optimizer']}")

    if "lr_scheduler" in data and str(data["lr_scheduler"]).lower() not in {"cosine", "linear", "constant"}:
        _record("yaml", str(path), f"lr_scheduler must be one of cosine/linear/constant, got {data['lr_scheduler']}")

    if "activation" in data and str(data["activation"]).lower() not in {"swiglu", "gelu"}:
        _record("yaml", str(path), f"activation must be one of swiglu/gelu, got {data['activation']}")


def validate_all_yaml() -> None:
    for directory in YAML_DIRECTORIES:
        base = Path(directory)
        if not base.exists():
            continue
        for path in sorted(base.rglob("config_*.yaml")):
            validate_yaml_file(path)
        for path in sorted(base.rglob("config_*.yml")):
            validate_yaml_file(path)


# ------------------------------------------------------------------
# Dead code detection
# ------------------------------------------------------------------
def _python_files(root: Path) -> list[Path]:
    return [p for p in root.rglob("*.py") if p.is_file()]


def _normalize(node: ast.AST) -> str:
    return ast.unparse(node) if hasattr(ast, "unparse") else ast.dump(node)


def detect_dead_code() -> None:
    roots = [Path("."), Path("scripts"), Path("backend"), Path("model"), Path("models"), Path("ASTROVOX_AI")]
    files: list[Path] = []
    for root in roots:
        if root.exists():
            files.extend(_python_files(root))

    defined_names: dict[str, set[str]] = {}
    imported_names: dict[str, set[str]] = {}
    used_names: dict[str, set[str]] = {}

    class NameCollector(ast.NodeVisitor):
        def __init__(self, names: set[str]) -> None:
            self.names = names

        def visit_Name(self, node: ast.Name) -> None:
            self.names.add(node.id)
            self.generic_visit(node)

        def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
            self.names.add(node.name)
            self.generic_visit(node)

        def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
            self.names.add(node.name)
            self.generic_visit(node)

        def visit_ClassDef(self, node: ast.ClassDef) -> None:
            self.names.add(node.name)
            self.generic_visit(node)

    class ImportCollector(ast.NodeVisitor):
        def __init__(self, imports: set[str]) -> None:
            self.imports = imports

        def visit_Import(self, node: ast.Import) -> None:
            for alias in node.names:
                self.imports.add(alias.asname or alias.name.split(".")[0])
            self.generic_visit(node)

        def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
            for alias in node.names:
                self.imports.add(alias.asname or alias.name)
            self.generic_visit(node)

    for file_path in files:
        try:
            source = file_path.read_text(encoding="utf-8")
            tree = ast.parse(source)
        except Exception:  # noqa: BLE001
            continue

        defined: set[str] = set()
        NameCollector(defined).visit(tree)
        defined_names[str(file_path)] = defined

        imported: set[str] = set()
        ImportCollector(imported).visit(tree)
        imported_names[str(file_path)] = imported

        used: set[str] = set()
        NameCollector(used).visit(tree)
        used_names[str(file_path)] = used

    for file_path, imported in imported_names.items():
        for name in imported:
            if name not in used_names.get(file_path, set()):
                report.dead_code.append({"file": file_path, "name": name, "reason": "imported but never used"})

    for file_path, defined in defined_names.items():
        module_name = Path(file_path).stem
        for name in defined:
            if name.startswith("_"):
                continue
            used_elsewhere = any(
                name in used_names.get(other, set())
                for other in used_names
                if other != file_path
            )
            if not used_elsewhere and name not in {"main", "run", "cli"}:
                if name not in imported_names.get(file_path, set()):
                    report.dead_code.append({"file": file_path, "name": name, "reason": "defined but never referenced"})


# ------------------------------------------------------------------
# Missing type hints
# ------------------------------------------------------------------
def detect_missing_type_hints() -> None:
    roots = [Path("."), Path("scripts"), Path("backend"), Path("model"), Path("models"), Path("ASTROVOX_AI")]
    files: list[Path] = []
    for root in roots:
        if root.exists():
            files.extend(_python_files(root))

    for file_path in files:
        try:
            source = file_path.read_text(encoding="utf-8")
            tree = ast.parse(source)
        except Exception:  # noqa: BLE001
            continue

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if node.name.startswith("_"):
                    continue
                missing: list[str] = []
                if node.returns is None:
                    missing.append("return")
                for arg in node.args.args:
                    if arg.arg == "self":
                        continue
                    if arg.annotation is None:
                        missing.append(f"arg:{arg.arg}")
                if missing:
                    report.missing_type_hints.append(
                        {
                            "file": str(file_path),
                            "function": node.name,
                            "missing": missing,
                        }
                    )


# ------------------------------------------------------------------
# Duplicate code
# ------------------------------------------------------------------
def _function_hash(node: ast.FunctionDef | ast.AsyncFunctionDef) -> str | None:
    try:
        if hasattr(ast, "unparse"):
            body = ast.unparse(node)
        else:
            body = ast.dump(node)
    except Exception:  # noqa: BLE001
        return None
    normalized = "\n".join(line.strip() for line in body.splitlines() if line.strip())
    if len(normalized) < 40:
        return None
    return hashlib.md5(normalized.encode("utf-8")).hexdigest()


def detect_duplicate_code() -> None:
    roots = [Path("."), Path("scripts"), Path("backend"), Path("model"), Path("models"), Path("ASTROVOX_AI")]
    files: list[Path] = []
    for root in roots:
        if root.exists():
            files.extend(_python_files(root))

    hash_map: dict[str, list[dict[str, Any]]] = {}

    for file_path in files:
        try:
            source = file_path.read_text(encoding="utf-8")
            tree = ast.parse(source)
        except Exception:  # noqa: BLE001
            continue

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if node.name.startswith("_"):
                    continue
                digest = _function_hash(node)
                if digest is None:
                    continue
                hash_map.setdefault(digest, []).append(
                    {
                        "file": str(file_path),
                        "function": node.name,
                        "lineno": node.lineno,
                    }
                )

    for digest, entries in hash_map.items():
        if len(entries) > 1:
            report.duplicate_code.append(
                {
                    "hash": digest,
                    "count": len(entries),
                    "locations": entries,
                }
            )


# ------------------------------------------------------------------
# Main
# ------------------------------------------------------------------
def main() -> int:
    from datetime import datetime

    report.generated_at = datetime.utcnow().isoformat() + "Z"

    validate_all_yaml()
    detect_dead_code()
    detect_missing_type_hints()
    detect_duplicate_code()

    report.print_summary()
    report.save(REPORT_PATH)
    print(f"\nReport saved to {REPORT_PATH}")

    return 1 if report.issues or report.dead_code or report.missing_type_hints or report.duplicate_code else 0


if __name__ == "__main__":
    sys.exit(main())
