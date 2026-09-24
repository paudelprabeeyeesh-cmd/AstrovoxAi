import numpy as np

from multimodal.video_language import (
    VideoFeatures,
    VideoLanguageModel,
)


def _make_frames(n=16, h=64, w=64):
    return [np.random.randint(0, 255, size=(h, w, 3), dtype=np.uint8) for _ in range(n)]


def test_extract_frames_subsamples_when_needed():
    model = VideoLanguageModel(fps=4.0)
    frames = _make_frames(16)
    sampled = model.extract_frames(frames, frame_rate=8.0)
    assert len(sampled) <= len(frames)


def test_extract_frames_returns_all_when_rate_lower():
    model = VideoLanguageModel(fps=16.0)
    frames = _make_frames(8)
    sampled = model.extract_frames(frames, frame_rate=8.0)
    assert len(sampled) == len(frames)


def test_compute_temporal_features_shape():
    model = VideoLanguageModel(feature_dim=128)
    frames = _make_frames(8, 32, 32)
    temporal = model.compute_temporal_features(frames)
    assert temporal.shape == (128,)


def test_compute_temporal_features_empty():
    model = VideoLanguageModel()
    temporal = model.compute_temporal_features([])
    assert np.all(temporal == 0)


def test_estimate_optical_flow_shape():
    model = VideoLanguageModel()
    prev = _make_frames(1, 32, 32)[0]
    curr = _make_frames(1, 32, 32)[0]
    flow = model.estimate_optical_flow(prev, curr)
    assert flow.shape == (32, 32, 2)


def test_understand_video_returns_expected_keys():
    model = VideoLanguageModel()
    frames = _make_frames(16)
    result = model.understand_video(frames, frame_rate=8.0, question="What is happening?")
    assert "answer" in result
    assert "temporal_features" in result
    assert "num_sampled_frames" in result
    assert "duration" in result


def test_understand_video_duration():
    model = VideoLanguageModel()
    frames = _make_frames(16)
    result = model.understand_video(frames, frame_rate=8.0, question="How long is the video?")
    assert abs(result["duration"] - 2.0) < 0.1


def test_summarize_video_returns_string():
    model = VideoLanguageModel()
    frames = _make_frames(8)
    summary = model.summarize_video(VideoFeatures(frames=frames, temporal_features=np.zeros(128), optical_flow=None, fps=8.0, duration=1.0))
    assert isinstance(summary, str)


def test_frame_to_vector_shape():
    model = VideoLanguageModel()
    frame = _make_frames(1, 32, 32)[0]
    vec = model._frame_to_vector(frame)
    assert vec.shape == (32,)


def test_temporal_reasoning_how_many_frames():
    model = VideoLanguageModel()
    frames = _make_frames(8)
    feats = VideoFeatures(frames=frames, temporal_features=np.zeros(128), optical_flow=None, fps=8.0, duration=1.0)
    answer = model._temporal_reasoning(feats, "How many frames?")
    assert "8" in answer


def test_block_match_returns_offset():
    model = VideoLanguageModel()
    prev = np.ones((8, 8), dtype=np.float64) * 128
    curr = np.ones((8, 8), dtype=np.float64) * 128
    dx, dy = model._block_match(prev, curr, search_range=3)
    assert isinstance(dx, (int, np.integer))
    assert isinstance(dy, (int, np.integer))
