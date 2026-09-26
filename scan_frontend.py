import os, re

patterns = [
    (r'(?i)(password|secret|api_key|apikey|token|authorization)\s*=\s*["\'][^"\']{8,}["\']', 'hardcoded secret'),
    (r'\bprint\(', 'print statement'),
]

for root, dirs, files in os.walk('frontend'):
    for f in files:
        if f.endswith(('.js', '.ts', '.jsx', '.tsx')):
            path = os.path.join(root, f)
            with open(path, 'r', errors='ignore') as fh:
                for i, line in enumerate(fh, 1):
                    for pat, desc in patterns:
                        if re.search(pat, line):
                            print(f'{path}:{i}: {desc}: {line.strip()[:80]}')
