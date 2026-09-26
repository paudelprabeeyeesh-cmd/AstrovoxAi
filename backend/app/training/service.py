import logging
import uuid
from typing import Dict, Any
import torch

from ASTROVOX_AI.ai_core.foundation_gpt import GPTModel, GPTConfig, GPTTrainer
from ASTROVOX_AI.ai_core.foundation_vit import ViTModel, ViTConfig, ViTTrainer
from ASTROVOX_AI.ai_core.foundation_multimodal import MultimodalModel, MultimodalConfig, MultimodalTrainer
from ASTROVOX_AI.ai_core.foundation_audio import AudioLanguageModel, AudioLanguageConfig, AudioLanguageTrainer
from ASTROVOX_AI.ai_core.foundation_code import CodeModel, CodeModelConfig, CodeModelTrainer
from ASTROVOX_AI.ai_core.foundation_reasoning import ReasoningModel, ReasoningConfig, ReasoningTrainer
from ASTROVOX_AI.ai_core.foundation_math import MathModel, MathModelConfig, MathTrainer
from ASTROVOX_AI.ai_core.foundation_instruction import InstructionModel, InstructionConfig, InstructionTrainer
from ASTROVOX_AI.ai_core.foundation_multilingual import MultilingualModel, MultilingualConfig, MultilingualTrainer
from ASTROVOX_AI.ai_core.foundation_moe import MoEModel, MoEConfig, MoETrainer

logger = logging.getLogger(__name__)

MODEL_REGISTRY = {
    "gpt": (GPTModel, GPTConfig, GPTTrainer),
    "vit": (ViTModel, ViTConfig, ViTTrainer),
    "multimodal": (MultimodalModel, MultimodalConfig, MultimodalTrainer),
    "audio": (AudioLanguageModel, AudioLanguageConfig, AudioLanguageTrainer),
    "code": (CodeModel, CodeModelConfig, CodeModelTrainer),
    "reasoning": (ReasoningModel, ReasoningConfig, ReasoningTrainer),
    "math": (MathModel, MathModelConfig, MathTrainer),
    "instruction": (InstructionModel, InstructionConfig, InstructionTrainer),
    "multilingual": (MultilingualModel, MultilingualConfig, MultilingualTrainer),
    "moe": (MoEModel, MoEConfig, MoETrainer),
}


class TrainingJob:
    def __init__(self, model_type: str, dataset_path: str, epochs: int = 1, batch_size: int = 4, learning_rate: float = 1e-4, device: str = "cpu"):
        self.job_id = str(uuid.uuid4())
        self.model_type = model_type
        self.dataset_path = dataset_path
        self.epochs = epochs
        self.batch_size = batch_size
        self.learning_rate = learning_rate
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        self.status = "pending"
        self.epoch = 0
        self.loss = None
        self.model = None
        self.trainer = None

    def setup(self):
        if self.model_type not in MODEL_REGISTRY:
            raise ValueError(f"Unknown model type: {self.model_type}")
        model_cls, config_cls, trainer_cls = MODEL_REGISTRY[self.model_type]
        config = config_cls()
        self.model = model_cls(config)
        optimizer = torch.optim.AdamW(self.model.parameters(), lr=self.learning_rate)
        self.trainer = trainer_cls(self.model, optimizer=optimizer, device=torch.device(self.device))
        self.status = "ready"

    def step(self, batch):
        if self.trainer is None:
            self.setup()
        result = self.trainer.train_step(batch)
        self.loss = result.get("loss")
        return result

    def run_epoch(self, dataloader):
        if self.trainer is None:
            self.setup()
        result = self.trainer.train_epoch(dataloader)
        self.epoch += 1
        self.loss = result.get("loss")
        self.status = "running"
        return result

    def evaluate(self, dataloader):
        if self.trainer is None:
            self.setup()
        result = self.trainer.evaluate(dataloader)
        return result

    def save(self, path: str):
        if self.trainer is None:
            raise RuntimeError("Trainer not initialized")
        self.trainer.save_checkpoint(path)


training_jobs: Dict[str, TrainingJob] = {}


class TrainingService:
    def create_job(self, model_type: str, dataset_path: str, epochs: int = 1, batch_size: int = 4, learning_rate: float = 1e-4, device: str = "cpu"):
        job = TrainingJob(model_type, dataset_path, epochs, batch_size, learning_rate, device)
        training_jobs[job.job_id] = job
        return job

    def get_job(self, job_id: str):
        return training_jobs.get(job_id)

    def list_jobs(self):
        return list(training_jobs.values())
