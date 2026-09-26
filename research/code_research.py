import logging
import torch
from ASTROVOX_AI.ai_core.foundation_code import CodeModel, CodeModelConfig, CodeModelTrainer

logger = logging.getLogger(__name__)


def run_synthetic_training():
    device = torch.device("cpu")
    model = CodeModel(CodeModelConfig(vocab_size=1000, hidden_size=128, num_layers=2, num_heads=2, intermediate_size=512, max_position_embeddings=128))
    trainer = CodeModelTrainer(model, device=device)
    batch = {"input_ids": torch.randint(0, 1000, (2, 64)), "labels": torch.randint(0, 1000, (2, 64))}
    for step in range(10):
        result = trainer.train_step(batch)
        logger.info("Code step %d loss=%.4f", step + 1, result["loss"])
    return trainer.evaluate([batch])


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print(run_synthetic_training())
