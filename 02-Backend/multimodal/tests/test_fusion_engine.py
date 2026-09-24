import numpy as np

from multimodal.fusion_engine import FusionEngine, FusionResult


def _random_emb(n=1, d=256, seed=42):
    rng = np.random.default_rng(seed)
    return rng.standard_normal((n, d)).astype(np.float64)[0]


def test_fusion_result_dataclass():
    result = FusionResult(
        fused_embedding=np.zeros(256),
        alignment_scores={"a_b": 0.5},
        modality_contributions={"text": 1.0},
    )
    assert result.fused_embedding.shape == (256,)
    assert isinstance(result.alignment_scores, dict)
    assert isinstance(result.modality_contributions, dict)


def test_fusion_engine_default_init():
    engine = FusionEngine()
    assert engine.embed_dim == 256


def test_fusion_engine_custom_init():
    engine = FusionEngine(embed_dim=128)
    assert engine.embed_dim == 128


def test_fusion_engine_fuse_two_modalities():
    engine = FusionEngine(embed_dim=256)
    text = _random_emb(256)
    image = _random_emb(256)
    result = engine.fuse(text, image)
    assert isinstance(result, FusionResult)


def test_fusion_engine_fuse_three_modalities():
    engine = FusionEngine(embed_dim=256)
    text = _random_emb(256)
    image = _random_emb(256)
    audio = _random_emb(256)
    result = engine.fuse(text, image, audio)
    assert isinstance(result, FusionResult)


def test_fusion_engine_fused_embedding_shape():
    engine = FusionEngine(embed_dim=256)
    text = _random_emb(256)
    image = _random_emb(256)
    result = engine.fuse(text, image)
    assert result.fused_embedding.shape == (256,)


def test_fusion_engine_alignment_scores_keys_two():
    engine = FusionEngine(embed_dim=256)
    text = _random_emb(256)
    image = _random_emb(256)
    result = engine.fuse(text, image)
    assert "text_image" in result.alignment_scores


def test_fusion_engine_alignment_scores_keys_three():
    engine = FusionEngine(embed_dim=256)
    text = _random_emb(256)
    image = _random_emb(256)
    audio = _random_emb(256)
    result = engine.fuse(text, image, audio)
    assert "text_image" in result.alignment_scores
    assert "text_audio" in result.alignment_scores
    assert "image_audio" in result.alignment_scores


def test_fusion_engine_modality_contributions_two():
    engine = FusionEngine(embed_dim=256)
    text = _random_emb(256)
    image = _random_emb(256)
    result = engine.fuse(text, image)
    assert "text" in result.modality_contributions
    assert "image" in result.modality_contributions
    assert "audio" not in result.modality_contributions


def test_fusion_engine_modality_contributions_three():
    engine = FusionEngine(embed_dim=256)
    text = _random_emb(256)
    image = _random_emb(256)
    audio = _random_emb(256)
    result = engine.fuse(text, image, audio)
    assert "audio" in result.modality_contributions


def test_fusion_engine_finite_output():
    engine = FusionEngine(embed_dim=128)
    rng = np.random.default_rng(0)
    text = rng.standard_normal(128).astype(np.float64)
    image = rng.standard_normal(128).astype(np.float64)
    result = engine.fuse(text, image)
    assert np.all(np.isfinite(result.fused_embedding))
