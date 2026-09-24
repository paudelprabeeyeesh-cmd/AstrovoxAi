import numpy as np
import pytest

from multimodal.multimodal_evaluation import (
    VQAMetrics,
    AudioMetrics,
    VideoMetrics,
    MultimodalEvaluator,
)


def test_exact_match_perfect():
    metrics = VQAMetrics()
    assert metrics.exact_match("hello world", "hello world") == 1.0


def test_exact_match_case_insensitive():
    metrics = VQAMetrics()
    assert metrics.exact_match("Hello World", "hello world") == 1.0


def test_exact_match_mismatch():
    metrics = VQAMetrics()
    assert metrics.exact_match("hello", "world") == 0.0


def test_f1_score_perfect():
    metrics = VQAMetrics()
    assert metrics.f1_score("hello world", "hello world") == pytest.approx(1.0)


def test_f1_score_partial():
    metrics = VQAMetrics()
    score = metrics.f1_score("hello", "hello world")
    assert 0.0 < score < 1.0


def test_f1_score_no_match():
    metrics = VQAMetrics()
    assert metrics.f1_score("abc", "xyz") == 0.0


def test_vqa_accuracy_perfect():
    metrics = VQAMetrics()
    acc = metrics.vqa_accuracy(["yes", "no"], ["yes", "no"], min_occurrences=1)
    assert acc == pytest.approx(1.0)


def test_vqa_accuracy_empty():
    metrics = VQAMetrics()
    acc = metrics.vqa_accuracy([], [])
    assert acc == 0.0


def test_bleu_like_perfect():
    metrics = VQAMetrics()
    score = metrics.bleu_like("hello world", "hello world")
    assert score == pytest.approx(1.0)


def test_bleu_like_no_match():
    metrics = VQAMetrics()
    score = metrics.bleu_like("abc", "xyz")
    assert score == 0.0


def test_audio_snr_high():
    metrics = AudioMetrics()
    clean = np.sin(np.linspace(0, 4 * np.pi, 1000))
    noisy = clean + 0.01 * np.random.randn(1000)
    snr = metrics.snr(clean, noisy)
    assert snr > 20


def test_audio_snr_infinite_for_identical():
    metrics = AudioMetrics()
    signal = np.sin(np.linspace(0, 4 * np.pi, 1000))
    snr = metrics.snr(signal, signal)
    assert snr == float("inf")


def test_audio_psd_ratio_range():
    metrics = AudioMetrics()
    clean = np.sin(np.linspace(0, 4 * np.pi, 1000))
    proc = clean + 0.01 * np.random.randn(1000)
    ratio = metrics.psd_ratio(clean, proc)
    assert 0.0 <= ratio <= 10.0


def test_audio_stoi_like_range():
    metrics = AudioMetrics()
    clean = np.sin(np.linspace(0, 4 * np.pi, 1000))
    proc = clean + 0.05 * np.random.randn(1000)
    stoi = metrics.stoi_like(clean, proc)
    assert 0.0 <= stoi <= 1.0


def test_video_psnr_perfect():
    metrics = VideoMetrics()
    frame = np.random.randint(0, 255, size=(32, 32, 3), dtype=np.uint8).astype(np.float64)
    psnr = metrics.psnr(frame, frame)
    assert psnr == float("inf")


def test_video_ssim_range():
    metrics = VideoMetrics()
    f1 = np.random.randint(0, 255, size=(32, 32, 3), dtype=np.uint8).astype(np.float64)
    f2 = np.random.randint(0, 255, size=(32, 32, 3), dtype=np.uint8).astype(np.float64)
    ssim = metrics.ssim(f1, f2)
    assert -1.0 <= ssim <= 1.0


def test_video_temporal_consistency_perfect():
    metrics = VideoMetrics()
    frames = np.stack([np.ones((16, 16, 3), dtype=np.float64) for _ in range(4)])
    tc = metrics.temporal_consistency(frames)
    assert tc == pytest.approx(1.0)


def test_evaluator_vqa_returns_dict():
    evaluator = MultimodalEvaluator()
    result = evaluator.evaluate_vqa(["yes"], ["yes"])
    assert "exact_match" in result
    assert "f1_score" in result
    assert "vqa_accuracy" in result


def test_evaluator_audio_returns_dict():
    evaluator = MultimodalEvaluator()
    clean = [np.sin(np.linspace(0, 4 * np.pi, 1000))]
    proc = [np.sin(np.linspace(0, 4 * np.pi, 1000)) + 0.01 * np.random.randn(1000)]
    result = evaluator.evaluate_audio(clean, proc)
    assert "snr" in result
    assert "stoi_like" in result


def test_evaluator_video_returns_dict():
    evaluator = MultimodalEvaluator()
    frames = np.stack([np.random.randint(0, 255, size=(16, 16, 3), dtype=np.uint8).astype(np.float64) for _ in range(4)])
    result = evaluator.evaluate_video(frames, frames)
    assert "psnr" in result
    assert "ssim" in result
    assert "temporal_consistency" in result
