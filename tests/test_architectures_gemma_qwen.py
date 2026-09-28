import os
import sys

import torch

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from models.llm.architectures import ArchitectureRegistry


class TestGemmaArchitecture:
    def test_gemma_builds(self):
        config = {
            "vocab_size": 1000,
            "hidden_size": 128,
            "num_layers": 2,
            "num_heads": 8,
            "num_kv_heads": 4,
            "intermediate_size": 512,
            "max_seq_len": 64,
            "rope_base": 1000000.0,
            "use_local_attention": True,
            "window_size": 32,
            "dropout": 0.0,
            "use_bias": False,
            "tie_weights": True,
        }
        model = ArchitectureRegistry.build("gemma", config)
        assert model is not None
        params = sum(p.numel() for p in model.parameters())
        assert params > 0

    def test_gemma_forward(self):
        config = {
            "vocab_size": 1000,
            "hidden_size": 128,
            "num_layers": 2,
            "num_heads": 8,
            "num_kv_heads": 4,
            "intermediate_size": 512,
            "max_seq_len": 64,
            "rope_base": 1000000.0,
            "use_local_attention": True,
            "window_size": 32,
            "dropout": 0.0,
            "use_bias": False,
            "tie_weights": True,
        }
        model = ArchitectureRegistry.build("gemma", config)
        input_ids = torch.randint(0, 1000, (2, 32))
        out = model(input_ids)
        assert "logits" in out
        assert out["logits"].shape == (2, 32, 1000)

    def test_gemma_parameter_count(self):
        config = {
            "vocab_size": 1000,
            "hidden_size": 128,
            "num_layers": 2,
            "num_heads": 8,
            "num_kv_heads": 4,
            "intermediate_size": 512,
            "max_seq_len": 64,
            "rope_base": 1000000.0,
            "use_local_attention": True,
            "window_size": 32,
            "dropout": 0.0,
            "use_bias": False,
            "tie_weights": True,
        }
        arch = ArchitectureRegistry.get("gemma")
        counted = arch.count_parameters(config)
        model = arch.build(config)
        actual = sum(p.numel() for p in model.parameters())
        assert counted == actual, f"Parameter count mismatch: counted {counted}, actual {actual}"

    def test_gemma_global_attention(self):
        config = {
            "vocab_size": 1000,
            "hidden_size": 128,
            "num_layers": 2,
            "num_heads": 8,
            "num_kv_heads": 4,
            "intermediate_size": 512,
            "max_seq_len": 64,
            "rope_base": 1000000.0,
            "use_local_attention": False,
            "window_size": 32,
            "dropout": 0.0,
            "use_bias": False,
            "tie_weights": True,
        }
        model = ArchitectureRegistry.build("gemma", config)
        input_ids = torch.randint(0, 1000, (2, 32))
        out = model(input_ids)
        assert out["logits"].shape == (2, 32, 1000)


class TestQwenArchitecture:
    def test_qwen_builds(self):
        config = {
            "vocab_size": 1000,
            "hidden_size": 128,
            "num_layers": 2,
            "num_heads": 8,
            "num_kv_heads": 2,
            "intermediate_size": 512,
            "max_seq_len": 64,
            "rope_base": 1000000.0,
            "use_yarn": False,
            "yarn_scale": 1.0,
            "dropout": 0.0,
            "use_bias": False,
            "tie_weights": True,
        }
        model = ArchitectureRegistry.build("qwen", config)
        assert model is not None
        params = sum(p.numel() for p in model.parameters())
        assert params > 0

    def test_qwen_forward(self):
        config = {
            "vocab_size": 1000,
            "hidden_size": 128,
            "num_layers": 2,
            "num_heads": 8,
            "num_kv_heads": 2,
            "intermediate_size": 512,
            "max_seq_len": 64,
            "rope_base": 1000000.0,
            "use_yarn": False,
            "yarn_scale": 1.0,
            "dropout": 0.0,
            "use_bias": False,
            "tie_weights": True,
        }
        model = ArchitectureRegistry.build("qwen", config)
        input_ids = torch.randint(0, 1000, (2, 32))
        out = model(input_ids)
        assert "logits" in out
        assert out["logits"].shape == (2, 32, 1000)

    def test_qwen_parameter_count(self):
        config = {
            "vocab_size": 1000,
            "hidden_size": 128,
            "num_layers": 2,
            "num_heads": 8,
            "num_kv_heads": 2,
            "intermediate_size": 512,
            "max_seq_len": 64,
            "rope_base": 1000000.0,
            "use_yarn": False,
            "yarn_scale": 1.0,
            "dropout": 0.0,
            "use_bias": False,
            "tie_weights": True,
        }
        arch = ArchitectureRegistry.get("qwen")
        counted = arch.count_parameters(config)
        model = arch.build(config)
        actual = sum(p.numel() for p in model.parameters())
        assert counted == actual, f"Parameter count mismatch: counted {counted}, actual {actual}"

    def test_qwen_yarn(self):
        config = {
            "vocab_size": 1000,
            "hidden_size": 128,
            "num_layers": 2,
            "num_heads": 8,
            "num_kv_heads": 2,
            "intermediate_size": 512,
            "max_seq_len": 64,
            "rope_base": 1000000.0,
            "use_yarn": True,
            "yarn_scale": 2.0,
            "dropout": 0.0,
            "use_bias": False,
            "tie_weights": True,
        }
        model = ArchitectureRegistry.build("qwen", config)
        input_ids = torch.randint(0, 1000, (2, 32))
        out = model(input_ids)
        assert out["logits"].shape == (2, 32, 1000)
