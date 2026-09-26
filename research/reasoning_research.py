import logging
import torch
from ASTROVOX_AI.ai_core.foundation_reasoning import ReasoningModel, ReasoningConfig, ReasoningTrainer

logger = logging.getLogger(__name__)


def run_synthetic_training():
    device = torch.device("cpu")
    model = ReasoningModel(ReasoningConfig(vocab_size=1000, hidden_size=128, num_layers=2, num_heads=2, intermediate_size=512, max_position_embeddings=128))
    trainer = ReasoningTrainer(model, device=device)
    batch = {
        "input_ids": torch.randint(0, 1000, (2, 32)),
        "labels": torch.randint(0, 1000, (2, 32)),
        "reasoning_labels": torch.randint(0, 2, (2, 32)).float(),
    }
    for step in range(10):
        result = trainer.train_step(batch)
        logger.info("Reasoning step %d loss=%.4f", step + 1, result["loss"])
    prompt = torch.randint(0, 1000, (1, 8))
    cot = model.chain_of_thought(prompt)
    logger.info("Chain of thought steps: %d", len(cot["steps"]))
    return {"train_loss": result["loss"], "cot_steps": len(cot["steps"])}


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print(run_synthetic_training())
