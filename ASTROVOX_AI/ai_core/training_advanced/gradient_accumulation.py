import torch


class GradientAccumulator:
    def __init__(self, accumulation_steps: int = 4, clip_grad_norm: float = 1.0):
        self.accumulation_steps = accumulation_steps
        self.clip_grad_norm = clip_grad_norm
        self.current_step = 0

    def backward(self, loss: torch.Tensor) -> None:
        scaled_loss = loss / self.accumulation_steps
        scaled_loss.backward()
        self.current_step += 1

    def step(self, optimizer: torch.optim.Optimizer) -> bool:
        if self.current_step % self.accumulation_steps == 0:
            if self.clip_grad_norm > 0:
                torch.nn.utils.clip_grad_norm_(optimizer.param_groups[0]['params'], self.clip_grad_norm)
            optimizer.step()
            optimizer.zero_grad()
            return True
        return False

    def reset(self) -> None:
        self.current_step = 0
