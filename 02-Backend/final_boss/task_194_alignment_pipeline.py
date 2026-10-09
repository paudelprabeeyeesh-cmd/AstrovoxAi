import numpy as np


class AlignmentPipeline:
    def __init__(self):
        self.stages = ["pretrain", "sft", "rlhf", "constitutional_ai", "rlaif"]
        self.current_stage = 0
        self.losses = []

    def stage_loss(self, x, y, stage):
        w = np.random.randn(x.shape[1], 512)
        pred = x @ w
        loss = np.mean((pred - y) ** 2)
        self.losses.append((stage, loss))
        return loss

    def pretrain(self, x, y):
        return self.stage_loss(x, y, "pretrain")

    def sft(self, x, y):
        return self.stage_loss(x, y, "sft")

    def rlhf(self, x, y):
        return self.stage_loss(x, y, "rlhf")

    def constitutional_ai(self, x, y):
        return self.stage_loss(x, y, "constitutional_ai")

    def rlaif(self, x, y):
        return self.stage_loss(x, y, "rlaif")

    def run(self, x, y):
        self.pretrain(x, y)
        self.sft(x, y)
        self.rlhf(x, y)
        self.constitutional_ai(x, y)
        return self.rlaif(x, y)
