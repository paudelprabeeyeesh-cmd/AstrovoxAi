with open('api_gateway/tests/test_circuit_breaker.py', 'rb') as f:
    data = bytearray(f.read())

lines = data.split(b'\n')
line = bytearray(lines[189])
print('Before:', bytes(line).decode('utf-8'))
print('Pos 32 char:', chr(line[32]), hex(line[32]))

# Fix: position 32 should be ')' not ']'
line[32] = ord(')')
lines[189] = bytes(line)
print('After:', bytes(line).decode('utf-8'))

with open('api_gateway/tests/test_circuit_breaker.py', 'wb') as f:
    f.write(b'\n'.join(lines))
print('Fixed')
