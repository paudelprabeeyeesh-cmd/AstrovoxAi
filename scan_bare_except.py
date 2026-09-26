import ast, os

def check_file(path):
    try:
        with open(path, 'r') as f:
            source = f.read()
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.ExceptHandler):
                if node.type is None:
                    print(f'{path}:{node.lineno}: bare except')
    except SyntaxError as e:
        print(f'{path}: syntax error: {e}')
    except Exception as e:
        print(f'{path}: error: {e}')

for root, dirs, files in os.walk('02-Backend/app'):
    for f in files:
        if f.endswith('.py'):
            check_file(os.path.join(root, f))
for root, dirs, files in os.walk('ASTROVOX_AI/ai_core'):
    for f in files:
        if f.endswith('.py'):
            check_file(os.path.join(root, f))
