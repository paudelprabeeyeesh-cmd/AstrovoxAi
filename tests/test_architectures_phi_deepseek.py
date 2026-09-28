import os
import sys

import torch

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from models.llm.architectures import ArchitectureRegistry


class TestPhiArchitecture:
    def test_phi_builds(self):
        config = {
            "vocab_size": 1000,
            "hidden_size": 128,
            "num_layers": 2,
            "num_heads": 8,
            "num_kv_heads": 8,
            "intermediate_size": 512,
            "max_seq_len": 64,
            "rope_base": 10000.0,
            "dropout": 0.0,
            "use_bias": False,
            "tie_weights": True,
        }
        model = ArchitectureRegistry.build("phi", config)
        assert model is not None
        params = sum(p.numel() for p in model.parameters())
        assert params > 0

    def test_phi_forward(self):
        config = {
            "vocab_size": 1000,
            "hidden_size": 128,
            "num_layers": 2,
            "num_heads": 8,
            "num_kv_heads": 8,
            "intermediate_size": 512,
            "max_seq_len": 64,
            "rope_base": 10000.0,
            "dropout": 0.0,
            "use_bias": False,
            "tie_weights": True,
        }
        model = ArchitectureRegistry.build("phi", config)
        input_ids = torch.randint(0, 1000, (2, 32))
        out = model(input_ids)
        assert "logits" in out
        assert out["logits"].shape == (2, 32, 1000)

    def test_phi_parameter_count(self):
        config = {
            "vocab_size": 1000,
            "hidden_size": 128,
            "num_layers": 2,
            "num_heads": 8,
            "num_kv_heads": 8,
            "intermediate_size": 512,
            "max_seq_len": 64,
            "rope_base": 10000.0,
            "dropout": 0.0,
            "use_bias": False,
            "tie_weights": True,
        }
        arch = ArchitectureRegistry.get("phi")
        counted = arch.count_parameters(config)
        model = arch.build(config)
        actual = sum(p.numel() for p in model.parameters())
        assert counted == actual, f"Parameter count mismatch: counted {counted}, actual {actual}"


class TestDeepSeekArchitecture:
    def test_deepseek_builds(self):
        config = {
            "vocab_size": 1000,
            "hidden_size": 128,
            "num_layers": 2,
            "num_heads": 8,
            "num_kv_heads": 4,
            "intermediate_size": 512,
            "max_seq_len": 64,
            "rope_base": 10000.0,
            "q_lora_rank": 32,
            "kv_lora_rank": 16,
            "num_experts": 4,
            "top_k": 2,
            "dropout": 0.0,
            "use_bias": False,
            "tie_weights": True,
        }
        model = ArchitectureRegistry.build("deepseek", config)
        assert model is not None
        params = sum(p.numel() for p in model.parameters())
        assert params > 0

    def test_deepseek_forward(self):
        config = {
            "vocab_size": 1000,
            "hidden_size": 128,
            "num_layers": 2,
            "num_heads": 8,
            "num_kv_heads": 4,
            "intermediate_size": 512,
            "max_seq_len": 64,
            "rope_base": 10000.0,
            "q_lora_rank": 32,
            "kv_lora_rank": 16,
            "num_experts": 4,
            "top_k": 2,
            "dropout": 0.0,
            "use_bias": False,
            "tie_weights": True,
        }
        model = ArchitectureRegistry.build("deepseek", config)
        input_ids = torch.randint(0, 1000, (2, 32))
        out = model(input_ids)
        assert "logits" in out
        assert out["logits"].shape == (2, 32, 1000)

    def test_deepseek_parameter_count(self):
        config = {
            "vocab_size": 1000,
            "hidden_size": 128,
            "num_layers": 2,
            "num_heads": 8,
            "num_kv_heads": 4,
            "intermediate_size": 512,
            "max_seq_len": 64,
            "rope_base": 10000.0,
            "q_lora_rank": 32,
            "kv_lora_rank": 16,
            "num_experts": 4,
            "top_k": 2,
            "dropout": 0.0,
            "use_bias": False,
            "tie_weights": True,
        }
        arch = ArchitectureRegistry.get("deepseek")
        counted = arch.count_parameters(config)
        model = arch.build(config)
        actual = sum(p.numel() for p in model.parameters())
        assert counted == actual, f"Parameter count mismatch: counted {counted}, actual {actual}"
