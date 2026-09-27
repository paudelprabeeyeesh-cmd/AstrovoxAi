import os
import sys

import pytest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from models.llm.tokenizer.train_tokenizer import load_tokenizer


TOKENIZER_PATH = os.path.join(ROOT, "models", "llm", "tokenizer.json")


@pytest.mark.skipif(not os.path.exists(TOKENIZER_PATH), reason="tokenizer.json not found")
class TestTokenizer:
    def test_load_tokenizer(self):
        tokenizer = load_tokenizer(TOKENIZER_PATH)
        assert tokenizer is not None
        assert hasattr(tokenizer, "encode")
        assert hasattr(tokenizer, "decode")

    def test_special_tokens(self):
        tokenizer = load_tokenizer(TOKENIZER_PATH)
        assert tokenizer.token_to_id("<pad>") is not None
        assert tokenizer.token_to_id("<eos>") is not None

    def test_encode_decode_roundtrip(self):
        tokenizer = load_tokenizer(TOKENIZER_PATH)
        text = "Hello world"
        ids = tokenizer.encode(text).ids if hasattr(tokenizer.encode(text), "ids") else tokenizer.encode(text)
        decoded = tokenizer.decode(ids)
        assert decoded.strip() == text

    def test_empty_string(self):
        tokenizer = load_tokenizer(TOKENIZER_PATH)
        ids = tokenizer.encode("").ids if hasattr(tokenizer.encode(""), "ids") else tokenizer.encode("")
        assert len(ids) == 0
