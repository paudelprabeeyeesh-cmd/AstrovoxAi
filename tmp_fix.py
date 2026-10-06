import re, ast

files = ['builders_55_60.py', 'builders_61_70.py', 'builders_71_80.py']
for fname in files:
    path = 'scripts/phases/' + fname
    text = open(path, encoding='utf-8').read()
    print(fname + ': ' + str(len(text)) + ' bytes')

    parts = text.split('def build_phase_')
    assert len(parts) > 1, 'no boundaries in ' + fname

    header = 'from scripts.phases._shared import write_module, ensure_dirs\n\n'
    out_parts = [header]
    for part in parts[1:]:
        if part.startswith('    \"\"\"'):
            m = re.search(r'write_module\("([^"]+)", code\)', part)
            assert m, 'no write_module found in ' + fname
            part = m.group(1) + '() -> str:\n' + part
        out_parts.append('def build_phase_' + part)

    text = chr(10).join(out_parts)
    if not text.endswith(chr(10)):
        text += chr(10)
    open(path, 'w', encoding='utf-8', newline=chr(10)).write(text)

    tree = ast.parse(text)
    funcs = [n.name for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name.startswith('build_phase_')]
    print('  -> ' + fname + ' rebuilt: ' + str(len(funcs)) + ' functions, first=' + funcs[0] + ', last=' + funcs[-1])
