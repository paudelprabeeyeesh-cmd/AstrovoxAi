import numpy as np
import pytest
import sys
import os
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from cognitive_architecture.emotional_processing import (
    EmotionRecognizer,
    AffectiveState,
    EmotionalProcessingSystem,
    EmotionState,
    EmotionalStimulus,
)


class TestEmotionState:
    def test_to_vector(self):
        state = EmotionState(valence=0.5, arousal=0.8, dominance=0.3, label="joy")
        vec = state.to_vector()
        assert vec.shape == (3,)
        assert vec[0] == pytest.approx(0.5)
        assert vec[1] == pytest.approx(0.8)

    def test_decay_reduces_intensity(self):
        state = EmotionState(valence=0.5, arousal=0.8, dominance=0.3, label="joy", intensity=1.0)
        state.decay(rate=0.5)
        assert state.intensity < 1.0


class TestEmotionRecognizer:
    def test_recognize_neutral_default(self):
        rec = EmotionRecognizer(feature_dim=4)
        stim = EmotionalStimulus(content="test", valence=0.0, arousal=0.0, dominance=0.0, confidence=1.0)
        state = rec.recognize(stim)
        assert isinstance(state, EmotionState)

    def test_recognize_high_valence_arousal(self):
        rec = EmotionRecognizer(feature_dim=4)
        stim = EmotionalStimulus(content="happy", valence=0.9, arousal=0.9, dominance=0.5, confidence=1.0)
        state = rec.recognize(stim)
        assert state.valence > 0.0

    def test_recognize_low_valence_high_arousal(self):
        rec = EmotionRecognizer(feature_dim=4)
        stim = EmotionalStimulus(content="angry", valence=-0.9, arousal=0.9, dominance=0.5, confidence=1.0)
        state = rec.recognize(stim)
        assert state.label == "anger"

    def test_train_step_returns_loss(self):
        rec = EmotionRecognizer(feature_dim=4)
        features = np.random.randn(4)
        loss = rec.train_step(features, target_valence=0.5, target_arousal=0.5, target_dominance=0.5)
        assert isinstance(loss, float)
        assert loss >= 0
        assert rec._trained

    def test_extract_features_from_string(self):
        rec = EmotionRecognizer(feature_dim=8)
        features = rec.extract_features("hello")
        assert features.shape == (8,)

    def test_extract_features_from_dict(self):
        rec = EmotionRecognizer(feature_dim=8)
        features = rec.extract_features({"value": 0.7, "intensity": 0.9})
        assert features.shape == (8,)


class TestAffectiveState:
    def test_update_creates_state(self):
        state = AffectiveState()
        rec = EmotionRecognizer(feature_dim=4)
        stim = EmotionalStimulus(content="x", valence=0.5, arousal=0.5, dominance=0.5, confidence=1.0)
        result = state.update(stim, rec)
        assert state.current_state is not None
        assert result.label is not None

    def test_affective_bias_empty(self):
        state = AffectiveState()
        bias = state.get_affective_bias()
        assert np.all(bias == 0.0)

    def test_affective_bias_with_state(self):
        state = AffectiveState()
        rec = EmotionRecognizer(feature_dim=4)
        stim = EmotionalStimulus(content="x", valence=0.8, arousal=0.8, dominance=0.8, confidence=1.0)
        state.update(stim, rec)
        bias = state.get_affective_bias()
        assert np.any(bias != 0.0)

    def test_history(self):
        state = AffectiveState()
        rec = EmotionRecognizer(feature_dim=4)
        stim = EmotionalStimulus(content="x", valence=0.5, arousal=0.5, dominance=0.5, confidence=1.0)
        state.update(stim, rec)
        history = state.get_history()
        assert len(history) == 1
        assert "valence" in history[0]


class TestEmotionalProcessingSystem:
    def test_process_stimulus(self):
        eps = EmotionalProcessingSystem(feature_dim=4)
        result = eps.process_stimulus("happy", 0.8, 0.6, 0.5, confidence=0.9)
        assert isinstance(result, EmotionState)

    def test_emotional_profile(self):
        eps = EmotionalProcessingSystem(feature_dim=4)
        eps.process_stimulus("test", 0.5, 0.5, 0.5)
        profile = eps.get_emotional_profile()
        assert "current_emotion" in profile
        assert "valence" in profile

    def test_profile_no_data(self):
        eps = EmotionalProcessingSystem()
        profile = eps.get_emotional_profile()
        assert profile["status"] == "no_data"
