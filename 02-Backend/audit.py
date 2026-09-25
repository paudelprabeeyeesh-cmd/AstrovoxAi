#!/usr/bin/env python3
"""
Backend Modularization Audit and Migration Script
Analyzes the monolith and generates migration plan.
"""

import os
import ast
import hashlib
from pathlib import Path
from collections import defaultdict
from typing import Dict, List, Set, Tuple

BASE_DIR = Path(r"C:\Users\Dell\Documents\GitHub\AstrovoxAi\02-Backend\app")


def get_file_hash(path: Path) -> str:
    """Get MD5 hash of file content."""
    try:
        content = path.read_text(encoding='utf-8')
        return hashlib.md5(content.encode()).hexdigest()
    except Exception:
        return ""


def get_all_python_files() -> List[Path]:
    """Get all Python files in the app directory."""
    return list(BASE_DIR.rglob("*.py"))


def analyze_imports(file_path: Path) -> Set[str]:
    """Extract all imports from a Python file."""
    imports = set()
    try:
        tree = ast.parse(file_path.read_text(encoding='utf-8'))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.add(alias.name.split('.')[0])
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    imports.add(node.module.split('.')[0])
    except Exception:
        pass
    return imports


def find_duplicates(files: List[Path]) -> Dict[str, List[Path]]:
    """Find duplicate files by content hash."""
    hash_map = defaultdict(list)
    for f in files:
        h = get_file_hash(f)
        if h:
            hash_map[h].append(f)
    return {h: paths for h, paths in hash_map.items() if len(paths) > 1}


def find_large_files(files: List[Path], threshold: int = 600) -> List[Tuple[Path, int]]:
    """Find files larger than threshold lines."""
    large = []
    for f in files:
        try:
            lines = len(f.read_text(encoding='utf-8').splitlines())
            if lines > threshold:
                large.append((f, lines))
        except Exception:
            pass
    return sorted(large, key=lambda x: x[1], reverse=True)


def categorize_files(files: List[Path]) -> Dict[str, List[Path]]:
    """Categorize files by functional area."""
    categories = defaultdict(list)
    for f in files:
        name = f.name.lower()
        if any(x in name for x in ['memory', 'remember', 'recall', 'context_mem']):
            categories['memory'].append(f)
        elif any(x in name for x in ['database', 'db_']):
            categories['database'].append(f)
        elif any(x in name for x in ['auth', 'login', 'token', 'security']):
            categories['auth'].append(f)
        elif any(x in name for x in ['api_v', 'api_version', 'version']):
            categories['api_versioning'].append(f)
        elif any(x in name for x in ['knowledge', 'rag', 'vector']):
            categories['knowledge'].append(f)
        elif any(x in name for x in ['model', 'llm', 'inference']):
            categories['models'].append(f)
        elif any(x in name for x in ['router', 'route']):
            categories['routers'].append(f)
        elif any(x in name for x in ['agent', 'multi_agent']):
            categories['agents'].append(f)
        else:
            categories['other'].append(f)
    return dict(categories)


def main():
    files = get_all_python_files()
    print(f"Total Python files: {len(files)}")
    
    # Find duplicates
    duplicates = find_duplicates(files)
    print(f"\nDuplicate files (by content): {len(duplicates)} groups")
    for h, paths in duplicates.items():
        print(f"  Hash {h[:8]}:")
        for p in paths:
            print(f"    - {p.relative_to(BASE_DIR)}")
    
    # Find large files
    large = find_large_files(files)
    print(f"\nFiles > 600 LOC: {len(large)}")
    for f, lines in large[:20]:
        print(f"  {lines:>4} lines: {f.relative_to(BASE_DIR)}")
    
    # Categorize
    categories = categorize_files(files)
    print(f"\nFile categories:")
    for cat, cat_files in sorted(categories.items()):
        print(f"  {cat}: {len(cat_files)} files")


if __name__ == "__main__":
    main()
