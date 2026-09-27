"""LLM service wrapping the 100M parameter model."""

import os
import logging
from typing import Optional

import torch
import torch.nn as nn

from models.llm.inference import generate
from models.llm.utils.helpers import load_config, get_device

logger = logging.getLogger(__name__)


class LLMService:
    def __init__(self, config_path: str = "models/llm/configs/config_100m.yaml", checkpoint_path: Optional[str] = None):
        self.config_path = config_path
        self.checkpoint_path = checkpoint_path or os.path.join(os.path.dirname(config_path), "..", "model.pt")
        self.config = load_config(config_path)
        self.device = get_device()
        self.model = None
        self.tokenizer = None
        self._loaded = False

    def load(self) -> None:
        if self._loaded:
            return

        from models.llm.model import LLM
        from models.llm.tokenizer.train_tokenizer import load_tokenizer

        self.model = LLM(self.config)

        checkpoint_path = os.path.abspath(self.checkpoint_path)
        if os.path.exists(checkpoint_path):
            state_dict = torch.load(checkpoint_path, map_location="cpu", weights_only=True)
            self.model.load_state_dict(state_dict, strict=False)
            logger.info("Loaded checkpoint from %s", checkpoint_path)
        else:
            logger.warning("Checkpoint not found at %s", checkpoint_path)

        if self.device == "cuda":
            self.model = self.model.to(self.device)
            try:
                self._replace_linear_with_8bit(self.model)
                logger.info("8-bit quantization enabled via bitsandbytes")
            except ImportError:
                logger.info("bitsandbytes not available, using full precision on CUDA")
            except Exception as exc:
                logger.warning("8-bit quantization failed: %s", exc)
        else:
            try:
                self.model = torch.quantization.quantize_dynamic(self.model, {nn.Linear}, dtype=torch.qint8)
                logger.info("8-bit quantization enabled via torch.dynamic")
            except Exception as exc:
                logger.warning("8-bit quantization failed: %s", exc)

        self.model.eval()
        self.tokenizer = load_tokenizer(self.config.get("tokenizer_path", "tokenizer.json"))
        self._loaded = True

    def _replace_linear_with_8bit(self, module: nn.Module) -> None:
        import bitsandbytes as bnb

        for name, child in list(module.named_children()):
            if isinstance(child, nn.Linear):
                quantized = bnb.nn.Linear8bitLt(
                    child.in_features,
                    child.out_features,
                    has_bias=child.bias is not None,
                    threshold=6.0,
                )
                quantized.weight = child.weight
                if child.bias is not None:
                    quantized.bias = child.bias
                setattr(module, name, quantized)
            else:
                self._replace_linear_with_8bit(child)

    def generate(self, prompt: str, max_new_tokens: int = 200, temperature: float = 0.8, top_k: int = 50) -> str:
        if not self._loaded:
            self.load()
        return generate(self.model, self.tokenizer, prompt, max_new_tokens=max_new_tokens, temperature=temperature, top_k=top_k, device=self.device)

    def chat(self, message: str, max_new_tokens: int = 200, temperature: float = 0.8, top_k: int = 50) -> str:
        if not self._loaded:
            self.load()
        prompt = f"You: {message}\nAI:"
        return generate(self.model, self.tokenizer, prompt, max_new_tokens=max_new_tokens, temperature=temperature, top_k=top_k, device=self.device)


llm_service = LLMService()
