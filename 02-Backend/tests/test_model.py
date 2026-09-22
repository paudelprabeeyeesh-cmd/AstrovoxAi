import pytest
import torch

from app.model import (
    AstroVoxModel,
    GroupedQueryAttention,
    SwiGLU,
    FeedForward,
    MoELayer,
    TransformerBlock,
    build_rotary_pos_emb,
    apply_rotary_pos_emb,
    create_model,
    DEFAULT_CONFIG,
)


def test_rotary_pos_emb_shapes():
    bsz, seq_len, n_heads, head_dim = 2, 16, 4, 8
    q = torch.randn(bsz, n_heads, seq_len, head_dim)
    k = torch.randn(bsz, n_heads, seq_len, head_dim)
    cos, sin = build_rotary_pos_emb(seq_len, head_dim, device=q.device)
    q_rot, k_rot = apply_rotary_pos_emb(q, k, cos, sin)
    assert q_rot.shape == q.shape
    assert k_rot.shape == k.shape


def test_grouped_query_attention_forward():
    bsz, seq_len, d_model = 2, 16, 64
    n_heads, n_kv_heads = 8, 2
    x = torch.randn(bsz, seq_len, d_model)
    attn = GroupedQueryAttention(d_model, n_heads, n_kv_heads)
    out = attn(x)
    assert out.shape == (bsz, seq_len, d_model)


def test_swiglu_activation():
    act = SwiGLU()
    x = torch.randn(2, 16, 64)
    out = act(x)
    assert out.shape == x.shape


def test_feed_forward():
    ff = FeedForward(d_model=64, d_ff=128)
    x = torch.randn(2, 16, 64)
    out = ff(x)
    assert out.shape == x.shape


def test_moe_layer_forward():
    moe = MoELayer(d_model=64, d_ff=128, n_experts=4, top_k=2)
    x = torch.randn(2, 16, 64)
    out, aux_loss = moe(x)
    assert out.shape == x.shape
    assert aux_loss.shape == ()


def test_moe_load_balance_loss_changes():
    moe = MoELayer(d_model=64, d_ff=128, n_experts=4, top_k=2)
    x = torch.randn(2, 16, 64)
    moe(x)
    loss1 = moe.load_balance_loss().item()
    assert isinstance(loss1, float)


def test_transformer_block_dense():
    block = TransformerBlock(d_model=64, n_heads=8, use_moe=False)
    x = torch.randn(2, 16, 64)
    out, aux = block(x)
    assert out.shape == x.shape
    assert aux is None


def test_transformer_block_moe():
    block = TransformerBlock(d_model=64, n_heads=8, use_moe=True, n_experts=4, moe_top_k=2)
    x = torch.randn(2, 16, 64)
    out, aux = block(x)
    assert out.shape == x.shape
    assert aux is not None
    assert aux.shape == ()


def test_model_forward():
    model = AstroVoxModel(vocab_size=100, d_model=64, n_heads=8, n_layers=2, max_seq_len=32)
    input_ids = torch.randint(0, 100, (2, 16))
    logits = model(input_ids)
    assert logits.shape == (2, 16, 100)


def test_model_with_gqa():
    model = AstroVoxModel(
        vocab_size=100,
        d_model=64,
        n_heads=8,
        n_kv_heads=2,
        n_layers=2,
        max_seq_len=32,
    )
    input_ids = torch.randint(0, 100, (2, 16))
    logits = model(input_ids)
    assert logits.shape == (2, 16, 100)


def test_model_with_moe():
    model = AstroVoxModel(
        vocab_size=100,
        d_model=64,
        n_heads=8,
        n_layers=2,
        max_seq_len=32,
        use_moe=True,
        n_experts=4,
        moe_top_k=2,
    )
    input_ids = torch.randint(0, 100, (2, 16))
    logits = model(input_ids)
    assert logits.shape == (2, 16, 100)
    assert model.aux_loss is not None


def test_model_n_params():
    model = AstroVoxModel(vocab_size=100, d_model=64, n_heads=8, n_layers=2, max_seq_len=32)
    assert model.n_params > 0


def test_create_model_factory():
    model = create_model({"vocab_size": 100, "d_model": 64, "n_heads": 8, "n_layers": 2, "max_seq_len": 32})
    assert isinstance(model, AstroVoxModel)
    input_ids = torch.randint(0, 100, (2, 8))
    logits = model(input_ids)
    assert logits.shape == (2, 8, 100)


def test_model_seq_len_too_long():
    model = AstroVoxModel(vocab_size=100, d_model=64, n_heads=8, n_layers=2, max_seq_len=32)
    input_ids = torch.randint(0, 100, (1, 64))
    with pytest.raises(ValueError):
        model(input_ids)
