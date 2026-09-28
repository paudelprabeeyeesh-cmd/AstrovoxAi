import os
import sys

import pytest
import torch

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from models.llm.architectures import ArchitectureRegistry


class TestGPT2Architecture:
    def test_gpt2_builds(self):
        config = {
            "vocab_size": 1000,
            "hidden_size": 256,
            "num_layers": 4,
            "num_heads": 4,
            "intermediate_size": 1024,
            "max_seq_len": 128,
            "dropout": 0.1,
            "use_bias": True,
            "tie_weights": True,
        }
        model = ArchitectureRegistry.build("gpt2", config)
        assert model is not None
        params = sum(p.numel() for p in model.parameters())
        assert params > 0

    def test_gpt2_forward(self):
        config = {
            "vocab_size": 1000,
            "hidden_size": 128,
            "num_layers": 2,
            "num_heads": 4,
            "intermediate_size": 512,
            "max_seq_len": 64,
            "dropout": 0.0,
            "use_bias": True,
            "tie_weights": True,
        }
        model = ArchitectureRegistry.build("gpt2", config)
        input_ids = torch.randint(0, 1000, (2, 32))
        out = model(input_ids)
        assert "logits" in out
        assert out["logits"].shape == (2, 32, 1000)

    def test_gpt2_parameter_count(self):
        config = {
            "vocab_size": 50257,
            "hidden_size": 768,
            "num_layers": 12,
            "num_heads": 12,
            "intermediate_size": 3072,
            "max_seq_len": 1024,
            "dropout": 0.1,
            "use_bias": True,
            "tie_weights": True,
        }
        arch = ArchitectureRegistry.get("gpt2")
        counted = arch.count_parameters(config)
        model = arch.build(config)
        actual = sum(p.numel() for p in model.parameters())
        assert counted == actual, f"Parameter count mismatch: counted {counted}, actual {actual}"


class TestLlamaArchitecture:
    def test_llama_builds(self):
        config = {
            "vocab_size": 32000,
            "hidden_size": 512,
            "num_layers": 4,
            "num_heads": 8,
            "num_kv_heads": 4,
            "intermediate_size": 2048,
            "max_seq_len": 2048,
            "rope_base": 500000.0,
            "dropout": 0.1,
            "use_bias": False,
            "tie_weights": True,
        }
        model = ArchitectureRegistry.build("llama", config)
        assert model is not None
        params = sum(p.numel() for p in model.parameters())
        assert params > 0

    def test_llama_forward(self):
        config = {
            "vocab_size": 32000,
            "hidden_size": 512,
            "num_layers": 4,
            "num_heads": 8,
            "num_kv_heads": 4,
            "intermediate_size": 2048,
            "max_seq_len": 128,
            "rope_base": 500000.0,
            "dropout": 0.0,
            "use_bias": False,
            "tie_weights": True,
        }
        model = ArchitectureRegistry.build("llama", config)
        input_ids = torch.randint(0, 32000, (2, 64))
        out = model(input_ids)
        assert "logits" in out
        assert out["logits"].shape == (2, 64, 32000)

    def test_llama_gqa(self):
        config = {
            "vocab_size": 32000,
            "hidden_size": 512,
            "num_layers": 2,
            "num_heads": 8,
            "num_kv_heads": 2,
            "intermediate_size": 2048,
            "max_seq_len": 64,
            "rope_base": 500000.0,
            "dropout": 0.0,
            "use_bias": False,
            "tie_weights": True,
        }
        model = ArchitectureRegistry.build("llama", config)
        input_ids = torch.randint(0, 32000, (1, 32))
        out = model(input_ids)
        assert out["logits"].shape == (1, 32, 32000)


class TestMistralArchitecture:
    def test_mistral_builds(self):
        config = {
            "vocab_size": 32000,
            "hidden_size": 512,
            "num_layers": 4,
            "num_heads": 8,
            "num_kv_heads": 2,
            "intermediate_size": 2048,
            "max_seq_len": 2048,
            "window_size": 512,
            "rope_base": 1000000.0,
            "dropout": 0.1,
            "use_bias": False,
            "tie_weights": True,
            "use_moe": False,
        }
        model = ArchitectureRegistry.build("mistral", config)
        assert model is not None

    def test_mixtral_moe(self):
        config = {
            "vocab_size": 32000,
            "hidden_size": 256,
            "num_layers": 2,
            "num_heads": 8,
            "num_kv_heads": 2,
            "intermediate_size": 512,
            "max_seq_len": 512,
            "window_size": None,
            "rope_base": 1000000.0,
            "dropout": 0.0,
            "use_bias": False,
            "tie_weights": True,
            "use_moe": True,
            "num_experts": 4,
            "top_k": 2,
        }
        model = ArchitectureRegistry.build("mistral", config)
        input_ids = torch.randint(0, 32000, (2, 64))
        out = model(input_ids)
        assert "logits" in out
        assert out["logits"].shape == (2, 64, 32000)


class TestArchitectureRegistry:
    def test_list_architectures(self):
        archs = ArchitectureRegistry.list_architectures()
        assert "gpt2" in archs
        assert "llama" in archs
        assert "mistral" in archs

    def test_compare(self):
        configs = {
            "gpt2": {
                "vocab_size": 1000,
                "hidden_size": 256,
                "num_layers": 4,
                "num_heads": 4,
                "intermediate_size": 1024,
                "max_seq_len": 128,
                "dropout": 0.1,
                "use_bias": True,
                "tie_weights": True,
            },
            "llama": {
                "vocab_size": 1000,
                "hidden_size": 256,
                "num_layers": 4,
                "num_heads": 4,
                "num_kv_heads": 4,
                "intermediate_size": 1024,
                "max_seq_len": 128,
                "rope_base": 500000.0,
                "dropout": 0.1,
                "use_bias": False,
                "tie_weights": True,
            },
        }
        results = ArchitectureRegistry.compare(configs)
        assert "gpt2" in results
        assert "llama" in results
        assert results["gpt2"]["parameters"] > 0
        assert results["llama"]["parameters"] > 0
