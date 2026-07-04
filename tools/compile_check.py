import ast
import sys
fn = r"c:\AstrovoxAi\\.venv\\Lib\\site-packages\\bs4\\__init__.py"
with open(fn, 'rb') as f:
    src = f.read()
text = src.decode('utf-8', errors='replace')
try:
    ast.parse(text, filename=fn)
    print('OK')
except SyntaxError as se:
    print('SyntaxError detected:')
    print('  msg:', se.msg)
    print('  filename:', se.filename)
    print('  lineno:', se.lineno)
    print('  offset:', se.offset)
    print('  text repr snippet:')
    if se.text:
        print(repr(se.text))
    print('\n--- File head (first 400 chars) ---')
    print(repr(text[:400]))
    sys.exit(1)
except Exception as e:
    print('Other exception:', type(e), e)
    sys.exit(2)
