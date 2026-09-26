from typing import Optional, Dict, List
import torch
import torch.nn as nn
import torch.distributed as dist
from ASTROVOX_AI.ai_core.distributed.data_parallelism import DataParallelism, DataParallelConfig
from ASTROVOX_AI.ai_core.distributed.tensor_parallelism import TensorParallelism, TensorParallelConfig
from ASTROVOX_AI.ai_core.distributed.pipeline_parallelism import PipelineParallelism, PipelineConfig
from ASTROVOX_AI.ai_core.distributed.fsdp import FSDP, FSDPConfig
from ASTROVOX_AI.ai_core.distributed.fault_recovery import FaultRecoveryManager, FaultRecoveryConfig


class DistributedTraining:
    def __init__(self, model: nn.Module, optimizer: torch.optim.Optimizer, world_size: int, rank: int, parallelism: str = "data", device_ids: Optional[List[int]] = None, zero_stage: int = 0):
        self.model = model
        self.optimizer = optimizer
        self.world_size = world_size
        self.rank = rank
        self.parallelism = parallelism
        self.device_ids = device_ids
        if parallelism == "data":
            config = DataParallelConfig(world_size=world_size, rank=rank)
            self.dp = DataParallelism(model, config, device_ids=device_ids)
            self.model = self.dp.model
        elif parallelism == "tensor":
            tp_config = TensorParallelConfig(world_size=world_size, rank=rank)
            self.tp = TensorParallelism(tp_config)
            self.model = self.tp.apply_to_model(model)
        elif parallelism == "pipeline":
            pp_config = PipelineConfig(world_size=world_size, rank=rank, num_stages=world_size)
            stages = pp_config.partition(model, num_stages=world_size)
            self.pp = PipelineParallelism(pp_config)
            self.pp.stages = stages
            self.model = stages[rank] if rank < len(stages) else nn.Identity()
        elif parallelism == "fsdp":
            fsdp_config = FSDPConfig(world_size=world_size, rank=rank)
            self.fsdp = FSDP(model, fsdp_config)
            self.model = self.fsdp.wrapper
        else:
            self.model = nn.parallel.DistributedDataParallel(model, device_ids=device_ids)
        self.fault_recovery = FaultRecoveryManager(FaultRecoveryConfig())

    def train_step(self, batch: Dict[str, torch.Tensor], loss_fn: callable) -> float:
        self.model.train()
        input_ids = batch["input_ids"].to(next(self.model.parameters()).device)
        labels = batch.get("labels", input_ids).to(input_ids.device)
        logits = self.model(input_ids)
        loss = loss_fn(logits.view(-1, logits.size(-1)), labels.view(-1))
        loss.backward()
        if self.parallelism == "data":
            self.optimizer.step()
        elif self.parallelism == "fsdp":
            self.fsdp.wrapper._shard_params()
            self.optimizer.step()
        else:
            self.optimizer.step()
        self.optimizer.zero_grad()
        return loss.item()

    def save_checkpoint(self, path: str) -> None:
        state = {"model": self.model.state_dict(), "optimizer": self.optimizer.state_dict(), "rank": self.rank, "parallelism": self.parallelism}
        torch.save(state, path)

    def load_checkpoint(self, path: str) -> None:
        ckpt = torch.load(path, map_location="cpu", weights_only=False)
        self.model.load_state_dict(ckpt["model"])
        self.optimizer.load_state_dict(ckpt["optimizer"])

    def cleanup(self) -> None:
        dist.destroy_process_group()
