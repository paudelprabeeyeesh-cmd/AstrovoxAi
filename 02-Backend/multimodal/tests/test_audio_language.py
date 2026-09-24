import numpy as np

from multimodal.audio_language import (
    AudioFeatures,
    AudioLanguageModel,
)


def _make_waveform(n=1600):
    return np.sin(np.linspace(0, 4 * np.pi, n)).astype(np.float64)


def test_load_audio_returns_audio_features():
    model = AudioLanguageModel(sample_rate=16000, n_mfcc=13)
    waveform = _make_waveform()
    feats = model.load_audio(waveform, 16000)
    assert isinstance(feats, AudioFeatures)
    assert feats.sample_rate == 16000
    assert feats.mfcc.shape[0] == 13
    assert feats.spectrogram.shape[0] > 0


def test_resample_changes_length():
    model = AudioLanguageModel()
    signal = _make_waveform(100)
    resampled = model._resample(signal, 100, 200)
    assert len(resampled) == 200


def test_normalize_scales_to_one():
    model = AudioLanguageModel()
    waveform = np.array([10.0, -10.0, 5.0, -5.0])
    norm = model._normalize(waveform)
    assert abs(np.max(np.abs(norm)) - 1.0) < 1e-6


def test_compute_spectrogram_shape():
    model = AudioLanguageModel()
    waveform = _make_waveform(1600)
    spec = model._compute_spectrogram(waveform)
    assert spec.ndim == 2
    assert spec.shape[0] > 0


def test_compute_mfcc_shape():
    model = AudioLanguageModel(n_mfcc=13)
    waveform = _make_waveform(1600)
    spec = model._compute_spectrogram(waveform)
    mfcc = model._compute_mfcc(spec)
    assert mfcc.shape[0] == 13
    assert mfcc.shape[1] == spec.shape[1]


def test_mel_filterbank_shape():
    model = AudioLanguageModel()
    fb = model._mel_filterbank(513, 40)
    assert fb.shape == (40, 513)


def test_dct_output_shape():
    model = AudioLanguageModel()
    x = np.random.randn(20)
    d = model._dct(x, 5)
    assert d.shape == (5,)


def test_transcribe_returns_string():
    model = AudioLanguageModel()
    waveform = _make_waveform(16000)
    feats = model.load_audio(waveform, 16000)
    text = model.transcribe(feats)
    assert isinstance(text, str)
    assert len(text) > 0


def test_transcribe_silence_returns_silence():
    model = AudioLanguageModel()
    silence = np.zeros(16000)
    feats = model.load_audio(silence, 16000)
    text = model.transcribe(feats)
    assert text == "[silence]"


def test_answer_audio_question_returns_expected_keys():
    model = AudioLanguageModel()
    waveform = _make_waveform(16000)
    feats = model.load_audio(waveform, 16000)
    result = model.answer_audio_question(feats, "What does the audio say?")
    assert "transcription" in result
    assert "answer" in result
    assert "similarity" in result
    assert "duration" in result
    assert abs(result["duration"] - 1.0) < 0.1


def test_compute_snr_high_for_clean():
    model = AudioLanguageModel()
    clean = np.sin(np.linspace(0, 4 * np.pi, 1000))
    noisy = clean + 0.01 * np.random.randn(1000)
    snr = model.compute_snr(clean, noisy)
    assert snr > 20


def test_compute_pesq_like_range():
    model = AudioLanguageModel()
    clean = np.sin(np.linspace(0, 4 * np.pi, 1000))
    degraded = clean + 0.1 * np.random.randn(1000)
    pesq = model.compute_pesq_like(clean, degraded)
    assert 1.0 <= pesq <= 4.5


def test_text_to_mfcc_embedding_shape():
    model = AudioLanguageModel()
    emb = model._text_to_mfcc_embedding("test")
    assert emb.shape == (13,)
