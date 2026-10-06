"""Training UI for Astrovox."""

from __future__ import annotations


class TrainerUI:
    """Training UI component."""

    def __init__(self):
        self.running = False
        self.progress = 0.0
        self.current_epoch = 0
        self.total_epochs = 0

    def start_training(self, epochs: int, steps: int) -> None:
        self.running = True
        self.total_epochs = epochs
        self.current_epoch = 0
        self.progress = 0.0

    def step(self, epoch: int, step: int, loss: float) -> dict:
        if self.total_epochs == 0:
            self.total_epochs = epoch + 1
        self.current_epoch = epoch
        self.progress = min(100.0, step / max(steps, 1) * 100)
        return {"epoch": epoch, "step": step, "loss": loss, "progress": self.progress}

    def stop(self) -> None:
        self.running = False

    def get_status(self) -> dict:
        return {"running": self.running, "epoch": self.current_epoch,
                "progress": self.progress, "total_epochs": self.total_epochs}
