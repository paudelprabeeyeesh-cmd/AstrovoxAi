import os

path = '02-Backend/app/api/routers/temporal_route.py'
with open(path, 'r') as f:
    content = f.read()

old = '@router.post("/ai/patterns/detect")\ndef detect_patterns(sequences: List[List[str]] = Body(...)):\n    _pattern_recognizer = HistoricalPatternRecognizer()\n    for seq in sequences:\n        _pattern_recognizer.observe(seq)\n    patterns = _pattern_recognizer.detect_patterns()\n    return {"patterns": [p.__dict__ for p in patterns]}'

new = '@router.post("/ai/patterns/detect")\ndef detect_patterns(sequences: List[List[str]] = Body(...)):\n    for seq in sequences:\n        _pattern_recognizer.observe(seq)\n    patterns = _pattern_recognizer.detect_patterns()\n    return {"patterns": [p.__dict__ for p in patterns]}'

if old in content:
    content = content.replace(old, new, 1)
    with open(path, 'w') as f:
        f.write(content)
    print('Fixed pattern_recognizer bug')
else:
    print('Pattern not found in file')
    # Show context around the function
    idx = content.find('def detect_patterns')
    if idx != -1:
        print('Context:')
        print(content[idx:idx+400])
