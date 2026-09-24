import numpy as np
from .task_189_training_run import TrainingRun
from .task_190_loss_spike_recovery import LossSpikeRecovery
from .task_191_checkpoint_consistency import AsyncCheckpoint
from .task_192_straggler_handling import StragglerHandler
from .task_193_silent_data_corruption import SilentDataCorruptionDetector
from .task_194_alignment_pipeline import AlignmentPipeline
from .task_195_inference_stack import InferenceStack
from .task_196_agentic_stack import AgenticStack
from .task_197_product_stack import ProductStack
from .task_198_safety_stack import SafetyStack
from .task_199_interpretability_stack import InterpretabilityStack


class CompleteAISystem:
    def __init__(self):
        self.training = TrainingRun()
        self.recovery = LossSpikeRecovery()
        self.checkpoint = AsyncCheckpoint()
        self.straggler = StragglerHandler()
        self.corruption = SilentDataCorruptionDetector()
        self.alignment = AlignmentPipeline()
        self.inference = InferenceStack()
        self.agentic = AgenticStack()
        self.product = ProductStack()
        self.safety = SafetyStack()
        self.interpretability = InterpretabilityStack()

    def train_step(self, x, y):
        loss = self.training.train_step(x, y)
        self.checkpoint.async_save(self.training.checkpoint())
        return loss

    def infer(self, x):
        x = self.safety.forward(x)
        return self.inference.forward(x)

    def agent_step(self, x):
        return self.agentic.forward(x)

    def interpret(self, x):
        return self.interpretability.forward(x)

    def align(self, x, y):
        return self.alignment.run(x, y)
