#!/usr/bin/env python3
"""
Unused Dependency Detector - Finds unused packages in requirements.txt and package.json.
"""
import ast
import json
import re
import sys
from pathlib import Path
from typing import Any

Path("code-quality-reports").mkdir(exist_ok=True)


def scan_python_deps(requirements: Path, src: Path) -> dict[str, Any]:
    if not requirements.exists():
        return {"error": "requirements.txt not found"}
    packages: list[str] = []
    for line in requirements.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and ">=" in line:
            pkg = line.split(">=")[0].strip().lower()
            packages.append(pkg)
    used: set[str] = set()
    for py_file in src.rglob("*.py"):
        text = py_file.read_text(errors="ignore")
        for pkg in packages:
            if pkg.replace("-", "_") in text.lower():
                used.add(pkg)
    unused = [p for p in packages if p not in used]
    return {"packages": packages, "used": sorted(used), "unused": unused}


def scan_ts_deps(package_json: Path, src: Path) -> dict[str, Any]:
    if not package_json.exists():
        return {"error": "package.json not found"}
    import json as _json
    data = _json.loads(package_json.read_text())
    deps = {k.lower(): k for k in list(data.get("dependencies", {}).keys())}
    used: set[str] = set()
    for ts_file in src.rglob("*.ts"):
        text = ts_file.read_text(errors="ignore").lower()
        for pkg in deps:
            if pkg in text:
                used.add(pkg)
    unused = [deps[p] for p in deps if p not in used]
    return {"packages": list(deps.values()), "used": sorted(used), "unused": unused}


if __name__ == "__main__":
    results = {
        "python": scan_python_deps(Path("02-Backend/requirements.txt"), Path("02-Backend/app")),
        "typescript": scan_ts_deps(Path("package.json"), Path("src")),
    }
    Path("code-quality-reports/unused-deps-report.json").write_text(json.dumps(results, indent=2))
    total_unused = len(results["python"].get("unused", [])) + len(results["typescript"].get("unused", []))
    if total_unused:
        print(f"Found {total_unused} unused dependencies")
        sys.exit(1)
    print("No unused dependencies found")
    sys.exit(0)
