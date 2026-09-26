import logging
import torch
from ASTROVOX_AI.ai_core.foundation_moe import MoEModel, MoEConfig, MoETrainer

logger = logging.getLogger(__name__)


def run_synthetic_training():
    device = torch.device("cpu")
    model = MoEModel(MoEConfig(vocab_size=1000, hidden_size=128, num_layers=2, num_heads=2, num_experts=4, top_k=2, intermediate_size=512))
    trainer = MoETrainer(model, device=device)
    batch = {"input_ids": torch.randint(0, 1000, (2, 32)), "labels": torch.randint(0, 1000, (2, 32))}
    for step in range(10):
        result = trainer.train_step(batch)
        logger.info("MoE step %d loss=%.4f lb=%.4f", step + 1, result["loss"], result["load_balance_loss"])
    hidden = torch.randn(1, 1, 128)
    routes = model.route(hidden)
    logger.info("Expert indices: %s", routes["expert_indices"])
    return result


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print(run_synthetic_training())
