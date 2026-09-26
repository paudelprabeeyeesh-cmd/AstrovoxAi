import logging
import torch
from ASTROVOX_AI.ai_core.foundation_audio import AudioLanguageModel, AudioLanguageConfig, AudioLanguageTrainer

logger = logging.getLogger(__name__)


def run_synthetic_training():
    device = torch.device("cpu")
    model = AudioLanguageModel(AudioLanguageConfig(vocab_size=1000, audio_dim=64, hidden_size=128, num_layers=2, num_heads=2))
    trainer = AudioLanguageTrainer(model, device=device)
    audio_batch = {"audio": torch.randn(2, 1, 128)}
    text_batch = {"input_ids": torch.randint(0, 1000, (2, 32)), "labels": torch.randint(0, 1000, (2, 32))}
    for step in range(10):
        result = trainer.train_step(audio_batch, text_batch)
        logger.info("Audio step %d loss=%.4f", step + 1, result["loss"])
    return result


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print(run_synthetic_training())
