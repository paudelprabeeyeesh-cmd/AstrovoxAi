from typing import Optional, List, Dict
import sentencepiece as spm


class SentencePieceTokenizer:
    def __init__(self, model_path: Optional[str] = None):
        self.sp = spm.SentencePieceProcessor()
        self.model_path = model_path
        if model_path:
            self.sp.load(model_path)

    def train(self, input_file: str, model_prefix: str, vocab_size: int = 32000, character_coverage: float = 0.9995, model_type: str = 'bpe') -> None:
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
        self.model_path = f'{model_prefix}.model'
        self.sp.load(self.model_path)

    def encode(self, text: str) -> List[int]:
        return self.sp.encode(text, out_type=int)

    def decode(self, ids: List[int]) -> str:
        return self.sp.decode(ids)

    def encode_as_pieces(self, text: str) -> List[str]:
        return self.sp.encode(text, out_type=str)

    def get_piece_size(self) -> int:
        return self.sp.get_piece_size()

    def pad_id(self) -> int:
        return self.sp.pad_id()

    def unk_id(self) -> int:
        return self.sp.unk_id()

    def bos_id(self) -> int:
        return self.sp.bos_id()

    def eos_id(self) -> int:
        return self.sp.eos_id()
