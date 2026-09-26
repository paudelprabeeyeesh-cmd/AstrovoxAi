import logging
import torch
from ASTROVOX_AI.ai_core.foundation_instruction import InstructionModel, InstructionConfig, InstructionTrainer, InstructionTuner

logger = logging.getLogger(__name__)


def run_synthetic_training():
    device = torch.device("cpu")
    model = InstructionModel(InstructionConfig(vocab_size=1000, hidden_size=128, num_layers=2, num_heads=2, intermediate_size=512, max_position_embeddings=256))
    trainer = InstructionTrainer(model, device=device)
    tuner = InstructionTuner(model)
    prompt, response = tuner.format_example("Translate to French", "Hello", "Bonjour")
    logger.info("Formatted prompt: %s", prompt)
    batch = {"input_ids": torch.randint(0, 1000, (2, 32)), "labels": torch.randint(0, 1000, (2, 32))}
    for step in range(10):
        result = trainer.train_step(batch)
        logger.info("Instruction step %d loss=%.4f", step + 1, result["loss"])
    return {"train_loss": result["loss"], "formatted_prompt": prompt}


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print(run_synthetic_training())
