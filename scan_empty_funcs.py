import os, re

for root, dirs, files in os.walk('02-Backend/app'):
    for f in files:
        if f.endswith('.py'):
            path = os.path.join(root, f)
            with open(path, 'r', errors='ignore') as fh:
                lines = fh.readlines()
                for i, line in enumerate(lines, 1):
                    if re.match(r'^\s*def\s+\w+\([^)]*\)\s*:\s*$', line):
                        if i < len(lines) and lines[i].strip() == 'pass':
                            print(f'{path}:{i+1}: empty function with pass')
