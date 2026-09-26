"""SentencePiece tokenizer with training pipeline for ASTROVOX_AI."""

from __future__ import annotations

import logging
import os
from typing import List, Optional

logger = logging.getLogger(__name__)


class SentencePieceTokenizer:
    def __init__(self, model_path: Optional[str] = None):
        self.model_path = model_path
        self._sp = None
        logger.info("SentencePiece tokenizer initialized")

    def _get_sp(self):
        if self._sp is not None:
            return self._sp
        try:
            import sentencepiece as spm

            self._sp = spm.SentencePieceProcessor()
            if self.model_path and os.path.exists(self.model_path):
                self._sp.load(self.model_path)
            return self._sp
        except ImportError:
            logger.warning("sentencepiece not installed")
            return None

    def train(self, input_file: str, model_prefix: str, vocab_size: int = 32000, character_coverage: float = 0.9995, model_type: str = "bpe") -> None:
        sp = self._get_sp()
        if sp is not None:
            import sentencepiece as spm

            spm.SentencePieceTrainer.train(
                input=input_file,
                model_prefix=model_prefix,
                vocab_size=vocab_size,
                character_coverage=character_coverage,
                model_type=model_type,
                pad_id=0,
                unk_id=1,
                bos_id=2,
                eos_id=3,
            )
            self.model_path = f"{model_prefix}.model"
            sp.load(self.model_path)
        else:
            logger.warning("SentencePiece not available; use BPETrainer instead")
            raise RuntimeError("sentencepiece is required for training")

    def encode(self, text: str) -> List[int]:
        sp = self._get_sp()
        if sp is None:
            raise RuntimeError("Model not loaded. Load a model first.")
        return sp.encode(text, out_type=int)

    def decode(self, ids: List[int]) -> str:
        sp = self._get_sp()
        if sp is None:
            raise RuntimeError("Model not loaded. Load a model first.")
        return sp.decode(ids)

    def encode_as_pieces(self, text: str) -> List[str]:
        sp = self._get_sp()
        if sp is None:
            raise RuntimeError("Model not loaded. Load a model first.")
        return sp.encode(text, out_type=str)

    def get_piece_size(self) -> int:
        sp = self._get_sp()
        return sp.get_piece_size() if sp is not None else 0

    def pad_id(self) -> int:
        sp = self._get_sp()
        return sp.pad_id() if sp is not None else 0

    def unk_id(self) -> int:
        sp = self._get_sp()
        return sp.unk_id() if sp is not None else 1

    def bos_id(self) -> int:
        sp = self._get_sp()
        return sp.bos_id() if sp is not None else 2

    def eos_id(self) -> int:
        sp = self._get_sp()
        return sp.eos_id() if sp is not None else 3

    def load(self, model_path: str) -> None:
        self.model_path = model_path
        sp = self._get_sp()
        if sp is not None:
            sp.load(model_path)
