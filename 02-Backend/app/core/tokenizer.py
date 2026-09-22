from collections import Counter
import json
from typing import Dict, List, Tuple


class BPETokenizer:
    SPECIAL_TOKENS = {
        "<|BOS|>": 256,
        "<|EOS|>": 257,
        "<|PAD|>": 258,
        "<|UNK|>": 259,
    }

    def __init__(self):
        self.vocab: Dict[int, bytes] = {}
        self.merges: Dict[Tuple[int, int], int] = {}
        self.vocab_size: int = 0
        self.special_token_ids = {v: k for k, v in self.SPECIAL_TOKENS.items()}

    def train_bpe(self, corpus: str, vocab_size: int):
        if vocab_size < 260:
            raise ValueError("vocab_size must be at least 260 (256 bytes + 4 special tokens)")

        text_bytes = corpus.encode("utf-8")
        self.vocab = {i: bytes([i]) for i in range(256)}
        for token, id_ in self.SPECIAL_TOKENS.items():
            self.vocab[id_] = token.encode("utf-8")

        symbols = list(text_bytes)
        self.merges = {}

        pair_counts = Counter()
        for i in range(len(symbols) - 1):
            pair = (symbols[i], symbols[i + 1])
            pair_counts[pair] += 1

        next_id = 260
        while next_id < vocab_size:
            if not pair_counts:
                break

            best_pair = max(pair_counts, key=pair_counts.get)
            self.merges[best_pair] = next_id
            self.vocab[next_id] = self.vocab[best_pair[0]] + self.vocab[best_pair[1]]

            i = 0
            new_symbols = []
            while i < len(symbols):
                if (
                    i < len(symbols) - 1
                    and symbols[i] == best_pair[0]
                    and symbols[i + 1] == best_pair[1]
                ):
                    new_symbols.append(next_id)
                    i += 2
                else:
                    new_symbols.append(symbols[i])
                    i += 1
            symbols = new_symbols

            pair_counts = Counter()
            for i in range(len(symbols) - 1):
                pair = (symbols[i], symbols[i + 1])
                pair_counts[pair] += 1

            next_id += 1

        self.vocab_size = len(self.vocab)

    def encode(self, text: str, add_bos: bool = False, add_eos: bool = False) -> List[int]:
        if not text:
            ids = []
            if add_bos:
                ids.append(self.SPECIAL_TOKENS["<|BOS|>"])
            if add_eos:
                ids.append(self.SPECIAL_TOKENS["<|EOS|>"])
            return ids

        symbols = list(text.encode("utf-8"))
        changed = True
        while changed:
            changed = False
            best_pair = None
            best_priority = float("inf")

            for i in range(len(symbols) - 1):
                pair = (symbols[i], symbols[i + 1])
                if pair in self.merges:
                    priority = self.merges[pair]
                    if priority < best_priority:
                        best_priority = priority
                        best_pair = pair

            if best_pair is None:
                break

            changed = True
            i = 0
            new_symbols = []
            while i < len(symbols):
                if (
                    i < len(symbols) - 1
                    and symbols[i] == best_pair[0]
                    and symbols[i + 1] == best_pair[1]
                ):
                    new_symbols.append(self.merges[best_pair])
                    i += 2
                else:
                    new_symbols.append(symbols[i])
                    i += 1
            symbols = new_symbols

        ids = []
        for s in symbols:
            ids.append(s if s in self.vocab else self.SPECIAL_TOKENS["<|UNK|>"])

        if add_bos:
            ids = [self.SPECIAL_TOKENS["<|BOS|>"]] + ids
        if add_eos:
            ids = ids + [self.SPECIAL_TOKENS["<|EOS|>"]]

        return ids

    def decode(self, ids: List[int]) -> str:
        byte_chunks = []
        for id_ in ids:
            if id_ in self.vocab:
                byte_chunks.append(self.vocab[id_])
            else:
                byte_chunks.append(self.SPECIAL_TOKENS["<|UNK|>"].encode("utf-8"))
        return b"".join(byte_chunks).decode("utf-8", errors="replace")

    def get_vocab_size(self) -> int:
        return self.vocab_size

    def save(self, path: str):
        data = {
            "vocab": {str(k): v.hex() for k, v in self.vocab.items()},
            "merges": {f"{k[0]},{k[1]}": v for k, v in self.merges.items()},
            "vocab_size": self.vocab_size,
            "special_tokens": self.SPECIAL_TOKENS,
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def load(self, path: str):
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.vocab = {int(k): bytes.fromhex(v) for k, v in data["vocab"].items()}
        self.merges = {
            tuple(map(int, k.split(","))): v for k, v in data["merges"].items()
        }
        self.vocab_size = data["vocab_size"]
        self.SPECIAL_TOKENS = data["special_tokens"]
        self.special_token_ids = {v: k for k, v in self.SPECIAL_TOKENS.items()}
