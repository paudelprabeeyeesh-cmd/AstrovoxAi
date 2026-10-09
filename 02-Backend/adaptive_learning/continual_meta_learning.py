import numpy as np
from typing import Dict, List, Optional, Any
from .learning_to_learn import MetaLearner, TaskBatch


class ContinualMetaLearner:
    def __init__(self, inner_lr: float = 0.01, outer_lr: float = 0.001, adaptation_steps: int = 5, buffer_size: int = 100):
        self.meta_learner = MetaLearner(inner_lr=inner_lr, outer_lr=outer_lr, adaptation_steps=adaptation_steps)
        self.buffer_size = buffer_size
        self.replay_buffer: List[TaskBatch] = []
        self.seen_tasks: List[str] = []
        self.task_performance: Dict[str, List[float]] = {}
        self._input_dim: Optional[int] = None

    def learn_task(self, task_id: str, task: TaskBatch, use_replay: bool = True) -> Dict[str, Any]:
        if self._input_dim is None:
            self._input_dim = task.support_x.shape[1]
            if not self.meta_learner.meta_params:
                self.meta_learner.initialize_params({
                    "W": (self._input_dim, max(2, int(np.max(task.support_y)) + 1)),
                    "b": (max(2, int(np.max(task.support_y)) + 1),),
                })
        batch = [task]
        if use_replay and self.replay_buffer:
            replay_tasks = self._sample_replay(len(self.replay_buffer))
            batch.extend(replay_tasks)
        loss = self.meta_learner.meta_train_step(batch)
        self._store_task(task)
        self.task_performance.setdefault(task_id, []).append(loss)
        self.seen_tasks.append(task_id)
        return {"task_id": task_id, "loss": loss, "buffer_size": len(self.replay_buffer)}

    def _sample_replay(self, n: int) -> List[TaskBatch]:
        if not self.replay_buffer:
            return []
        indices = np.random.choice(len(self.replay_buffer), size=min(n, len(self.replay_buffer)), replace=False)
        return [self.replay_buffer[int(i)] for i in indices]

    def _store_task(self, task: TaskBatch) -> None:
        self.replay_buffer.append(task)
        if len(self.replay_buffer) > self.buffer_size:
            self.replay_buffer.pop(0)

    def adapt_to_new_task(self, task: TaskBatch) -> Dict[str, np.ndarray]:
        return self.meta_learner.adapt_to_task(task)

    def evaluate_task(self, task: TaskBatch) -> float:
        adapted = self.adapt_to_new_task(task)
        logits = task.query_x @ adapted.get("W", np.zeros((task.query_x.shape[1], 1))) + adapted.get("b", np.zeros(1))
        probs = MetaLearner._softmax(logits)
        y = task.query_y.astype(int)
        loss = -np.mean(np.log(probs[np.arange(len(y)), y] + 1e-12))
        return float(loss)

    def get_task_statistics(self) -> Dict[str, Dict[str, float]]:
        stats = {}
        for task_id, losses in self.task_performance.items():
            stats[task_id] = {
                "mean_loss": float(np.mean(losses)),
                "std_loss": float(np.std(losses)),
                "last_loss": float(losses[-1]),
            }
        return stats
