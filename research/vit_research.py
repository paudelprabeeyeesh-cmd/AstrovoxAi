import logging
import torch
from ASTROVOX_AI.ai_core.foundation_vit import ViTModel, ViTConfig, ViTTrainer

logger = logging.getLogger(__name__)


def run_synthetic_training():
    device = torch.device("cpu")
    model = ViTModel(ViTConfig(image_size=64, patch_size=8, num_classes=10, hidden_size=128, num_layers=2, num_heads=2, mlp_ratio=4.0))
    trainer = ViTTrainer(model, device=device)
    batch = {"pixels": torch.randn(2, 3, 64, 64), "labels": torch.randint(0, 10, (2,))}
    for step in range(10):
        result = trainer.train_step(batch)
        logger.info("ViT step %d loss=%.4f", step + 1, result["loss"])
    return trainer.evaluate([batch])


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print(run_synthetic_training())
