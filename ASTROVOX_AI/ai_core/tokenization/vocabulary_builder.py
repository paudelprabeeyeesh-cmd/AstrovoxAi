from typing import List, Tuple, Dict, Optional
from collections import Counter
import re


class VocabularyBuilder:
    def __init__(self, vocab_size: int = 50257, min_frequency: int = 2, special_tokens: Optional[List[str]] = None):
        self.vocab_size = vocab_size
        self.min_frequency = min_frequency
        self.special_tokens = special_tokens or ['<unk>', '<pad>', '<s>', '</s>', '<mask>']
        self.vocab: Dict[str, int] = {}
        self.inverse_vocab: Dict[int, str] = {}
        self.merges: List[Tuple[str, str]] = []

    def build(self, corpus: List[str]) -> Dict[str, int]:
        words = [list(word) for text in corpus for word in text.split()]
        self.vocab = {token: idx for idx, token in enumerate(self.special_tokens)}
        idx = len(self.vocab)
        unique_chars = sorted({char for word in words for char in word})
        for char in unique_chars:
            if char not in self.vocab:
                self.vocab[char] = idx
                idx += 1
        for _ in range(self.vocab_size - len(self.vocab)):
            pairs = self._get_pair_counts(words)
            if not pairs:
                break
            best = max(pairs, key=pairs.get)
            self.merges.append(best)
            words = self._merge_vocab(best, words)
            merged_token = ''.join(best)
            if merged_token not in self.vocab:
                self.vocab[merged_token] = idx
                idx += 1
        self.inverse_vocab = {v: k for k, v in self.vocab.items()}
        return self.vocab

    def encode(self, text: str) -> List[int]:
        tokens = self._tokenize(text)
        return [self.vocab.get(token, self.vocab.get('<unk>', 0)) for token in tokens]

    def decode(self, ids: List[int]) -> str:
        return ''.join([self.inverse_vocab.get(i, '') for i in ids])

    def save(self, path: str) -> None:
        import json
        with open(path, 'w', encoding='utf-8') as f:
            json.dump({'vocab': self.vocab, 'merges': self.merges, 'inverse_vocab': self.inverse_vocab}, f, ensure_ascii=False, indent=2)

    def load(self, path: str) -> None:
        import json
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            self.vocab = data['vocab']
            self.merges = data.get('merges', [])
            self.inverse_vocab = data.get('inverse_vocab', {v: k for k, v in self.vocab.items()})

    def _get_pair_counts(self, words: List[List[str]]) -> Counter:
        pairs = Counter()
        for word in words:
            for i in range(len(word) - 1):
                pairs[(word[i], word[i + 1])] += 1
        return pairs

    def _merge_vocab(self, pair: Tuple[str, str], words: List[List[str]]) -> List[List[str]]:
        bigram = ' '.join(pair)
        replacement = ''.join(pair)
        v_out = []
        for word in words:
            new_word = []
            i = 0
            while i < len(word):
                if i < len(word) - 1 and word[i] == pair[0] and word[i + 1] == pair[1]:
                    new_word.append(replacement)
                    i += 2
                else:
                    new_word.append(word[i])
                    i += 1
            v_out.append(new_word)
        return v_out

    def _tokenize(self, text: str) -> List[str]:
        tokens = []
        for word in text.split():
            subword = self._encode_word(word)
            tokens.extend(subword)
        return tokens

    def _encode_word(self, word: str) -> List[str]:
        chars = list(word)
        for merge in self.merges:
            new_chars = []
            i = 0
            while i < len(chars):
                if i < len(chars) - 1 and chars[i] == merge[0] and chars[i + 1] == merge[1]:
                    new_chars.append(''.join(merge))
                    i += 2
                else:
                    new_chars.append(chars[i])
                    i += 1
            chars = new_chars
        return chars

    def get_vocab_size(self) -> int:
        return len(self.vocab)

    def get_special_token_ids(self) -> Dict[str, int]:
        return {token: self.vocab[token] for token in self.special_tokens if token in self.vocab}
