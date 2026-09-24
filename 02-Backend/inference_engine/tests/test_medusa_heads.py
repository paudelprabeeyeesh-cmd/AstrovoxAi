
import pytest
import numpy as np

from inference_engine.medusa_heads import (
    MedusaHeads, MedusaConfig, MedusaHead, medusa_sampling
)


def test_medusa_head_forward():
    head = MedusaHead(head_id=0, input_dim=64, output_dim=100)
    hidden = np.random.randn(2, 64).astype(np.float32)
    logits = head.forward(hidden)
    assert logits.shape == (2, 100)


def test_medusa_heads_forward():
    heads = MedusaHeads(MedusaConfig(num_heads=4, head_input_dim=64, head_output_dim=100))
    hidden = np.random.randn(2, 64).astype(np.float32)
    outputs = heads.forward(hidden)
    assert len(outputs) == 4
    for out in outputs:
        assert out.shape == (2, 100)


def test_medusa_verify():
    heads = MedusaHeads(MedusaConfig(num_heads=3, head_input_dim=64, head_output_dim=100))
    target_logits = np.zeros((1, 100), dtype=np.float32)
    target_logits[0, 0] = 10.0
    target_logits[0, 1] = 1.0
    target_logits[0, 2] = 1.0
    draft_tokens = [[0], [1], [2]]
    verified = heads.verify(draft_tokens, target_logits)
    assert len(verified) == 3


def test_medusa_generate_tree():
    heads = MedusaHeads(MedusaConfig(num_heads=4, head_input_dim=64, head_output_dim=100))
    hidden = np.random.randn(1, 64).astype(np.float32)
    tree = heads.generate_tree(hidden, depth=3)
    assert len(tree) == 3
    for branch in tree:
        assert len(branch) == 1
        assert 0 <= branch[0] < 100


def test_medusa_sampling():
    logits_list = [np.random.randn(1, 100).astype(np.float32) for _ in range(3)]
    sampled = medusa_sampling(logits_list, temperature=1.0)
    assert len(sampled) == 3
    for s in sampled:
        assert len(s) == 1
        assert 0 <= s[0] < 100


def test_medusa_config_defaults():
    config = MedusaConfig()
    assert config.num_heads == 4
    assert config.head_input_dim == 128
    assert config.head_output_dim == 1000
