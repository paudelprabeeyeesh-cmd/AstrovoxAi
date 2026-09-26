from typing import Dict, List
import torch
import torch.nn as nn
import logging

logger = logging.getLogger(__name__)


class SharedWeightManager:
    def __init__(self):
        self.shared: Dict[str, nn.Parameter] = {}
        self.bindings: Dict[str, str] = {}

    def register(self, name: str, parameter: nn.Parameter) -> None:
        self.shared[name] = parameter

    def bind(self, module_path: str, shared_name: str) -> None:
        self.bindings[module_path] = shared_name

    def apply(self, model: nn.Module) -> nn.Module:
        for path, shared_name in self.bindings.items():
            param = self.shared.get(shared_name)
            if param is None:
                continue
            parts = path.split('.')
            obj = model
            for part in parts[:-1]:
                obj = getattr(obj, part)
            setattr(obj, parts[-1], param)
            logger.info("Bound %s to shared parameter %s", path, shared_name)
        return model

    def tie_embeddings(self, model: nn.Module, embedding_attr: str = 'embed_tokens', lm_head_attr: str = 'lm_head') -> nn.Module:
        embedding = getattr(model, embedding_attr, None)
        lm_head = getattr(model, lm_head_attr, None)
        if embedding is not None and lm_head is not None:
            lm_head.weight = embedding.weight
            logger.info("Tied embeddings %s and %s", embedding_attr, lm_head_attr)
        return model
