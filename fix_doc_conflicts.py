import re
import os
from pathlib import Path

def fix_doc_conflicts(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    original = content
    
    # Remove conflict markers, keep HEAD version
    content = re.sub(
        r'<<<<<<< HEAD\r?\n(.*?)\r?\n=======\r?\n.*?\r?\n>>>>>>> [a-f0-9]+',
        r'\1',
        content,
        flags=re.DOTALL
    )
    
    # Also handle cases where there's no incoming section
    content = re.sub(
        r'<<<<<<< HEAD\r?\n(.*?)\r?\n>>>>>>> [a-f0-9]+',
        r'\1',
        content,
        flags=re.DOTALL
    )
    
    if content != original:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        return True
    return False

# Fix remaining doc files
doc_files = [
    'README.md',
    'CHANGELOG.md',
    'CONTRIBUTING.md',
    'DEPLOYMENT.md',
    'docs/ARCHITECTURE.md',
    'docs/CONTRIBUTING.md',
    'docs/DEPLOYMENT_GUIDE.md',
    'docs/architecture-review.md'
]

fixed = 0
for file_path in doc_files:
    if os.path.exists(file_path):
        if fix_doc_conflicts(file_path):
            print(f"Fixed: {file_path}")
            fixed += 1

print(f"Fixed {fixed} documentation files")
