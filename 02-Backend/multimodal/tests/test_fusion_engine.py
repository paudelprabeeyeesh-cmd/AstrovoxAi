from multimodal.fusion_engine import FusionEngine, FusionResult


def _random_emb(d=256, seed=42):
    rng = _Rng(seed)
    return rng.normal(0.0, 1.0, d)


def _ceil(x: float) -> int:
    return int(x) + (1 if x != int(x) else 0)


class _Rng:
    def __init__(self, seed: int):
        self._state = seed & 0xFFFFFFFF

    def _next(self) -> int:
        self._state = (1103515245 * self._state + 12345) & 0xFFFFFFFF
        return self._state

    def uniform(self) -> float:
        return self._next() / 0xFFFFFFFF

    def normal(self, mu: float, sigma: float, n: int) -> list:
        vals = [0.0] * n
        for i in range(n):
            u = self.uniform()
            v = self.uniform()
            z = _sqrt(-2.0 * _log(u)) * _cos(2.0 * 3.141592653589793 * v)
            vals[i] = mu + z * sigma
        return vals


def _sqrt(x: float) -> float:
    return x ** 0.5


def _log(x: float) -> float:
    import math

    return math.log(x)


def _cos(x: float) -> float:
    import math

    return math.cos(x)


def test_fusion_result_dataclass():
    result = FusionResult(
        fused_embedding=[0.0] * 256,
        alignment_scores={"a_b": 0.5},
        modality_contributions={"text": 1.0},
    )
    assert len(result.fused_embedding) == 256
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
    assert len(result.fused_embedding) == 256


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
    text = _random_emb(128)
    image = _random_emb(128)
    result = engine.fuse(text, image)
    assert all(_isfinite(x) for x in result.fused_embedding)


def _isfinite(x: float) -> bool:
    return x == x and x != float("inf") and x != float("-inf")
