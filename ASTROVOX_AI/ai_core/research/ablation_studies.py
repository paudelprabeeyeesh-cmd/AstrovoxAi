import logging
from typing import Dict, List, Optional
from dataclasses import dataclass
import torch
import torch.nn as nn

logger = logging.getLogger(__name__)


@dataclass
class AblationConfig:
    name: str
    use_attention: bool = True
    use_feedforward: bool = True
    use_norm: bool = True
    num_layers: int = 2


@dataclass
class AblationResult:
    config: AblationConfig
    loss: float
    params: int


class AblationStudy:
    def __init__(self, input_dim: int = 64, hidden_size: int = 128, seq_len: int = 32, vocab_size: int = 100):
        self.input_dim = input_dim
        self.hidden_size = hidden_size
        self.seq_len = seq_len
        self.vocab_size = vocab_size

    def _build_model(self, config: AblationConfig) -> nn.Module:
        layers: List[nn.Module] = []
        for _ in range(max(1, config.num_layers)):
            if config.use_norm:
                layers.append(nn.LayerNorm(self.hidden_size))
            if config.use_attention:
                layers.append(nn.MultiheadAttention(self.hidden_size, 4, batch_first=True))
            if config.use_feedforward:
                layers.append(nn.Sequential(nn.Linear(self.hidden_size, self.hidden_size * 4), nn.GELU(), nn.Linear(self.hidden_size * 4, self.hidden_size)))
        return nn.Sequential(nn.Linear(self.input_dim, self.hidden_size), *layers, nn.Linear(self.hidden_size, self.vocab_size))

    def _count_params(self, model: nn.Module) -> int:
        return sum(p.numel() for p in model.parameters() if p.requires_grad)

    def _estimate_loss(self, model: nn.Module, x: torch.Tensor) -> float:
        with torch.no_grad():
            out = model(x)
            target = torch.zeros(x.size(0), x.size(1), dtype=torch.long, device=x.device)
            loss = nn.functional.cross_entropy(out.transpose(1, 2), target)
        return loss.item()

    def run(self, configs: Optional[List[AblationConfig]] = None) -> List[AblationResult]:
        if configs is None:
            configs = [
                AblationConfig("full"),
                AblationConfig("no_ffn", use_feedforward=False),
                AblationConfig("no_attn", use_attention=False),
                AblationConfig("no_norm", use_norm=False),
                AblationConfig("shallow", num_layers=1),
            ]
        x = torch.randn(2, self.seq_len, self.input_dim)
        results = []
        for config in configs:
            model = self._build_model(config)
            params = self._count_params(model)
            loss = self._estimate_loss(model, x)
            results.append(AblationResult(config=config, loss=loss, params=params))
            logger.info(
                "Ablation %s: params=%d loss=%.4f",
                config.name,
                params,
                loss,
            )
        return results


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    AblationStudy().run()
