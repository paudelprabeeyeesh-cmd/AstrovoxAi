import numpy as np

from multimodal.vision_pipeline import VisionPipeline, VisionPipelineResult


def _make_image(h=32, w=32):
    return np.random.randint(0, 255, size=(h, w, 3), dtype=np.uint8)


def test_vision_pipeline_result_dataclass():
    result = VisionPipelineResult(
        features=None,
        caption="a scene",
        vqa_score=0.9,
    )
    assert result.caption == "a scene"
    assert result.vqa_score == 0.9
    assert isinstance(result.metadata, dict)


def test_vision_pipeline_default_init():
    pipeline = VisionPipeline()
    assert pipeline.feature_dim == 256
    assert pipeline.num_regions == 9


def test_vision_pipeline_custom_init():
    pipeline = VisionPipeline(feature_dim=128, num_regions=4)
    assert pipeline.feature_dim == 128
    assert pipeline.num_regions == 4


def test_vision_pipeline_process_returns_result():
    pipeline = VisionPipeline()
    pixels = _make_image(64, 64)
    result = pipeline.process(pixels)
    assert isinstance(result, VisionPipelineResult)


def test_vision_pipeline_process_features_type():
    pipeline = VisionPipeline()
    pixels = _make_image(64, 64)
    result = pipeline.process(pixels)
    from multimodal.vision_language import ImageFeatures
    assert isinstance(result.features, ImageFeatures)


def test_vision_pipeline_caption_is_string():
    pipeline = VisionPipeline()
    pixels = _make_image(64, 64)
    result = pipeline.process(pixels)
    assert isinstance(result.caption, str)
    assert len(result.caption) > 0


def test_vision_pipeline_vqa_score_in_range():
    pipeline = VisionPipeline()
    pixels = _make_image(64, 64)
    result = pipeline.process(pixels)
    assert 0.0 <= result.vqa_score <= 1.0


def test_vision_pipeline_metadata_keys():
    pipeline = VisionPipeline()
    pixels = _make_image(64, 64)
    result = pipeline.process(pixels)
    assert "num_regions" in result.metadata
    assert "shape" in result.metadata


def test_vision_pipeline_regions_count():
    pipeline = VisionPipeline(feature_dim=256, num_regions=9)
    pixels = _make_image(64, 64)
    result = pipeline.process(pixels)
    assert result.metadata["num_regions"] == 9
