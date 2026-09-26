import torch
import torch.nn as nn
import logging

logger = logging.getLogger(__name__)


class LowRankDecomposer:
    def __init__(self, rank: int = 16):
        self.rank = rank

    def decompose(self, weight: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
        u, s, v = torch.linalg.svd(weight.float(), full_matrices=False)
        u_r = u[:, :self.rank]
        s_r = s[:self.rank]
        v_r = v[:self.rank, :]
        a = u_r @ torch.diag(s_r)
        b = v_r
        logger.info("Decomposed weight %s to rank %d", weight.shape, self.rank)
        return a, b

    def reconstruct(self, a: torch.Tensor, b: torch.Tensor) -> torch.Tensor:
        return a @ b

    def compress_model(self, model: nn.Module) -> nn.Module:
        for name, module in model.named_modules():
            if isinstance(module, nn.Linear):
                a, b = self.decompose(module.weight.data)
                module.weight.data = self.reconstruct(a, b)
                logger.info("Low-rank compressed %s", name)
        return model
