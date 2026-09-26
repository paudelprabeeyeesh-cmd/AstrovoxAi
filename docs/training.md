# Distributed Training

AstrovoxAI supports distributed training across multiple GPUs and nodes using PyTorch DDP, FSDP, and custom ring-allreduce implementations. The training infrastructure supports fine-tuning, instruction tuning, and RLHF at scale.

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                     DISTRIBUTED TRAINING                             │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────────────┐  │
│  │   Dataset    │    │   Data       │    │   Training           │  │
│  │   Loader     │───►│   Sampler    │───►│   Orchestrator       │  │
│  └──────────────┘    └──────────────┘    └──────────┬───────────┘  │
│                                                     │               │
│  ┌──────────────┐    ┌──────────────┐    ┌─────────▼───────────┐  │
│  │   Gradient   │    │   Optimizer  │    │   Distributed       │  │
│  │   Accumulator│◄──►│   Sharding   │◄──►│   AllReduce          │  │
│  └──────────────┘    └──────────────┘    └─────────┬───────────┘  │
│                                                     │               │
│  ┌──────────────┐    ┌──────────────┐    ┌─────────▼───────────┐  │
│  │   Mixed      │    │   Checkpoint │    │   Metrics &         │  │
│  │   Precision  │    │   Manager    │    │   Logging            │  │
│  └──────────────┘    └──────────────┘    └──────────────────────┘  │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

## Features

- **Multi-GPU Training**: DDP and FSDP with gradient sharding
- **Multi-Node Training**: TCP-based and NCCL-based communication
- **Sharded Checkpoints**: Save/load sharded model checkpoints
- **Optimizer Sharding**: Partition optimizer states across workers
- **Mixed Precision**: BF16/FP16 with loss scaling
- **Gradient Accumulation**: Effective batch size scaling
- **Curriculum Learning**: Progressive difficulty scheduling
- **Early Stopping**: Automatic convergence detection
- **Experiment Tracking**: Weights & Biases, MLflow integration

## Usage

### Basic Training

```python
from ASTROVOX_AI.ai_core.distributed.distributed_training import DistributedTraining
import torch.nn as nn
import torch.optim as optim

model = nn.Transformer()
optimizer = optim.AdamW(model.parameters(), lr=1e-4)

trainer = DistributedTraining(
    model=model,
    optimizer=optimizer,
    world_size=4,
    rank=0,
    gradient_accumulation_steps=4,
    mixed_precision=True
)

# Training loop
for epoch in range(num_epochs):
    for batch in dataloader:
        loss = trainer.train_step(
            batch,
            loss_fn=nn.CrossEntropyLoss()
        )
        trainer.log_metrics({"loss": loss})

    trainer.save_checkpoint(f"checkpoint_epoch_{epoch}.pt")
```

### FSDP Training

```python
from ASTROVOX_AI.ai_core.distributed.fsdp_trainer import FSDPTrainer

trainer = FSDPTrainer(
    model=model,
    optimizer=optimizer,
    world_size=8,
    sharding_strategy="FULL_SHARD",  # or "SHARD_GRAD_OP", "NO_SHARD"
    mixed_precision=True,
    cpu_offload=False  # Offload optimizer states to CPU
)

trainer.fit(dataloader, num_epochs=10)
```

### RLHF Training

```python
from ASTROVOX_AI.ai_core.alignment.rlhf_trainer import RLHFTrainer

trainer = RLHFTrainer(
    model=model,
    reward_model=reward_model,
    reference_model=reference_model,
    kl_coef=0.1
)

for batch in preference_data:
    loss = trainer.rlhf_step(batch)
    trainer.log_metrics({"rlhf_loss": loss})
```

### Instruction Tuning

```python
from ASTROVOX_AI.ai_core.training.instruction_tuner import InstructionTuner

tuner = InstructionTuner(
    model=model,
    tokenizer=tokenizer,
    lora_rank=16,
    lora_alpha=32
)

tuner.train(
    instructions=instruction_dataset,
    num_epochs=3,
    batch_size=8,
    learning_rate=2e-4
)
```

## Slurm Integration

```bash
#!/bin/bash
#SBATCH --job-name=astrovox-train
#SBATCH --nodes=4
#SBATCH --gpus-per-node=8
#SBATCH --cpus-per-task=8
#SBATCH --mem=256GB
#SBATCH --time=24:00:00

srun torchrun \
    --nnodes=4 \
    --nproc_per_node=8 \
    --rdzv_backend=c10d \
    --rdzv_endpoint=$MASTER_ADDR:29500 \
    train.py \
    --config configs/llama-2-7b.yaml
```

## Kubernetes Training

```yaml
apiVersion: batch/v1
kind: Job
metadata:
  name: astrovox-training
spec:
  template:
    spec:
      containers:
        - name: trainer
          image: astrovox/trainer:latest
          command: ["python", "train.py"]
          resources:
            limits:
              nvidia.com/gpu: 8
          env:
            - name: WORLD_SIZE
              value: "8"
            - name: RANK
              valueFrom:
                fieldRef:
                  fieldPath: metadata.name
      restartPolicy: Never
```

## Checkpoint Management

```python
# Save sharded checkpoint
trainer.save_sharded_checkpoint("checkpoints/epoch-5")

# Load checkpoint
trainer.load_checkpoint("checkpoints/epoch-5")

# Merge sharded checkpoint
from ASTROVOX_AI.ai_core.training.checkpoint import merge_sharded_checkpoint
merge_sharded_checkpoint("checkpoints/epoch-5", "merged/model.pt")
```

## Experiment Tracking

```python
from ASTROVOX_AI.ai_core.training.tracker import ExperimentTracker

tracker = ExperimentTracker(
    project="astrovox-training",
    experiment_name="llama-2-7b-finetune",
    tags=["instruction-tuning", "v2.0"]
)

tracker.log_params({
    "model": "llama-2-7b",
    "lr": 2e-4,
    "batch_size": 32,
    "epochs": 3
})

tracker.log_metrics({"train_loss": 0.5, "val_loss": 0.6}, step=100)
tracker.log_model(model, "model_final.pt")
```

## Data Pipeline

```python
from ASTROVOX_AI.ai_core.training.data_pipeline import (
    DataPipeline,
    StreamingDataset,
    Preprocessor
)

pipeline = DataPipeline(
    source="s3://astrovox-data/instructions",
    format="jsonl",
    batch_size=32
)

dataset = StreamingDataset(
    pipeline=pipeline,
    preprocessor=Preprocessor(
        tokenizer=tokenizer,
        max_length=2048,
        truncation=True
    )
)
```

## Performance Optimization

| Technique | Speedup | Memory Savings |
|-----------|---------|----------------|
| Mixed Precision (FP16) | 1.5-2x | 50% |
| BF16 (Ampere+) | 1.5-2x | 50% |
| Gradient Checkpointing | 1.2x | 40-60% |
| FSDP | 2-4x (multi-node) | Scales with nodes |
| LoRA Fine-tuning | 1.1x | 75% |
| Flash Attention | 2-4x | 20-30% |

## Monitoring

Track training metrics:

- Loss curves (train/validation)
- Learning rate schedule
- Gradient norms
- Memory utilization per GPU
- Throughput (samples/second)
- Model convergence indicators
