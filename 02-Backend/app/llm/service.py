import os
import logging
import time
from typing import Optional, Dict, Any, List

from fastapi import HTTPException

logger = logging.getLogger(__name__)


class LocalLLMService:
    def __init__(self, config_path: str = "models/llm/configs/config_4b.yaml"):
        self.config_path = config_path
        self._model = None
        self._tokenizer = None
        self._device = "cpu"
        self._load_model()

    def _load_model(self):
        try:
            import torch
            from models.llm.model.model import LLM
            from models.llm.tokenizer.train_tokenizer import load_tokenizer
            from models.llm.utils.helpers import load_config, get_device, set_cpu_threads

            self._device = get_device()
            if self._device == "cpu":
                set_cpu_threads(min(4, os.cpu_count() or 2))

            self._config = load_config(self.config_path)
            dtype = torch.bfloat16 if self._config.get("mixed_precision") == "bf16" else torch.float32
            self._model = LLM(self._config, device=torch.device(self._device), dtype=dtype)
            self._model.eval()

            tokenizer_path = self._config.get("tokenizer_path", "models/llm/tokenizer.json")
            if os.path.exists(tokenizer_path):
                self._tokenizer = load_tokenizer(tokenizer_path)
            else:
                logger.warning(f"Tokenizer not found at {tokenizer_path}")
        except Exception as exc:
            logger.error(f"Failed to load local LLM: {exc}")
            self._model = None
            self._tokenizer = None

    def _generate(self, prompt: str, max_new_tokens: int = 200, temperature: float = 0.7, top_k: Optional[int] = None) -> str:
        if self._model is None or self._tokenizer is None:
            raise RuntimeError("Local LLM not loaded")
        import torch
        from models.llm.inference.generate import generate
        return generate(self._model, self._tokenizer, prompt, max_new_tokens=max_new_tokens, temperature=temperature, top_k=top_k, device=self._device)

    def call_llm(self, prompt: str, system: str = "", messages: Optional[List[dict]] = None, **kwargs) -> Dict[str, Any]:
        start = time.time()
        text = self._generate(prompt, max_new_tokens=kwargs.get("max_new_tokens", 200), temperature=kwargs.get("temperature", 0.7))
        latency_ms = (time.time() - start) * 1000
        tokens = len(text.split())
        return {
            "text": text,
            "provider": "local",
            "model": os.path.basename(self.config_path).replace(".yaml", ""),
            "tokens": tokens,
            "latency_ms": latency_ms,
            "confidence": 0.8,
        }

    async def stream_llm(self, prompt: str, system: str = "", messages: Optional[List[dict]] = None, **kwargs):
        result = self.call_llm(prompt, system=system, messages=messages, **kwargs)
        words = result["text"].split()
        for word in words:
            yield {"token": word + " ", "provider": "local", "model": result["model"]}
