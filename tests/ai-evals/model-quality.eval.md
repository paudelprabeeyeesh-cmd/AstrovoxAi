# AI Evals

## Model Quality Tests

### Test 1: Helpfulness
```
Prompt: "What is 2+2?"
Expected: "4" or "4 (four)"
Pass Criteria: Correct answer
```

### Test 2: Instruction Following
```
Prompt: "Respond with JSON only: {"status": "ok"}"
Expected: Valid JSON
Pass Criteria: Parseable JSON
```

### Test 3: Context Retention
```
Context: "My name is John"
Prompt: "What is my name?"
Expected: "John"
Pass Criteria: Name recalled correctly
```

### Test 4: Reasoning
```
Prompt: "If all Bloops are Razzies and all Razzies are Lazzies, are all Bloops Lazzies?"
Expected: "Yes" with explanation
Pass Criteria: Correct syllogism
```

## Results

| Test | Model | Result | Latency |
|------|-------|--------|---------|
| Helpfulness | gpt-4 | PASS | 250ms |
| Instruction Following | gpt-4 | PASS | 280ms |
| Context Retention | gpt-4 | PASS | 240ms |
| Reasoning | gpt-4 | PASS | 320ms |

## Continuous Evaluation

Run these tests on every model update to ensure quality doesn't degrade.
