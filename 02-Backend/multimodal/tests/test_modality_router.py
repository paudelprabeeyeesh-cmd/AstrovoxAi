from multimodal.modality_router import ModalityRouter, RoutingDecision


def _make_waveform(n=1600):
    return [float(i % 100) / 100.0 for i in range(n)]


def _make_image(h=32, w=32):
    return [[[int((i * j) % 256) for _ in range(3)] for j in range(w)] for i in range(h)]


def test_routing_decision_dataclass():
    decision = RoutingDecision(
        modality="audio",
        confidence=0.9,
        processor="AudioPipeline",
    )
    assert decision.modality == "audio"
    assert decision.confidence == 0.9
    assert isinstance(decision.metadata, dict)


def test_modality_router_default_init():
    router = ModalityRouter()
    assert router.audio_pipeline is not None
    assert router.vision_pipeline is not None


def test_modality_router_custom_init():
    router = ModalityRouter(sample_rate=44100, n_mfcc=20, feature_dim=128, num_regions=4)
    assert router.audio_pipeline.sample_rate == 44100
    assert router.audio_pipeline.n_mfcc == 20
    assert router.vision_pipeline.feature_dim == 128
    assert router.vision_pipeline.num_regions == 4


def test_route_audio_only():
    router = ModalityRouter()
    waveform = _make_waveform(16000)
    result = router.route(waveform=waveform, sample_rate=16000)
    assert "audio" in result
    from multimodal.audio_pipeline import AudioPipelineResult

    assert isinstance(result["audio"], AudioPipelineResult)


def test_route_vision_only():
    router = ModalityRouter()
    pixels = _make_image(64, 64)
    result = router.route(pixels=pixels)
    assert "vision" in result
    from multimodal.vision_pipeline import VisionPipelineResult

    assert isinstance(result["vision"], VisionPipelineResult)


def test_route_both_modalities():
    router = ModalityRouter()
    waveform = _make_waveform(16000)
    pixels = _make_image(64, 64)
    result = router.route(waveform=waveform, sample_rate=16000, pixels=pixels)
    assert "audio" in result
    assert "vision" in result


def test_route_no_data():
    router = ModalityRouter()
    result = router.route()
    assert result == {}


def test_route_audio_dedicated():
    router = ModalityRouter()
    waveform = _make_waveform(16000)
    result = router.route_audio(waveform, 16000)
    from multimodal.audio_pipeline import AudioPipelineResult

    assert isinstance(result, AudioPipelineResult)


def test_route_vision_dedicated():
    router = ModalityRouter()
    pixels = _make_image(64, 64)
    result = router.route_vision(pixels)
    from multimodal.vision_pipeline import VisionPipelineResult

    assert isinstance(result, VisionPipelineResult)


def test_detect_modality_1d_audio():
    router = ModalityRouter()
    data = [0.0] * 100
    assert router.detect_modality(data) == "audio"


def test_detect_modality_2d_vision():
    router = ModalityRouter()
    data = [[0.0] * 32 for _ in range(32)]
    assert router.detect_modality(data) == "vision"


def test_detect_modality_3d_vision():
    router = ModalityRouter()
    data = [[[0.0] * 3 for _ in range(32)] for _ in range(32)]
    assert router.detect_modality(data) == "vision"


def test_detect_modality_text():
    router = ModalityRouter()
    assert router.detect_modality("hello world") == "text"


def test_detect_modality_unknown():
    router = ModalityRouter()
    assert router.detect_modality([1, 2, 3]) == "audio"


def test_route_audio_transcription_nonempty():
    router = ModalityRouter()
    waveform = _make_waveform(16000)
    result = router.route_audio(waveform, 16000)
    assert len(result.transcription) > 0


def test_route_vision_caption_nonempty():
    router = ModalityRouter()
    pixels = _make_image(64, 64)
    result = router.route_vision(pixels)
    assert len(result.caption) > 0
