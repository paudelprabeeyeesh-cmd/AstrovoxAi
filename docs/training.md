# Distributed Training

AstrovoxAI supports distributed training across multiple GPUs and nodes using PyTorch DDP, FSDP, and custom ring-allreduce implementations.

## Features
- **Multi-GPU Training**: DDP and FSDP with gradient sharding
- **Multi-Node Training**: TCP-based and NCCL-based communication
- **Sharded Checkpoints**: Save/load sharded model checkpoints
- **Optimizer Sharding**: Partition optimizer states across workers
- **Mixed Precision**: BF16/FP16 with loss scaling
- **Gradient Accumulation**: Effective batch size scaling

## Usage
```python
from ASTROVOX_AI.ai_core.distributed.distributed_training import DistributedTraining
import torch.nn as nn
import torch.optim as optim

model = nn.Transformer()
optimizer = optim.AdamW(model.parameters(), lr=1e-4)
trainer = DistributedTraining(model, optimizer, world_size=4, rank=0)
loss = trainer.train_step(batch, loss_fn=nn.CrossEntropyLoss())
trainer.save_checkpoint("checkpoint.pt")
```

## Slurm Integration
```bash
#!/bin/bash
#SBATCH --nodes=4
#SBATCH --gpus-per-node=8
srun torchrun --nnodes=4 --nproc_per_node=8 train.py
```
