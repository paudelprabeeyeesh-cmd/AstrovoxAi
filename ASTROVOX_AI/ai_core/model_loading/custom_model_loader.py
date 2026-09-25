from typing import Dict, Optional, Any
import torch
import torch.nn as nn
import os


class CustomModelLoader:
    def __init__(self, device: str = 'cuda'):
        self.device = device

    def load_from_path(self, model_path: str, config: Optional[Dict[str, Any]] = None) -> nn.Module:
        if not os.path.exists(model_path):
            raise FileNotFoundError(f'Model path not found: {model_path}')
        if model_path.endswith('.pt') or model_path.endswith('.pth'):
            return self._load_torch(model_path, config)
        elif model_path.endswith('.bin'):
            return self._load_bin(model_path, config)
        else:
            raise ValueError(f'Unsupported model format: {model_path}')

    def _load_torch(self, path: str, config: Optional[Dict[str, Any]]) -> nn.Module:
        checkpoint = torch.load(path, map_location=self.device)
        model = checkpoint.get('model', checkpoint)
        if isinstance(model, dict) and 'state_dict' in model:
            model = self._build_model_from_config(config or {})
            model.load_state_dict(checkpoint['state_dict'])
        return model

    def _load_bin(self, path: str, config: Optional[Dict[str, Any]]) -> nn.Module:
        state_dict = torch.load(path, map_location=self.device)
        model = self._build_model_from_config(config or {})
        model.load_state_dict(state_dict, strict=False)
        return model

    def _build_model_from_config(self, config: Dict[str, Any]) -> nn.Module:
        from ASTROVOX_AI.ai_core.transformers.transformer_from_scratch import TransformerFromScratch, TransformerConfig
        cfg = TransformerConfig(**config)
        return TransformerFromScratch(cfg)

    def save(self, model: nn.Module, path: str) -> None:
        torch.save({'model': model}, path)
