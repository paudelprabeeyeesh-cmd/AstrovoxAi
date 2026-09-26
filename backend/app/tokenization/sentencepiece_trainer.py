"""SentencePiece trainer with pure-Python fallback."""

from __future__ import annotations

import logging
import os
from typing import List, Optional

logger = logging.getLogger(__name__)


class SentencePieceTrainer:
    def __init__(self, model_path: Optional[str] = None):
        self.model_path = model_path
        self._sp = None
        logger.info("SentencePiece trainer initialized")

    def _load_sentencepiece(self):
        if self._sp is not None:
            return self._sp
        try:
            import sentencepiece as spm

            self._sp = spm.SentencePieceProcessor()
            if self.model_path and os.path.exists(self.model_path):
                self._sp.load(self.model_path)
            return self._sp
        except ImportError:
            logger.warning("sentencepiece not installed; using fallback tokenizer")
            return None

    def train(self, input_file: str, model_prefix: str, vocab_size: int = 32000, character_coverage: float = 0.9995, model_type: str = "bpe") -> str:
        sp = self._load_sentencepiece()
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
            logger.info("SentencePiece model trained at %s", self.model_path)
            return self.model_path
        else:
            logger.info("Using fallback BPE trainer for %s", model_prefix)
            from .bpe_trainer import BPETrainer, BPETrainerConfig

            texts: List[str] = []
            with open(input_file, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        texts.append(line)
            trainer = BPETrainer(BPETrainerConfig(vocab_size=vocab_size))
            trainer.train(texts)
            self.model_path = f"{model_prefix}.json"
            trainer.save(self.model_path)
            self._trainer = trainer
            logger.info("Fallback BPE model saved to %s", self.model_path)
            return self.model_path

    def load(self, model_path: str) -> None:
        self.model_path = model_path
        sp = self._load_sentencepiece()
        if sp is not None:
            sp.load(model_path)
            logger.info("Loaded SentencePiece model from %s", model_path)
        else:
            from .bpe_trainer import BPETrainer

            trainer = BPETrainer()
            trainer.load(model_path)
            self._trainer = trainer
            logger.info("Loaded fallback BPE model from %s", model_path)

    def encode(self, text: str) -> List[int]:
        sp = self._load_sentencepiece()
        if sp is not None:
            return sp.encode(text, out_type=int)
        trainer = getattr(self, "_trainer", None)
        if trainer is None:
            raise RuntimeError("Model not loaded. Call train() or load() first.")
        return trainer.encode(text)

    def decode(self, ids: List[int]) -> str:
        sp = self._load_sentencepiece()
        if sp is not None:
            return sp.decode(ids)
        trainer = getattr(self, "_trainer", None)
        if trainer is None:
            raise RuntimeError("Model not loaded. Call train() or load() first.")
        return trainer.decode(ids)

    def encode_as_pieces(self, text: str) -> List[str]:
        sp = self._load_sentencepiece()
        if sp is not None:
            return sp.encode(text, out_type=str)
        trainer = getattr(self, "_trainer", None)
        if trainer is None:
            raise RuntimeError("Model not loaded. Call train() or load() first.")
        ids = trainer.encode(text)
        return [trainer.inverse_vocab.get(i, "<unk>") for i in ids]

    def get_piece_size(self) -> int:
        sp = self._load_sentencepiece()
        if sp is not None:
            return sp.get_piece_size()
        trainer = getattr(self, "_trainer", None)
        if trainer is None:
            return 0
        return trainer.vocab_size

    def pad_id(self) -> int:
        sp = self._load_sentencepiece()
        return sp.pad_id() if sp is not None else 0

    def unk_id(self) -> int:
        sp = self._load_sentencepiece()
        return sp.unk_id() if sp is not None else 1

    def bos_id(self) -> int:
        sp = self._load_sentencepiece()
        return sp.bos_id() if sp is not None else 2

    def eos_id(self) -> int:
        sp = self._load_sentencepiece()
        return sp.eos_id() if sp is not None else 3
