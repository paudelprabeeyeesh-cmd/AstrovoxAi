import os
import math
import torch
import pytest
import torch.nn as nn
from models.llm.model.model import LLM
from models.llm.utils.helpers import load_config


def tiny_config():
    return {
        "vocab_size": 100,
        "hidden_size": 64,
        "num_hidden_layers": 2,
        "num_attention_heads": 2,
        "intermediate_size": 128,
        "max_position_embeddings": 32,
        "rms_norm_eps": 1e-5,
        "rope_theta": 10000.0,
        "activation": "swiglu",
        "attention_bias": False,
        "mlp_bias": False,
        "dropout": 0.0,
        "tie_weights": True,
    }


def test_tiny_forward_backward():
    m = LLM(tiny_config(), device=torch.device("cpu"), dtype=torch.bfloat16)
    x = torch.randint(0, 100, (2, 8))
    y = torch.randint(0, 100, (2, 8))
    out = m(x, labels=y)
    assert out["loss"].item() > 0
    out["loss"].backward()
    for n, p in m.named_parameters():
        if p.requires_grad and p.grad is not None:
            assert torch.isfinite(p.grad).all(), f"NaN grad in {n}"


def test_overfit_tiny_dataset():
    m = LLM(tiny_config(), device=torch.device("cpu"), dtype=torch.bfloat16)
    opt = torch.optim.AdamW(m.parameters(), lr=1e-3)
    data = [(torch.randint(0, 100, (1, 8)), torch.randint(0, 100, (1, 8))) for _ in range(10)]
    losses = []
    for step in range(20):
        loss = 0.0
        opt.zero_grad()
        for x, y in data:
            out = m(x, labels=y)
            loss += out["loss"]
        loss = loss / len(data)
        loss.backward()
        torch.nn.utils.clip_grad_norm_(m.parameters(), 1.0)
        opt.step()
        losses.append(loss.item())
    assert losses[0] > losses[-1], f"Loss did not decrease: {losses}"


def test_checkpoint_save_load():
    m = LLM(tiny_config(), device=torch.device("cpu"), dtype=torch.bfloat16)
    x = torch.randint(0, 100, (2, 8))
    out1 = m(x, labels=x)
    torch.save(m.state_dict(), "test_ckpt.pt")
    m2 = LLM(tiny_config(), device=torch.device("cpu"), dtype=torch.bfloat16)
    m2.load_state_dict(torch.load("test_ckpt.pt", weights_only=True))
    out2 = m2(x, labels=x)
    assert torch.allclose(out1["logits"], out2["logits"], atol=1e-5)
    os.remove("test_ckpt.pt")


def test_config_validation():
    bad = dict(tiny_config())
    bad["hidden_size"] = 10
    bad["num_attention_heads"] = 3
    with pytest.raises(ValueError):
        LLM(bad)


def test_4b_forward_shape():
    c = load_config("models/llm/configs/config_4b.yaml")
    c["num_hidden_layers"] = 1
    m = LLM(c, device=torch.device("cpu"), dtype=torch.bfloat16)
    x = torch.randint(0, c["vocab_size"], (1, 16))
    out = m(x)
    assert out["logits"].shape == (1, 16, c["vocab_size"])
