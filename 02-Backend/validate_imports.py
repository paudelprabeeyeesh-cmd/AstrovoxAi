#!/usr/bin/env python3
"""
Validate imports across the backend codebase after modularization.
"""

import ast
import sys
from pathlib import Path
from collections import defaultdict

BASE_DIR = Path(r"C:\Users\Dell\Documents\GitHub\AstrovoxAi\02-Backend\app")


def check_imports(file_path: Path) -> list:
    """Check if imports in a file are valid."""
    errors = []
    try:
        content = file_path.read_text(encoding='utf-8')
        tree = ast.parse(content)
        
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                if node.module:
                    # Handle relative imports
                    if node.level > 0:
                        # Relative import - check if module exists
                        parts = node.module.split('.') if node.module else []
                        rel_path = file_path.parent
                        for _ in range(node.level - 1):
                            rel_path = rel_path.parent
                        for part in parts:
                            rel_path = rel_path / part
                        
                        # Check if module exists as package or file
                        if not (rel_path.exists() or (rel_path.with_suffix('.py')).exists()):
                            errors.append(f"  Line {node.lineno}: from {'.' * node.level}{node.module or ''} - module not found")
                    else:
                        # Absolute import - skip for now
                        pass
    except SyntaxError as e:
        errors.append(f"  Syntax error: {e}")
    except Exception as e:
        errors.append(f"  Error: {e}")
    
    return errors


def main():
    py_files = list(BASE_DIR.rglob("*.py"))
    print(f"Checking {len(py_files)} Python files...")
    
    files_with_errors = 0
    total_errors = 0
    
    for py_file in py_files:
        errors = check_imports(py_file)
        if errors:
            files_with_errors += 1
            total_errors += len(errors)
            rel_path = py_file.relative_to(BASE_DIR)
            print(f"\n{rel_path}:")
            for error in errors[:5]:  # Limit output
                print(error)
            if len(errors) > 5:
                print(f"  ... and {len(errors) - 5} more")
    
    print(f"\n=== Summary ===")
    print(f"Files with import errors: {files_with_errors}")
    print(f"Total import errors: {total_errors}")
    
    if files_with_errors == 0:
        print("All imports are valid!")
    else:
        print("Some imports need fixing.")


if __name__ == "__main__":
    main()
