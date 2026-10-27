# Architecture — AstrovoxAI Mathematics Engine

## Design goals
- Lightweight (4 GB RAM Windows laptop): lazy optional deps, no scipy/sklearn at import, numpy + sympy only.
- No `eval()`: safe whitelisted expression parser.
- Honest statuses: planned/scaffolded/implemented/tested/verified/blocked.
- Additive: does not modify existing auth/chat/database/routers.

## Layered structure

```
math_engine/
  registry/   topics.json (machine-readable), loader.py, schemas.py, status.py, register.py, generate_registry.py
  core/       dispatcher.py, result.py, execution_context.py, errors.py, validation.py, limits.py
  symbolic/   arithmetic.py, algebra.py, functions.py, geometry.py
  numerical/  roots.py
  linear_algebra/  matrices.py
  calculus/   differentiation.py
  probability/  distributions.py
  statistics/   descriptive.py
  information_theory/  entropy.py
  discrete/     logic.py
  machine_learning/ losses.py
  deep_learning/    activations.py
  transformers/     attention.py
  reinforcement_learning/  mdp.py
  advanced/         measure_theory.py
  service.py        thin service layer (compute, list_topics)
  api_routes.py     FastAPI router (/v1/math)
  tests/            unit/ property/ regression/ integration/ topic_coverage/
  docs/
```

## Execution contract (common)

Every request: `topic_id`, `operation_id`, validated `inputs`, optional `level`, `precision`, `tolerance`, execution `limits`.

Every result (`MathResult`): `topic_id`, `operation_id`, `status`, `result`, `explanation`, `steps`, `assumptions`, `tolerance`, `warnings`, `error`, `verified`.

Errors: `MathEngineError`, `DomainError`, `PrecisionError`, `ValidationError`, `UnsupportedTopicError`, `ResourceLimitError`.

## Dispatcher

`Dispatcher.dispatch(topic_id, operation_id, **kwargs)` routes to a registered callable. Handlers are registered in `registry/register.py` (`build_dispatcher()`). Unknown operations raise `UnsupportedTopicError` with the registry status.

## Integration

Service layer `math_engine.service.compute(topic_id, operation_id, **kwargs)` -> dict.  
FastAPI router `math_engine.api_routes.router` mounted in `02-Backend/app/main.py` at `/v1/math`:
- `POST /v1/math/compute` {topic_id, operation_id, inputs}
- `GET /v1/math/topics`

Preserves existing auth (`get_user_id_from_token`) and error handling. Additive `app.include_router(math_router)`.

## Topic statuses (from registry, 850 topics)

| Status | Meaning | Count (approx) |
|--------|---------|----------------|
| implemented | real computation + tests | most of Levels 0–4 computable topics |
| scaffolded | framework/demo, no independent verification | Section 13, 19 theoretical topics |
| planned | catalogued, not implemented | residual advanced topics |

A topic is marked `tested`/`verified` only when automated tests pass with independent correctness evidence.

## Dependencies
- Required: numpy, sympy (both installed)
- Optional (lazy, not required): scipy, sklearn (not installed; features using them are unavailable)
- Standard library only for: arithmetic, algebra, discrete, numerical root finding, info theory

## Resource limits (lightweight mode)
`math_engine/core/limits.py`: max_matrix_dim 2048, max_tensor_elements 1e6, max_iterations 100000, max_polynomial_degree 512, no GPU, no heavy deps.
