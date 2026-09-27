# AstrovoxAI LLM Training Pipeline

## Phase 0 — Architecture Verification
```bash
python -m pytest tests/test_phase0_architecture.py -v
```

## Phase 1 — Tokenizer Training
```bash
python -m models.llm.tokenizer.train_tokenizer --input data/corpus.txt --vocab-size 32000 --algorithm bpe --output tokenizer.json
```

## Phase 2 — Dataset Preparation
```python
from models.llm.training_data.pipeline import build_default_pipeline, run_pipeline
pipeline = build_default_pipeline(input_dir="data/raw", output_path="data/processed/train.jsonl")
run_pipeline(pipeline)
```

## Phase 3 — Curriculum Learning
```python
from models.llm.training.curriculum import CurriculumScheduler, CurriculumSampler
scheduler = CurriculumSampler(datasets, schedule=[("language", 0.3), ("books", 0.4), ("code", 0.3)])
```

## Phase 4 — Pretraining
```bash
python -m models.llm.training.pretrain --config models/llm/configs/config_4b.yaml --resume checkpoints/latest.pt
```

## Phase 5 — Stability
- Gradient clipping: `gradient_clip_norm: 1.0`
- Warmup: `warmup_steps: 500`
- Cosine LR: `lr_scheduler: cosine`
- Mixed precision: `mixed_precision: bf16`
- Gradient checkpointing: `gradient_checkpointing: true`

## Phase 6 — Scaling Progression
```python
from models.llm.training.scaling import ScalingProgression
progression = ScalingProgression([
    "models/llm/configs/config_100m.yaml",
    "models/llm/configs/config_1b.yaml",
    "models/llm/configs/config_4b.yaml",
])
```

## Phase 7 — Instruction Tuning
```bash
python -m models.llm.training.instruction_tune --base-model model.pt --instructions data/instructions.jsonl
```

## Phase 8 — Evaluation
```python
from models.llm.training.evaluation import Evaluator
evaluator = Evaluator(model, tokenizer)
ppl = evaluator.perplexity(val_loader)
acc = evaluator.accuracy(val_loader)
```

## Phase 9 — Inference Optimization
```python
from models.llm.inference.optimization import InferenceOptimizer
optimizer = InferenceOptimizer(model, tokenizer)
optimizer.enable_kv_cache()
text = optimizer.generate("Hello")
```

## Phase 10 — Experiment Tracking
```python
from models.llm.training.experiment_tracker import ExperimentLogger
tracker = ExperimentLogger("experiments")
tracker.log_config(config)
tracker.log_metrics({"loss": 2.5}, step=100)
tracker.log_artifact("model.pt")
tracker.close()
```

## Configs
- `models/llm/configs/config_4b.yaml` — 3.7B parameter model
- `models/llm/configs/config_8b.yaml` — 6.6B parameter model  
- `models/llm/configs/config_13b.yaml` — 12.9B parameter model

## Key Features
- ✅ RMSNorm + RoPE + SwiGLU architecture
- ✅ Meta-device initialization for large models
- ✅ Streaming dataset pipeline
- ✅ Curriculum learning support
- ✅ Mixed precision training (BF16/FP16)
- ✅ Gradient checkpointing
- ✅ KV cache for inference
- ✅ Experiment tracking
- ✅ Scaling progression
