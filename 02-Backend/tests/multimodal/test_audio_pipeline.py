from multimodal.audio_pipeline import AudioPipeline, AudioPipelineResult


def _make_waveform(n=1600):
    return [float(i % 100) / 100.0 for i in range(n)]


def test_audio_pipeline_result_dataclass():
    result = AudioPipelineResult(
        features=None,
        transcription="hello",
        snr=20.0,
        pesq=3.0,
    )
    assert result.transcription == "hello"
    assert result.snr == 20.0
    assert result.pesq == 3.0
    assert isinstance(result.metadata, dict)


def test_audio_pipeline_default_init():
    pipeline = AudioPipeline()
    assert pipeline.sample_rate == 16000
    assert pipeline.n_mfcc == 13


def test_audio_pipeline_custom_init():
    pipeline = AudioPipeline(sample_rate=44100, n_mfcc=20)
    assert pipeline.sample_rate == 44100
    assert pipeline.n_mfcc == 20


def test_audio_pipeline_process_returns_result():
    pipeline = AudioPipeline()
    waveform = _make_waveform(16000)
    result = pipeline.process(waveform, 16000)
    assert isinstance(result, AudioPipelineResult)


def test_audio_pipeline_process_features_type():
    pipeline = AudioPipeline()
    waveform = _make_waveform(16000)
    result = pipeline.process(waveform, 16000)
    from multimodal.audio_pipeline import AudioFeatures

    assert isinstance(result.features, AudioFeatures)


def test_audio_pipeline_transcription_is_string():
    pipeline = AudioPipeline()
    waveform = _make_waveform(16000)
    result = pipeline.process(waveform, 16000)
    assert isinstance(result.transcription, str)
    assert len(result.transcription) > 0


def test_audio_pipeline_snr_float():
    pipeline = AudioPipeline()
    waveform = _make_waveform(16000)
    result = pipeline.process(waveform, 16000)
    assert isinstance(result.snr, float)


def test_audio_pipeline_pesq_in_range():
    pipeline = AudioPipeline()
    waveform = _make_waveform(16000)
    result = pipeline.process(waveform, 16000)
    assert 1.0 <= result.pesq <= 4.5


def test_audio_pipeline_metadata_keys():
    pipeline = AudioPipeline()
    waveform = _make_waveform(16000)
    result = pipeline.process(waveform, 16000)
    assert "sample_rate" in result.metadata
    assert "duration" in result.metadata


def test_audio_pipeline_resample_via_process():
    pipeline = AudioPipeline(sample_rate=16000)
    waveform = _make_waveform(8000)
    result = pipeline.process(waveform, 8000)
    assert result.features.sample_rate == 16000


def test_audio_pipeline_accepts_numpy_array():
    try:
        import numpy as np
    except ImportError:
        return
    pipeline = AudioPipeline()
    waveform = np.sin(np.linspace(0, 4 * 3.141592653589793, 16000)).astype(float)
    result = pipeline.process(waveform, 16000)
    assert isinstance(result, AudioPipelineResult)
