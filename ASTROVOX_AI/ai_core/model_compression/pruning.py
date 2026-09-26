import torch
import torch.nn as nn
import logging

logger = logging.getLogger(__name__)


class MagnitudePruner:
    def __init__(self, amount: float = 0.3):
        self.amount = amount

    def prune(self, model: nn.Module) -> nn.Module:
        for name, module in model.named_modules():
            if isinstance(module, nn.Linear):
                weight = module.weight.data
                threshold = torch.quantile(weight.abs(), self.amount)
                mask = (weight.abs() > threshold).float()
                module.weight.data *= mask
                logger.info("Pruned %s: %d/%d weights retained", name, int(mask.sum()), mask.numel())
        return model


class StructuredPruner:
    def __init__(self, amount: float = 0.3):
        self.amount = amount

    def prune(self, model: nn.Module) -> nn.Module:
        for name, module in model.named_modules():
            if isinstance(module, nn.Linear):
                importance = module.weight.data.abs().sum(dim=1)
                num_keep = max(1, int(module.out_features * (1 - self.amount)))
                _, indices = torch.topk(importance, num_keep)
                module.weight.data = module.weight.data[indices]
                if module.bias is not None:
                    module.bias.data = module.bias.data[indices]
                module.out_features = num_keep
                logger.info("Structured pruned %s to %d features", name, num_keep)
        return model


class ChannelPruner:
    def __init__(self, amount: float = 0.3):
        self.amount = amount

    def prune(self, model: nn.Module) -> nn.Module:
        for name, module in model.named_modules():
            if isinstance(module, nn.Conv2d):
                importance = module.weight.data.abs().sum(dim=(0, 2, 3))
                num_keep = max(1, int(module.out_channels * (1 - self.amount)))
                _, indices = torch.topk(importance, num_keep)
                module.weight.data = module.weight.data[indices]
                if module.bias is not None:
                    module.bias.data = module.bias.data[indices]
                module.out_channels = num_keep
                logger.info("Channel pruned %s to %d channels", name, num_keep)
        return model
