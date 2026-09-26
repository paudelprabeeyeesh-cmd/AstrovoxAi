import logging
import torch
from ASTROVOX_AI.ai_core.foundation_multilingual import MultilingualModel, MultilingualConfig, MultilingualTrainer

logger = logging.getLogger(__name__)


def run_synthetic_training():
    device = torch.device("cpu")
    model = MultilingualModel(MultilingualConfig(vocab_size=5000, hidden_size=128, num_layers=2, num_heads=2, num_languages=10))
    trainer = MultilingualTrainer(model, device=device)
    batch = {"input_ids": torch.randint(0, 5000, (2, 32)), "language_id": torch.randint(0, 10, (2,)), "labels": torch.randint(0, 5000, (2, 32))}
    for step in range(10):
        result = trainer.train_step(batch)
        logger.info("Multilingual step %d loss=%.4f", step + 1, result["loss"])
    translation = model.translate("Hello world", source_lang=0, target_lang=1)
    logger.info("Translation: %s", translation)
    return {"train_loss": result["loss"], "translation": translation}


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print(run_synthetic_training())
