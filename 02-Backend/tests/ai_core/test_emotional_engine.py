from ai_core.emotional_engine import EmotionalEngine, EmotionRecognizer, EmpathyModel, EmotionalStimulus, EmotionState


def test_emotion_recognizer_string():
    rec = EmotionRecognizer(feature_dim=16)
    stim = EmotionalStimulus(content="great", valence=0.8, arousal=0.5, dominance=0.3, confidence=1.0)
    state = rec.recognize(stim)
    assert state.label in {"joy", "contentment", "neutral", "surprise", "anger", "sadness", "fear"}
    assert -1.0 <= state.valence <= 1.0


def test_empathy_alignment():
    empathy = EmpathyModel()
    target = EmotionState(valence=0.8, arousal=0.5, dominance=0.3, label="joy")
    aligned = empathy.align(target)
    assert aligned.shape == (3,)


def test_emotional_contagion():
    engine = EmotionalEngine()
    engine.process_stimulus("happy", valence=0.9, arousal=0.7, dominance=0.4, confidence=1.0)
    source = engine.current_state
    other = engine.empathy.emotional_contagion(source, engine.current_state, strength=0.3)
    assert other is not None
    assert -1.0 <= other.valence <= 1.0


def test_emotional_engine_profile():
    engine = EmotionalEngine()
    engine.process_stimulus("exciting", valence=0.7, arousal=0.9, dominance=0.2, confidence=0.8)
    profile = engine.get_emotional_profile()
    assert "current_emotion" in profile
    assert "valence" in profile
    assert "intensity" in profile


def test_emotional_stimulus_creation():
    stim = EmotionalStimulus(content="test", valence=0.5, arousal=0.5, dominance=0.5)
    assert stim.confidence == 1.0
    assert stim.valence == 0.5
