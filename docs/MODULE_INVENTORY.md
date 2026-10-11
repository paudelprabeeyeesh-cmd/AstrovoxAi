# Module Inventory — AstrovoxAi

Generated: 2026-10-10 · Method: AST import graph over every `.py` file under
`02-Backend/app/` (1,503 files scanned), recording the top-level name of each
module-level import.

## Classification rule
A top-level package or module is **live** if `02-Backend/app/` imports it.
Everything else is **experimental** (research toys and simulations) or **tooling**.

## Live modules (7)

| Module | Import sites in `app/` | Role |
|---|---:|---|
| `app` | — | The FastAPI application itself (entry point `app.main`) |
| `routes` | many | Route handlers included by `app.main` |
| `api_gateway` | many | API gateway, rate limiting, webhooks |
| `sandboxing` | many | Tool execution sandbox + metrics |
| `database` | many | Database access layer (`database/database.py`, connection, query builder) |
| `retrieval` | some | RAG / retrieval helpers |
| `memory_persistence` | some | Persistent memory store |

## Experimental modules (107)

Imported by nothing under `app/`. These are NumPy simulations and research
scaffolds, not product code.

```
active_learning          adaptive_learning       advanced_backend
advanced_learning        advanced_optimization   advanced_planning
advanced_reasoning       adversarial_defense     agent_modeling
agentic_loop             agi_core                agi_safety
alignment                analytics               audit
autonomous_agents        backup_recovery         cache_coherence
caching                  causality               check_syntax (script)
code_aware_retrieval     cognitive_architecture  complex_learning
complex_reasoning        consciousness           constrained_opt
context_management       continual_learning      continual_learning_advanced
contrastive_learning     coordinate_descent      creativity
cryptographic_protocols  curriculum_learning     curriculum_learning_advanced
data_pipeline            diff_patch_engine       differential_privacy
disaster_recovery        distributed_computing   emergent_abilities
ethical_reasoning        evaluation              evals
evolutionary_computation few_shot_learning       final_boss
final_system             fix_cb (script)         fix_cb_test (script)
fix_tool_results (script) gradient_descent       gradient_descent_advanced
gunicorn.conf            hardware_abstraction    homomorphic_encryption
inference_engine         injection_defense       interpretability
knowledge_graph          learning_to_learn       lifelong_learning
lifelong_learning_advanced  meta_learning_advanced  metacognition
migrate (script)         model_architecture       multi_agent
multi_task_learning      multimodal              online_learning
online_meta_learning     performance_optimization  plugin_system
product_polish           proximal_algorithms     quantization
quantum_ml               quantum_optimization    reasoning_engine
representation_learning  resource_management     safety_moderation
scalability_patterns     security_audit          security_orchestration
self_supervised_learning  semi_supervised         simulation_engine
social_intelligence      spatial_reasoning       streaming_analytics
superintelligence        swarm_intelligence      system_integration
temporal_reasoning       tensor_engine           test_imports (script)
threat_intelligence      training_engine         transfer_learning
transfer_learning_advanced  verification_loop   world_model
zero_shot_learning
```

## Enforcement

`tools/check_live_imports.py` fails if any module under the live set imports an
experimental module. It runs in CI (`.github/workflows/ci.yml`), so product code
cannot grow a dependency on experimental code.

Reproduce with:

```
python tools/check_live_imports.py
```
