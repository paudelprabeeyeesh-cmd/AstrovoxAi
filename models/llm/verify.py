import os
import sys
import torch

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from model.model import LLM
from utils.helpers import load_config, count_parameters, get_device


def verify_instantiation():
    config = {
        "vocab_size": 100,
        "hidden_size": 64,
        "num_hidden_layers": 2,
        "num_attention_heads": 2,
        "intermediate_size": 128,
        "max_position_embeddings": 64,
        "dropout": 0.0,
        "layer_norm_epsilon": 1e-5,
    }
    model = LLM(config)
    assert model is not None
    assert model.get_num_params(trainable_only=True) > 0
    assert model.get_num_params(trainable_only=False) >= model.get_num_params(trainable_only=True)
    print(f"Instantiation OK: {model.get_num_params():,} params")


def verify_forward():
    config = {
        "vocab_size": 100,
        "hidden_size": 64,
        "num_hidden_layers": 2,
        "num_attention_heads": 2,
        "intermediate_size": 128,
        "max_position_embeddings": 64,
        "dropout": 0.0,
        "layer_norm_epsilon": 1e-5,
    }
    model = LLM(config)
    model.eval()
    input_ids = torch.randint(0, 100, (1, 16))
    with torch.no_grad():
        out = model(input_ids)
    assert "logits" in out
    assert out["logits"].shape == (1, 16, 100)
    print(f"Forward OK: logits shape {out['logits'].shape}")


def verify_from_config():
    config = {
        "vocab_size": 100,
        "hidden_size": 64,
        "num_hidden_layers": 2,
        "num_attention_heads": 2,
        "intermediate_size": 128,
        "max_position_embeddings": 64,
        "dropout": 0.0,
        "layer_norm_epsilon": 1e-5,
    }
    model = LLM.from_config(config)
    assert model is not None
    assert model.get_num_params() > 0
    print("from_config OK")


def verify_count_parameters():
    config = {
        "vocab_size": 100,
        "hidden_size": 64,
        "num_hidden_layers": 2,
        "num_attention_heads": 2,
        "intermediate_size": 128,
        "max_position_embeddings": 64,
        "dropout": 0.0,
        "layer_norm_epsilon": 1e-5,
    }
    model = LLM(config)
    assert count_parameters(model) == model.get_num_params()
    print(f"count_parameters OK: {count_parameters(model):,}")


def verify_device_selection():
    device = get_device()
    assert device in ("cpu", "cuda", "mps")
    print(f"Device selection OK: {device}")


if __name__ == "__main__":
    verify_instantiation()
    verify_forward()
    verify_from_config()
    verify_count_parameters()
    verify_device_selection()
    print("All verification passed.")
