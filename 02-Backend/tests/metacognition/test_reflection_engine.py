from metacognition.reflection_engine import ReflectionEngine, Reflection, ReflectionReport


def test_record_feedback():
    engine = ReflectionEngine()
    engine.record_feedback("key1", "Good job")
    assert "key1" in engine.feedback_patterns


def test_reflect():
    engine = ReflectionEngine()
    ref = engine.reflect("key1", 0.8, "Good job")
    assert ref.score == 0.8
    assert ref.key == "key1"
    assert "key1" in engine.reflections
    assert "key1" in engine.score_history


def test_get_score_trend_insufficient():
    engine = ReflectionEngine()
    trend = engine.get_score_trend("key1")
    assert trend == 0.0


def test_get_score_trend():
    engine = ReflectionEngine()
    engine.reflect("key1", 0.5, "test")
    engine.reflect("key1", 0.8, "test")
    trend = engine.get_score_trend("key1")
    assert trend > 0.0


def test_improvement_rate():
    engine = ReflectionEngine()
    engine.reflect("key1", 0.5, "test")
    engine.reflect("key1", 0.8, "test")
    rate = engine.improvement_rate("key1")
    assert rate > 0.0


def test_improvement_rate_insufficient():
    engine = ReflectionEngine()
    rate = engine.improvement_rate("key1")
    assert rate == 0.0


def test_common_improvements():
    engine = ReflectionEngine()
    engine.reflect("key1", 0.4, "Needs practice")
    engine.reflect("key1", 0.4, "Needs practice")
    common = engine.common_improvements("key1")
    assert "Needs practice" in common


def test_common_improvements_no_reflections():
    engine = ReflectionEngine()
    common = engine.common_improvements("key1")
    assert common == []


def test_generate_report_empty():
    engine = ReflectionEngine()
    report = engine.generate_report("key1")
    assert report.avg_score == 0.0
    assert report.total_improvements == 0


def test_generate_report():
    engine = ReflectionEngine()
    engine.reflect("key1", 0.6, "Needs practice")
    engine.reflect("key1", 0.8, "Good job")
    report = engine.generate_report("key1")
    assert report.avg_score == 0.7
    assert report.total_improvements > 0
    assert len(report.reflections) == 2


def test_reflection_confidence():
    engine = ReflectionEngine()
    for i in range(5):
        engine.reflect("key1", 0.7, "test")
    ref = engine.reflect("key1", 0.8, "test")
    assert ref.confidence >= 0.5


def test_reflect_history_limit():
    engine = ReflectionEngine(history_size=5)
    for i in range(10):
        engine.reflect("key1", float(i) / 10.0, "test")
    assert len(engine.reflections["key1"]) == 5
    assert len(engine.score_history["key1"]) == 5


def test_identify_improvements_low_score():
    engine = ReflectionEngine()
    improvements = engine._identify_improvements("key1", 0.2)
    assert "Low performance" in improvements
    assert "Needs practice" in improvements


def test_identify_improvements_high_score():
    engine = ReflectionEngine()
    improvements = engine._identify_improvements("key1", 0.8)
    assert "Good job" in improvements


def test_identify_improvements_feedback_error():
    engine = ReflectionEngine()
    engine.record_feedback("key1", "There was an error")
    improvements = engine._identify_improvements("key1", 0.5)
    assert "Reduce errors" in improvements


def test_identify_improvements_feedback_slow():
    engine = ReflectionEngine()
    engine.record_feedback("key1", "It was too slow")
    improvements = engine._identify_improvements("key1", 0.5)
    assert "Increase speed" in improvements


def test_identify_improvements_feedback_incomplete():
    engine = ReflectionEngine()
    engine.record_feedback("key1", "The result was incomplete")
    improvements = engine._identify_improvements("key1", 0.5)
    assert "Improve completeness" in improvements


def test_common_improvements_top_k():
    engine = ReflectionEngine()
    for _ in range(3):
        engine.reflect("key1", 0.4, "Needs practice")
    for _ in range(2):
        engine.reflect("key1", 0.4, "Low performance")
    common = engine.common_improvements("key1", top_k=1)
    assert len(common) <= 1


def test_generate_report_strengths_and_weaknesses():
    engine = ReflectionEngine()
    for _ in range(4):
        engine.reflect("key1", 0.4, "Needs practice")
    for _ in range(2):
        engine.reflect("key1", 0.4, "Low performance")
    report = engine.generate_report("key1")
    assert len(report.reflections) == 6
    assert report.total_improvements > 0


def test_multiple_keys_isolated():
    engine = ReflectionEngine()
    engine.reflect("key1", 0.8, "test")
    engine.reflect("key2", 0.5, "test")
    trend1 = engine.get_score_trend("key1")
    trend2 = engine.get_score_trend("key2")
    assert trend1 > 0.0
    assert trend2 == 0.0
