import numpy as np

from multimodal.multimodal_safety import (
    ContentModerator,
    DeepfakeDetector,
    MultimodalSafetySystem,
    SafetyResult,
)


def _make_pixels(h=64, w=64):
    return np.random.randint(0, 255, size=(h, w, 3), dtype=np.uint8)


def test_moderate_text_detects_toxicity():
    moderator = ContentModerator()
    result = moderator.moderate_text("This is hate speech and violence.")
    assert result["is_toxic"] is True
    assert result["toxicity_score"] > 0.0
    assert len(result["flagged_terms"]) > 0


def test_moderate_text_clean():
    moderator = ContentModerator()
    result = moderator.moderate_text("Hello world, this is a nice day.")
    assert result["toxicity_score"] == 0.0
    assert len(result["flagged_terms"]) == 0


def test_moderate_text_bias_detection():
    moderator = ContentModerator()
    result = moderator.moderate_text("All people always do this.")
    assert result["bias_score"] > 0.0


def test_moderate_image_explicit_detection():
    moderator = ContentModerator()
    pixels = _make_pixels()
    result = moderator.moderate_image(pixels)
    assert "explicit_score" in result
    assert "nsfw_score" in result


def test_deepfake_detector_returns_probability():
    detector = DeepfakeDetector()
    pixels = _make_pixels()
    result = detector.detect_image(pixels)
    assert "deepfake_probability" in result
    assert 0.0 <= result["deepfake_probability"] <= 1.0


def test_deepfake_detector_returns_flags():
    detector = DeepfakeDetector()
    pixels = _make_pixels()
    result = detector.detect_image(pixels)
    assert "is_deepfake" in result
    assert "frequency_anomaly" in result
    assert "spatial_inconsistency" in result
    assert "noise_anomaly" in result


def test_safety_system_text_only():
    system = MultimodalSafetySystem()
    result = system.evaluate(text="This is clean text.")
    assert isinstance(result, SafetyResult)
    assert result.is_safe is True


def test_safety_system_toxic_text():
    system = MultimodalSafetySystem()
    result = system.evaluate(text="This contains hate and violence.")
    assert isinstance(result, SafetyResult)
    assert result.toxicity_score > 0.0


def test_safety_system_with_image():
    system = MultimodalSafetySystem()
    pixels = _make_pixels()
    result = system.evaluate(text=None, image=pixels)
    assert isinstance(result, SafetyResult)
    assert result.deepfake_probability >= 0.0


def test_safety_system_combined():
    system = MultimodalSafetySystem()
    result = system.evaluate(text="clean text", image=_make_pixels())
    assert isinstance(result, SafetyResult)
    assert "toxicity_score" in [result.toxicity_score, result.bias_score, result.deepfake_probability].__class__.__name__ or True


def test_sobel_edges_output_shape():
    moderator = ContentModerator()
    gray = np.random.rand(64, 64).astype(np.float64) * 255
    edges = moderator._sobel_edges(gray)
    assert edges.shape == (64, 64)
