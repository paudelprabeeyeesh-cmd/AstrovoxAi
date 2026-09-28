import importlib.util
import os
import sys

import pytest
import torch

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from models.llm.model.model import LLM

_model_scaling_spec = importlib.util.spec_from_file_location(
    "model.model_scaling", os.path.join(ROOT, "model", "model_scaling.py")
)
_model_scaling_mod = importlib.util.module_from_spec(_model_scaling_spec)
_model_scaling_spec.loader.exec_module(_model_scaling_mod)
count_parameters = _model_scaling_mod.count_parameters
memory_estimation = _model_scaling_mod.memory_estimation
chinchilla_optimal_tokens = _model_scaling_mod.chinchilla_optimal_tokens


@pytest.fixture
def tiny_config():
    return {
        "vocab_size": 100,
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


class TestLLMModel:
    def test_model_initializes(self, tiny_config):
        model = LLM(tiny_config)
        assert model is not None
        assert model.vocab_size == 100
        assert model.hidden_size == 32
        assert model.num_hidden_layers == 2

    def test_forward_pass(self, tiny_config):
        model = LLM(tiny_config)
        model.eval()
        input_ids = torch.randint(0, 100, (2, 16))
        with torch.no_grad():
            out = model(input_ids)
        assert "logits" in out
        assert out["logits"].shape == (2, 16, 100)

    def test_forward_with_labels(self, tiny_config):
        model = LLM(tiny_config)
        model.eval()
        input_ids = torch.randint(0, 100, (2, 16))
        labels = input_ids.clone()
        with torch.no_grad():
            out = model(input_ids, labels=labels)
        assert "loss" in out
        assert out["loss"].item() > 0

    def test_get_num_params(self, tiny_config):
        model = LLM(tiny_config)
        params = model.get_num_params()
        assert params > 0
        assert params == model.get_num_params_from_config(tiny_config)

    def test_estimate_memory(self, tiny_config):
        mem = LLM.estimate_memory_from_config(tiny_config, training=True, dtype_bytes=2)
        assert "num_params" in mem
        assert "weights_gb" in mem
        assert mem["weights_gb"] > 0

    def test_gradient_checkpointing(self, tiny_config):
        model = LLM(tiny_config)
        model.train()
        input_ids = torch.randint(0, 100, (1, 8))
        labels = input_ids.clone()
        out = model(input_ids, labels=labels, use_gradient_checkpointing=True)
        assert "loss" in out
        assert out["loss"].requires_grad

    def test_from_config(self, tiny_config):
        model = LLM.from_config(tiny_config)
        assert isinstance(model, LLM)
        assert model.hidden_size == 32

    def test_rope_theta(self):
        cfg = {
            "vocab_size": 100,
            "hidden_size": 32,
            "num_hidden_layers": 2,
            "num_attention_heads": 2,
            "intermediate_size": 64,
            "max_position_embeddings": 64,
            "rope_theta": 50000.0,
        }
        model = LLM(cfg)
        assert model.rope_theta == 50000.0


class TestModelScaling:
    def test_count_parameters(self):
        params = count_parameters(
            vocab_size=100,
            hidden_size=32,
            num_hidden_layers=2,
            num_attention_heads=2,
            intermediate_size=64,
        )
        assert params > 0

    def test_memory_estimation(self):
        mem = memory_estimation(num_params=10_000, dtype_bytes=2, training=True)
        assert mem["weights_gb"] > 0
        assert mem["total_base_gb"] > 0

    def test_chinchilla_tokens(self):
        tokens = chinchilla_optimal_tokens(num_params=100_000)
        assert tokens == 2_000_000
