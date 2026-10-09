import numpy as np
import pytest

from multimodal.vision_language import (
    ImageFeatures,
    VisionLanguageModel,
)


def _make_image(h=32, w=32):
    return np.random.randint(0, 255, size=(h, w, 3), dtype=np.uint8)


def test_encode_image_returns_image_features():
    model = VisionLanguageModel(feature_dim=256, num_regions=9)
    pixels = _make_image(32, 32)
    feats = model.encode_image(pixels)
    assert isinstance(feats, ImageFeatures)
    assert feats.features.shape == (9, 256)
    assert feats.regions is not None
    assert len(feats.regions) == 9


def test_encode_text_returns_normalized_vector():
    model = VisionLanguageModel()
    vec = model.encode_text("hello world")
    assert vec.shape == (256,)
    assert abs(np.linalg.norm(vec) - 1.0) < 1e-6


def test_encode_text_consistent():
    model = VisionLanguageModel()
    v1 = model.encode_text("hello")
    v2 = model.encode_text("hello")
    np.testing.assert_array_equal(v1, v2)


def test_cross_modal_attention_shapes():
    model = VisionLanguageModel()
    image_features = model.encode_image(_make_image())
    q_emb = model.encode_text("what is in the image")
    context, attn = model.cross_modal_attention(image_features.features, q_emb)
    assert context.shape == (1, 256)
    assert attn.shape == (1, 9)
    assert abs(attn.sum() - 1.0) < 1e-6


def test_answer_question_returns_expected_keys():
    model = VisionLanguageModel()
    image_features = model.encode_image(_make_image())
    result = model.answer_question(image_features, "What color is the object?")
    assert "answer" in result
    assert "confidence" in result
    assert "attention_weights" in result
    assert "context_vector" in result
    assert 0.0 <= result["confidence"] <= 1.0
    assert len(result["attention_weights"]) == 9


def test_answer_question_color_keyword():
    model = VisionLanguageModel()
    image_features = model.encode_image(_make_image())
    result = model.answer_question(image_features, "What color is the object?")
    assert "color" in result["answer"].lower()


def test_generate_caption_returns_string():
    model = VisionLanguageModel()
    image_features = model.encode_image(_make_image())
    caption = model.generate_caption(image_features)
    assert isinstance(caption, str)
    assert len(caption) > 0


def test_compute_vqa_score_perfect_match():
    model = VisionLanguageModel()
    score = model.compute_vqa_score("hello world", "hello world")
    assert score == pytest.approx(1.0)


def test_compute_vqa_score_no_match():
    model = VisionLanguageModel()
    score = model.compute_vqa_score("abc xyz", "hello world")
    assert score == 0.0


def test_compute_vqa_score_partial():
    model = VisionLanguageModel()
    score = model.compute_vqa_score("hello", "hello world")
    assert 0.0 < score < 1.0


def test_spatial_pyramid_constructed():
    model = VisionLanguageModel()
    image_features = model.encode_image(_make_image())
    assert image_features.spatial_pyramid is not None
    assert len(image_features.spatial_pyramid) > 0


def test_patch_to_vector_shape():
    model = VisionLanguageModel(feature_dim=64)
    patch = np.random.randint(0, 255, size=(8, 8, 3), dtype=np.uint8)
    vec = model._patch_to_vector(patch)
    assert vec.shape == (64,)


def test_softmax_normalization():
    model = VisionLanguageModel()
    x = np.array([1.0, 2.0, 3.0])
    s = model._softmax(x)
    assert abs(s.sum() - 1.0) < 1e-6
    assert np.all(s > 0)
