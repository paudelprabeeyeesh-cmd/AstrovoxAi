import os, re

# Scan for specific obvious bugs in frontend
patterns = [
    (r'\bparseInt\s*\([^,]+\)(?!\s*,\s*10)', 'parseInt without radix'),
    (r'\.addEventListener\([^,]+,\s*function\s*\([^)]*\)\s*\{[^}]*\}\s*\)', 'anonymous event listener'),
    (r'on\w+\s*=\s*["\']javascript:', 'javascript: in event handler'),
    (r'\bfunction\s+\w+\s*\([^)]*\)\s*:\s*$', 'arrow function syntax error'),
    (r'/\*[^*]*\*+(?:[^/*][^*]*\*+)*/', 'multi-line comment in JS'),
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
