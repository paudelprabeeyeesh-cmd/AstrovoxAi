import logging
from dataclasses import dataclass
from typing import List
import torch

logger = logging.getLogger(__name__)


@dataclass
class TokenizerReport:
    name: str
    num_tokens: int
    unique_tokens: int
    compression_ratio: float
    avg_token_length: float


class TokenizerComparator:
    def __init__(self, text: str):
        self.text = text

    def _simple_word_tokenize(self, text: str) -> List[str]:
        return text.split()

    def _simple_char_tokenize(self, text: str) -> List[str]:
        return list(text)

    def compare(self) -> List[TokenizerReport]:
        words = self._simple_word_tokenize(self.text)
        chars = self._simple_char_tokenize(self.text)
        byte_len = len(self.text.encode("utf-8"))
        reports = [
            TokenizerReport(
                name="word",
                num_tokens=len(words),
                unique_tokens=len(set(words)),
                compression_ratio=len(words) / byte_len if byte_len else 0.0,
                avg_token_length=sum(len(w) for w in words) / len(words) if words else 0.0,
            ),
            TokenizerReport(
                name="char",
                num_tokens=len(chars),
                unique_tokens=len(set(chars)),
                compression_ratio=len(chars) / byte_len if byte_len else 0.0,
                avg_token_length=1.0,
            ),
        ]
        logger.info("Tokenizer comparison:")
        for report in reports:
            logger.info(
                "%s: tokens=%d unique=%d compression=%.4f avg_len=%.2f",
                report.name,
                report.num_tokens,
                report.unique_tokens,
                report.compression_ratio,
                report.avg_token_length,
            )
        return reports


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    TokenizerComparator("Hello world. This is a tokenizer comparison test.").compare()
