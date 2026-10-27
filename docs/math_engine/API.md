# API — AstrovoxAI Mathematics Engine

Base: mounted at `/v1/math` in `02-Backend/app/main.py` (`app.include_router(math_router)`).  
Auth: uses existing `get_user_id_from_token(authorization)` header. Errors return HTTP 400 with detail.

## Endpoints

### POST /v1/math/compute
Execute one registered math operation.

Request:
```json
{
  "topic_id": "S1.T009",
  "operation_id": "gcd",
  "inputs": { "a": 12, "b": 18 }
}
```

Response:
```json
{
  "ok": true,
  "data": {
    "topic_id": "S1.T009",
    "operation_id": "gcd",
    "status": "implemented",
    "result": { "gcd": 6, "a": 12, "b": 18 },
    "explanation": "",
    "steps": ["gcd(12, 18) = 6"],
    "assumptions": [],
    "tolerance": null,
    "warnings": [],
    "error": null,
    "verified": true
  }
}
```

On unsupported topic/operation: `ok: false`, `data.error` set, HTTP 400.

### GET /v1/math/topics
Returns the machine-readable registry (`math_engine/registry/topics.json`): `{ count, topics: [...] }`.

## Service layer (programmatic, used by API and tests)

```python
from math_engine.service import compute, list_topics, get_dispatcher

res = compute("S2.T042", "solve_quadratic", a=1, b=-3, c=2)
# res = {"topic_id":"S2.T042","operation_id":"solve_quadratic","status":"implemented",
#        "result":{"roots":[1.0,2.0],"type":"two_real","discriminant":1.0}, ...}
```

## Error contract
All errors are structured `MathResult` with `error` field; never raw stack traces to the client. Domain violations (log of negative, division by zero, singular matrix, support mismatch) return `DomainError` messages. Malformed input returns `ValidationError`.

## Safety
- No `eval()` on user input. Expression parsing uses a whitelisted shunting-yard parser (`evaluate_expression`).
- Input-size and iteration limits enforced (`math_engine/core/limits.py`).
- No secrets in logs/responses.

## Example calls
- Arithmetic: `compute("S1.T016","power", base=2, exp=10)` -> 1024
- Algebra: `compute("S2.T040","solve_linear", a=2, b=-10)` -> x=5
- Linear algebra: `compute("S5.T131","mat_mul", a=[[1,2],[3,4]], b=[[1,0],[0,1]])`
- Calculus: `compute("S6.T179","derivative", expr="x**2", var="x", point=3)` -> 6
- Optimizer: `compute("S7.T229","adam_step", param=[1.0], grad=[0.5], t=1)`
- Probability: `compute("S8.T265","bayes", p_a=0.01, p_b_given_a=0.9, p_b=0.1)`
- Transformer attention: `compute("S16.T643","scaled_dot_product_attention", Q=[[1,0]],K=[[1,0]],V=[[10]])`
