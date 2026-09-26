import logging
import torch
from ASTROVOX_AI.ai_core.foundation_multimodal import MultimodalModel, MultimodalConfig, MultimodalTrainer

logger = logging.getLogger(__name__)


def run_synthetic_training():
    device = torch.device("cpu")
    model = MultimodalModel(MultimodalConfig(text_vocab_size=1000, image_dim=128, hidden_size=128, num_layers=2, num_heads=2, projection_dim=64))
    trainer = MultimodalTrainer(model, device=device)
    text_batch = {"input_ids": torch.randint(0, 1000, (2, 32))}
    image_batch = {"pixels": torch.randn(2, 3, 224, 224)}
    for step in range(10):
        result = trainer.contrastive_step(text_batch, image_batch)
        logger.info("Multimodal step %d loss=%.4f", step + 1, result["loss"])
    return result


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print(run_synthetic_training())
