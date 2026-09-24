import ast
line = 'proxy.call("k1", lambda: (_ for _ in ()).throw(ValueError("err")))'
try:
    ast.parse(line, mode='eval')
    print("Line 189 is syntactically valid")
except SyntaxError as e:
    print(f"SyntaxError: {e.msg} at col {e.offset}")

# Now check the whole function context
src = '''
def test_records_failure(self):
    cb = CircuitBreaker(name="p")
    proxy = CircuitBreakerProxy(cb)
    with pytest.raises(ValueError):
        proxy.call("k1", lambda: (_ for _ in ()).throw(ValueError("err")))
    assert cb.get_state("k1")["failure_count"] == 1
'''
try:
    ast.parse(src)
    print("Whole block is syntactically valid")
except SyntaxError as e:
    print(f"SyntaxError: {e.msg} at line {e.lineno}, col {e.offset}")
