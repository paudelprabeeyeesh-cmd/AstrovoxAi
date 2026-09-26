from typing import Callable
import torch
import torch.nn as nn


class GradientCheckpointing:
    @staticmethod
    def checkpoint(fn: Callable, *args, **kwargs) -> torch.Tensor:
        return torch.utils.checkpoint.checkpoint(fn, *args, use_reentrant=False, **kwargs)

    @staticmethod
    def enable(model: nn.Module) -> nn.Module:
        for name, module in model.named_modules():
            if hasattr(module, 'forward'):
                original_forward = module.forward
                def make_forward(orig, mod_name):
                    def forward_with_checkpoint(*args, **kwargs):
                        return GradientCheckpointing.checkpoint(orig, *args, **kwargs)
                    return forward_with_checkpoint
                module.forward = make_forward(original_forward, name)
        return model

    @staticmethod
    def apply_to_transformer_block(model: nn.Module) -> nn.Module:
        for name, module in model.named_modules():
            if 'block' in name.lower() or 'layer' in name.lower():
                if hasattr(module, 'forward'):
                    original_forward = module.forward
                    def make_forward(orig):
                        def forward_with_checkpoint(x, mask=None):
                            return GradientCheckpointing.checkpoint(orig, x, mask)
                        return forward_with_checkpoint
                    module.forward = make_forward(original_forward)
        return model
