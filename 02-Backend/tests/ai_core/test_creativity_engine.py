import numpy as np
from ai_core.creativity_engine import CreativityEngine, CreativeOutput, NoveltySearch


def test_creative_generation():
    engine = CreativityEngine()
    outputs = engine.generate("idea", n=3, temperature=0.5)
    assert len(outputs) == 3
    for out in outputs:
        assert isinstance(out, CreativeOutput)
        assert out.novelty >= 0.0
        assert 0.0 <= out.quality <= 1.0


def test_recombination():
    engine = CreativityEngine()
    outputs = engine.generate("base", n=4)
    recombined = engine.recombine(outputs)
    assert len(recombined) > 0
    assert all(isinstance(c, CreativeOutput) for c in recombined)


def test_style_transfer():
    engine = CreativityEngine()
    engine.style.register_style("modern", vector=np.ones(16))
    content_vec = np.zeros(16)
    result = engine.transfer_style(content_vec, "modern", strength=0.8)
    assert result.shape == (16,)
    assert np.allclose(result, 0.8 * np.ones(16))


def test_novelty_search_archive():
    novelty = NoveltySearch(archive_size=10)
    b1 = np.random.randn(16)
    b2 = np.random.randn(16)
    n1 = novelty.evaluate_novelty(b1)
    n2 = novelty.evaluate_novelty(b2)
    assert n1 == 1.0
    assert n2 > 0.0
    novelty.update_archive(b1, 0.5)
    assert len(novelty.archive) == 1


def test_style_blend():
    engine = CreativityEngine()
    engine.style.register_style("a", vector=np.ones(16))
    engine.style.register_style("b", vector=-np.ones(16))
    blended = engine.style.blend_styles(["a", "b"], weights=[0.5, 0.5])
    assert np.allclose(blended, 0.0)
