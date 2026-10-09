import math
import random
from typing import Any, Callable, Dict, Iterable, List, Optional, Tuple

from training_engine.data_loader import DataLoader
from training_engine.checkpoint_manager import CheckpointManager
from training_engine.lr_scheduler import LRScheduler, TrainConfig


class TrainerLoop:
    def __init__(
        self,
        model: Any,
        optimizer: Any,
        loss_fn: Callable[[Any, Any], float],
        config: TrainConfig,
        data: Optional[List[Any]] = None,
        checkpoint_dir: str = "checkpoints",
    ) -> None:
        self.model = model
        self.optimizer = optimizer
        self.loss_fn = loss_fn
        self.config = config
        self.loader = DataLoader(data=data, batch_size=1, shuffle=True)
        self.checkpoint_manager = CheckpointManager(directory=checkpoint_dir)
        self.scheduler = LRScheduler(optimizer, config)
        self.global_step = 0
        self.history: List[float] = []

    def train_step(self, batch: List[Any]) -> float:
        x, y = batch[0]
        loss = self.loss_fn(self.model(x), y)
        self.history.append(loss)
        return loss

    def run(self, max_steps: Optional[int] = None) -> List[float]:
        max_steps = int(max_steps or self.config.max_steps)
        data_iter = iter(self.loader)
        for _ in range(max_steps):
            try:
                batch = next(data_iter)
            except StopIteration:
                data_iter = iter(self.loader)
                try:
                    batch = next(data_iter)
                except StopIteration:
                    batch = [(None, None)]
            self.scheduler.step()
            loss = self.train_step(batch)
            self.global_step += 1
            self.checkpoint_manager.save(self.global_step, {"loss": loss, "step": self.global_step})
        return self.history

    def evaluate(self, data: Optional[List[Any]] = None) -> float:
        eval_loader = DataLoader(data=data, batch_size=1, shuffle=False)
        total_loss = 0.0
        count = 0
        for batch in eval_loader:
            x, y = batch[0]
            loss = self.loss_fn(self.model(x), y)
            total_loss += loss
            count += 1
        return total_loss / max(count, 1)

    def resume(self) -> int:
        step = self.checkpoint_manager.latest()
        if step is None:
            return 0
        _, state = self.checkpoint_manager.load(step)
        self.global_step = int(state.get("step", step))
        self.scheduler.step_count = self.global_step
        return self.global_step
