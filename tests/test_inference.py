import os
import sys

import pytest
import torch

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from models.llm.model.model import LLM
from models.llm.inference.engine import InferenceEngine, SamplingParams, GenerationOutput
from models.llm.tokenizer.train_tokenizer import load_tokenizer
from models.llm.utils.helpers import load_config, get_device

CONFIG_100M = os.path.join(ROOT, "models", "llm", "configs", "config_100m.yaml")
TOKENIZER_PATH = os.path.join(ROOT, "models", "llm", "tokenizer.json")


@pytest.fixture
def tiny_model():
    config = {
        "vocab_size": 1000,
        "hidden_size": 32,
        "num_hidden_layers": 2,
        "num_attention_heads": 2,
        "intermediate_size": 64,
        "max_position_embeddings": 64,
        "rms_norm_eps": 1e-5,
        "rope_theta": 10000.0,
        "activation": "swiglu",
        "attention_bias": False,
        "mlp_bias": False,
        "dropout": 0.0,
        "tie_weights": True,
    }
    model = LLM(config)
    model.eval()
    return model


@pytest.fixture
def tiny_tokenizer():
    if not os.path.exists(TOKENIZER_PATH):
        pytest.skip("tokenizer.json not found")
    return load_tokenizer(TOKENIZER_PATH)


class TestInferenceEngine:
    def test_engine_initializes(self, tiny_model, tiny_tokenizer):
        engine = InferenceEngine(tiny_model, tiny_tokenizer)
        assert engine is not None
        assert engine.model is tiny_model

    def test_generate_returns_output(self, tiny_model, tiny_tokenizer):
        engine = InferenceEngine(tiny_model, tiny_tokenizer)
        output = engine.generate("Hello", params=SamplingParams(max_new_tokens=10))
        assert isinstance(output, GenerationOutput)
        assert isinstance(output.text, str)
        assert output.num_tokens > 0

    def test_generate_respects_max_tokens(self, tiny_model, tiny_tokenizer):
        engine = InferenceEngine(tiny_model, tiny_tokenizer)
        output = engine.generate("Hello", params=SamplingParams(max_new_tokens=3))
        assert output.num_tokens <= 3

    def test_count_tokens(self, tiny_model, tiny_tokenizer):
        engine = InferenceEngine(tiny_model, tiny_tokenizer)
        count = engine.count_tokens("Hello world")
        assert count > 0

    def test_batch_generate(self, tiny_model, tiny_tokenizer):
        engine = InferenceEngine(tiny_model, tiny_tokenizer)
        outputs = engine.batch_generate(["Hello", "World"], params=SamplingParams(max_new_tokens=5))
        assert len(outputs) == 2
        for out in outputs:
            assert isinstance(out, GenerationOutput)

    def test_beam_search(self, tiny_model, tiny_tokenizer):
        engine = InferenceEngine(tiny_model, tiny_tokenizer)
        output = engine.beam_search("Hello", beam_width=2, max_new_tokens=5)
        assert isinstance(output, GenerationOutput)
        assert output.num_tokens > 0

    def test_kv_cache_reset(self, tiny_model, tiny_tokenizer):
        engine = InferenceEngine(tiny_model, tiny_tokenizer)
        engine.generate("Hello", params=SamplingParams(max_new_tokens=5))
        engine.kv_cache.reset()
        assert len(engine.kv_cache.free_blocks) == engine.kv_cache.max_blocks
