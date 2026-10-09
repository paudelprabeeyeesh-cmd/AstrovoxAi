import numpy as np


class SilentDataCorruptionDetector:
    def __init__(self):
        self.loss_patterns = []

    def record_loss(self, loss):
        self.loss_patterns.append(loss)

    def detect_via_loss_patterns(self):
        if len(self.loss_patterns) < 10:
            return False
        arr = np.array(self.loss_patterns)
        diffs = np.diff(arr)
        mean_diff = np.mean(diffs)
        std_diff = np.std(diffs)
        if std_diff == 0:
            return False
        z = (diffs[-1] - mean_diff) / std_diff
        return abs(z) > 4.0
