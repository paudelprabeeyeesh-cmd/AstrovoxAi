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
