from typing import List, Tuple, Dict
from collections import Counter


class BPETrainer:
    def __init__(self, vocab_size: int = 50257, min_frequency: int = 2, special_tokens: Optional[List[str]] = None):
        self.vocab_size = vocab_size
        self.min_frequency = min_frequency
        self.special_tokens = special_tokens or ['<unk>', '<pad>', '<s>', '</s>']
        self.merges: List[Tuple[str, str]] = []
        self.vocab: Dict[str, int] = {}

    def get_stats(self, words: List[List[str]]) -> Counter:
        pairs = Counter()
        for word in words:
            for i in range(len(word) - 1):
                pairs[(word[i], word[i + 1])] += 1
        return pairs

    def merge_vocab(self, pair: Tuple[str, str], v_in: List[List[str]]) -> List[List[str]]:
        v_out = []
        bigram = ' '.join(pair)
        replacement = ''.join(pair)
        for word in v_in:
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

    def train(self, corpus: List[str]) -> None:
        words = [list(word) for text in corpus for word in text.split()]
        self.vocab = {token: idx for idx, token in enumerate(self.special_tokens)}
        idx = len(self.vocab)
        unique_chars = set(char for word in words for char in word)
        for char in sorted(unique_chars):
            if char not in self.vocab:
                self.vocab[char] = idx
                idx += 1
        for _ in range(self.vocab_size - len(self.vocab)):
            pairs = self.get_stats(words)
            if not pairs:
                break
            best = max(pairs, key=pairs.get)
            self.merges.append(best)
            words = self.merge_vocab(best, words)
        for word in words:
            for token in word:
                if token not in self.vocab:
                    self.vocab[token] = idx
                    idx += 1

    def encode(self, text: str) -> List[int]:
        word = list(text)
        for pair in self.merges:
            word = self._merge(word, pair)
        return [self.vocab.get(token, self.vocab.get('<unk>', 0)) for token in word]

    def _merge(self, word: List[str], pair: Tuple[str, str]) -> List[str]:
        new_word = []
        i = 0
        while i < len(word):
            if i < len(word) - 1 and word[i] == pair[0] and word[i + 1] == pair[1]:
                new_word.append(pair[0] + pair[1])
                i += 2
            else:
                new_word.append(word[i])
                i += 1
        return new_word
