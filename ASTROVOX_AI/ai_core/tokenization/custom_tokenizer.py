from typing import List, Dict, Optional, Tuple
import re


class CustomTokenizer:
    def __init__(self, vocab: Optional[Dict[str, int]] = None, merges: Optional[List[Tuple[str, str]]] = None):
        self.vocab = vocab or {}
        self.merges = merges or []
        self.inverse_vocab = {v: k for k, v in self.vocab.items()}
        self.pattern = re.compile(r"""'s|'t|'re|'ve|'m|'ll|'d| ?\p{L}+| ?\p{N}+| ?[^\s\p{L}\p{N}]+|\s+(?!\S)|\s+""", re.UNICODE)

    def encode(self, text: str) -> List[int]:
        tokens = self.pattern.findall(text)
        ids = []
        for token in tokens:
            if token in self.vocab:
                ids.append(self.vocab[token])
            else:
                ids.extend([self.vocab.get(ch, self.vocab.get('<unk>', 0)) for ch in token])
        return ids

    def decode(self, ids: List[int]) -> str:
        return ''.join([self.inverse_vocab.get(i, '') for i in ids])

    def save(self, path: str) -> None:
        import json
        with open(path, 'w', encoding='utf-8') as f:
            json.dump({'vocab': self.vocab, 'merges': self.merges}, f, ensure_ascii=False, indent=2)

    def load(self, path: str) -> None:
        import json
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            self.vocab = data['vocab']
            self.merges = data['merges']
            self.inverse_vocab = {v: k for k, v in self.vocab.items()}
