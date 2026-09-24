import numpy as np

from multimodal.cross_modal_attention import (
    CrossModalAttention,
    ModalityFusion,
    ModalityAlignment,
    MultimodalTransformer,
)


def _random_embeddings(n=4, d=256, seed=42):
    rng = np.random.default_rng(seed)
    return rng.standard_normal((n, d)).astype(np.float64)


def test_cross_modal_attention_output_shape():
    attn = CrossModalAttention(embed_dim=256, num_heads=4)
    q = _random_embeddings(1, 256)
    k = _random_embeddings(5, 256)
    v = _random_embeddings(5, 256)
    out = attn.forward(q, k, v)
    assert out.shape == (1, 256)


def test_cross_modal_attention_finite_output():
    attn = CrossModalAttention(embed_dim=128, num_heads=4)
    q = _random_embeddings(2, 128)
    k = _random_embeddings(3, 128)
    v = _random_embeddings(3, 128)
    out = attn.forward(q, k, v)
    assert np.all(np.isfinite(out))


def test_early_fusion_shape():
    fusion = ModalityFusion(embed_dim=256)
    t = _random_embeddings(1, 256)[0]
    i = _random_embeddings(1, 256)[0]
    out = fusion.early_fusion(t, i)
    assert out.shape == (256,)


def test_late_fusion_shape():
    fusion = ModalityFusion(embed_dim=256)
    t = _random_embeddings(1, 256)[0]
    i = _random_embeddings(1, 256)[0]
    out = fusion.late_fusion(t, i)
    assert out.shape == (256,)


def test_hybrid_fusion_shape():
    fusion = ModalityFusion(embed_dim=256)
    t = _random_embeddings(1, 256)[0]
    i = _random_embeddings(1, 256)[0]
    out = fusion.hybrid_fusion(t, i)
    assert out.shape == (256,)


def test_hybrid_fusion_with_audio():
    fusion = ModalityFusion(embed_dim=256)
    t = _random_embeddings(1, 256)[0]
    i = _random_embeddings(1, 256)[0]
    a = _random_embeddings(1, 256)[0]
    out = fusion.hybrid_fusion(t, i, a)
    assert out.shape == (256,)


def test_modality_alignment_score_range():
    alignment = ModalityAlignment(embed_dim=256)
    X = _random_embeddings(10, 256, seed=1)
    Y = _random_embeddings(10, 256, seed=2)
    score = alignment.compute_alignment_score(X, Y)
    assert -1.0 <= score <= 1.0


def test_modality_alignment_perfect_correlation():
    alignment = ModalityAlignment(embed_dim=64)
    rng = np.random.default_rng(0)
    X = rng.standard_normal((20, 64))
    Y = X.copy()
    score = alignment.compute_alignment_score(X, Y)
    assert score > 0.9


def test_align_modalities_returns_dict():
    alignment = ModalityAlignment(embed_dim=64)
    embeddings = {
        "text": _random_embeddings(5, 64, seed=1),
        "image": _random_embeddings(5, 64, seed=2),
    }
    result = alignment.align_modalities(embeddings)
    assert "text_image" in result


def test_multimodal_transformer_forward_shape():
    transformer = MultimodalTransformer(embed_dim=256, num_layers=2)
    inputs = {
        "text": _random_embeddings(3, 256, seed=1),
        "image": _random_embeddings(4, 256, seed=2),
    }
    out = transformer.forward(inputs)
    assert out.shape == (256,)


def test_multimodal_transformer_finite():
    transformer = MultimodalTransformer(embed_dim=128, num_layers=2)
    inputs = {
        "text": _random_embeddings(2, 128, seed=1),
    }
    out = transformer.forward(inputs)
    assert np.all(np.isfinite(out))
