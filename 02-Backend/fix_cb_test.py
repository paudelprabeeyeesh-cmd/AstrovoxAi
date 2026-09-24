with open('api_gateway/tests/test_circuit_breaker.py', 'r', encoding='utf-8') as f:
    content = f.read()

old = 'assert cb.get_state("k1")["failure_count"] == 1'
new = 'state = cb.get_state("k1")\n        assert state["failure_count"] == 1'

if old in content:
    content = content.replace(old, new)
    with open('api_gateway/tests/test_circuit_breaker.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print('Replaced successfully')
else:
    print('Old string not found')
    idx = content.find('test_records_failure')
    print(repr(content[idx:idx+500]))
