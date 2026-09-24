import numpy as np


class LossSpikeRecovery:
    def __init__(self, window=100, threshold=3.0):
        self.window = window
        self.threshold = threshold
        self.loss_history = []

    def detect_spike(self, loss):
        self.loss_history.append(loss)
        if len(self.loss_history) < self.window:
            return False
        recent = self.loss_history[-self.window:]
        mean = np.mean(recent[:-1])
        std = np.std(recent[:-1])
        if std == 0:
            return False
        z = (recent[-1] - mean) / std
        return abs(z) > self.threshold

    def rollback(self, training_run):
        if training_run.checkpoints:
            return training_run.checkpoints[-1]
        return None

    def reduce_lr(self, training_run):
        training_run.lr *= 0.1

    def restart(self, training_run):
        ckpt = self.rollback(training_run)
        self.reduce_lr(training_run)
        return ckpt
