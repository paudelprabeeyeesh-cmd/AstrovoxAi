from typing import Optional, Dict, Any, List, Tuple, Callable
import torch
import torch.nn as nn
import logging

logger = logging.getLogger(__name__)


class ActivationPatcher:
    def __init__(self, model: nn.Module):
        self.model = model
        self.hooks = []
        self._original_state: Dict[str, Any] = {}

    def _get_activation(self, name: str):
        def hook(module, input, output):
            self._original_state[name] = output.clone() if isinstance(output, torch.Tensor) else output
        return hook

    def register_hook(self, layer_name: str) -> None:
        for name, module in self.model.named_modules():
            if name == layer_name:
                hook = module.register_forward_hook(self._get_activation(name))
                self.hooks.append(hook)
                break

    def apply_patch(self, layer_name: str, patch_fn: Callable[[torch.Tensor], torch.Tensor]) -> None:
        def hook(module, input, output):
            return patch_fn(output)
        for name, module in self.model.named_modules():
            if name == layer_name:
                self.hooks.append(module.register_forward_hook(hook))
                break

    def remove_hooks(self) -> None:
        for hook in self.hooks:
            hook.remove()
        self.hooks = []

    def patch_forward(self, inputs: torch.Tensor, layer_name: str, patch_fn: Callable[[torch.Tensor], torch.Tensor], attention_mask: Optional[torch.Tensor] = None) -> torch.Tensor:
        self.apply_patch(layer_name, patch_fn)
        with torch.no_grad():
            if attention_mask is not None:
                outputs = self.model(inputs, attention_mask=attention_mask)
            else:
                outputs = self.model(inputs)
        self.remove_hooks()
        return outputs.logits if hasattr(outputs, "logits") else outputs

    def restore_forward(self, inputs: torch.Tensor, layer_name: str, attention_mask: Optional[torch.Tensor] = None) -> torch.Tensor:
        original = self._original_state.get(layer_name)
        if original is None:
            logger.warning("No original activation stored for %s", layer_name)
            return self._forward_default(inputs, attention_mask)
        patch_fn = lambda output: original.to(output.device)
        return self.patch_forward(inputs, layer_name, patch_fn, attention_mask)

    def _forward_default(self, inputs: torch.Tensor, attention_mask: Optional[torch.Tensor] = None) -> torch.Tensor:
        with torch.no_grad():
            if attention_mask is not None:
                outputs = self.model(inputs, attention_mask=attention_mask)
            else:
                outputs = self.model(inputs)
        return outputs.logits if hasattr(outputs, "logits") else outputs
