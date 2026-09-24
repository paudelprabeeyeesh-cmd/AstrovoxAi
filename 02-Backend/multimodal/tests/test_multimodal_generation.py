import numpy as np
import pytest

from multimodal.multimodal_generation import (
    TextToImageGenerator,
    TextToSpeechSynthesizer,
    TextToVideoGenerator,
    GenerationConfig,
)


def test_text_to_image_generate_shape():
    gen = TextToImageGenerator(image_size=64, latent_dim=128)
    config = GenerationConfig(text="a red car", modality="image", num_steps=5)
    image = gen.generate(config)
    assert image.shape == (64, 64, 3)
    assert image.dtype == np.uint8
    assert np.all(image >= 0) and np.all(image <= 255)


def test_text_to_image_deterministic_with_seed():
    gen = TextToImageGenerator(image_size=32, latent_dim=64)
    config = GenerationConfig(text="cat", modality="image", seed=123, num_steps=3)
    img1 = gen.generate(config)
    img2 = gen.generate(config)
    np.testing.assert_array_equal(img1, img2)


def test_text_to_image_different_seeds_differ():
    gen = TextToImageGenerator(image_size=32, latent_dim=64)
    config1 = GenerationConfig(text="cat", modality="image", seed=1, num_steps=3)
    config2 = GenerationConfig(text="cat", modality="image", seed=2, num_steps=3)
    img1 = gen.generate(config1)
    img2 = gen.generate(config2)
    assert not np.array_equal(img1, img2)


def test_text_to_speech_synthesize_shape():
    synth = TextToSpeechSynthesizer(sample_rate=22050)
    waveform = synth.synthesize("hello world")
    assert len(waveform) > 0
    assert abs(np.max(np.abs(waveform)) - 1.0) < 1e-6


def test_text_to_speech_different_texts_differ():
    synth = TextToSpeechSynthesizer()
    w1 = synth.synthesize("hello")
    w2 = synth.synthesize("world")
    assert len(w1) != len(w2) or not np.array_equal(w1, w2)


def test_text_to_speech_speed_changes_length():
    synth = TextToSpeechSynthesizer()
    w1 = synth.synthesize("test", speed=1.0)
    w2 = synth.synthesize("test", speed=2.0)
    assert len(w1) > len(w2)


def test_text_to_video_generate_shape():
    gen = TextToVideoGenerator(num_frames=8, frame_size=32, latent_dim=64)
    frames = gen.generate("a dancing cat", num_steps=4, fps=8)
    assert frames.shape == (8, 32, 32, 3)
    assert frames.dtype == np.uint8


def test_text_to_video_different_texts_differ():
    gen = TextToVideoGenerator(num_frames=4, frame_size=16, latent_dim=32)
    f1 = gen.generate("sunset", num_steps=2)
    f2 = gen.generate("sunrise", num_steps=2)
    assert f1.shape == f2.shape
    assert not np.array_equal(f1, f2)


def test_generation_config_defaults():
    config = GenerationConfig(text="test", modality="text")
    assert config.num_steps == 10
    assert config.guidance_scale == 7.5
    assert config.seed is None
