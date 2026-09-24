from agent_modeling.deception_detector import DeceptionDetector, DeceptionReport, DeceptionSignal, Statement


def test_record_statement():
    detector = DeceptionDetector()
    stmt = Statement(claim="I saw a cat", confidence=0.9, timestamp=1000.0, topic="animals")
    detector.record_statement(stmt)
    assert len(detector.statements) == 1
    assert "animals" in detector.topic_claims


def test_check_consistency_empty():
    detector = DeceptionDetector()
    consistency = detector.check_consistency("animals")
    assert consistency == 1.0


def test_check_consistency_populated():
    detector = DeceptionDetector()
    detector.record_statement(Statement("I saw a cat", 0.9, 1000.0, topic="animals"))
    detector.record_statement(Statement("I saw a cat", 0.9, 1001.0, topic="animals"))
    consistency = detector.check_consistency("animals")
    assert consistency > 0.0


def test_detect_contradictions_none():
    detector = DeceptionDetector()
    detector.record_statement(Statement("I saw a cat", 0.9, 1000.0, topic="animals"))
    detector.record_statement(Statement("I saw a cat", 0.9, 1001.0, topic="animals"))
    signals = detector.detect_contradictions("animals")
    assert len(signals) == 0


def test_detect_contradictions_found():
    detector = DeceptionDetector()
    detector.contradiction_threshold = 0.1
    detector.record_statement(Statement("Apples grow on trees", 0.9, 1000.0, topic="facts"))
    detector.record_statement(Statement("Cats sleep during day", 0.1, 1001.0, topic="facts"))
    signals = detector.detect_contradictions("facts")
    assert len(signals) > 0
    assert signals[0].signal_type == "contradiction"


def test_calculate_risk_score_no_contradictions():
    detector = DeceptionDetector()
    detector.record_statement(Statement("I saw a cat", 0.9, 1000.0, topic="animals"))
    detector.record_statement(Statement("I saw a cat", 0.9, 1001.0, topic="animals"))
    risk = detector.calculate_risk_score("animals")
    assert risk >= 0.0
    assert risk <= 1.0


def test_generate_report():
    detector = DeceptionDetector()
    detector.record_statement(Statement("I saw a cat", 0.9, 1000.0, topic="animals"))
    detector.record_statement(Statement("I saw a dog", 0.1, 1001.0, topic="animals"))
    report = detector.generate_report("animals")
    assert isinstance(report, DeceptionReport)
    assert 0.0 <= report.risk_score <= 1.0


def test_claim_similarity_identical():
    detector = DeceptionDetector()
    sim = detector._claim_similarity("I saw a cat", "I saw a cat")
    assert sim == 1.0


def test_claim_similarity_different():
    detector = DeceptionDetector()
    sim = detector._claim_similarity("I saw a cat", "I saw a dog")
    assert sim < 1.0


def test_claim_similarity_empty():
    detector = DeceptionDetector()
    sim = detector._claim_similarity("", "")
    assert sim == 1.0


def test_history_size_cap():
    detector = DeceptionDetector(history_size=3)
    for i in range(5):
        detector.record_statement(Statement(f"claim{i}", 0.9, float(i), topic="t"))
    assert len(detector.topic_claims["t"]) == 3


def test_check_consistency_single():
    detector = DeceptionDetector()
    detector.record_statement(Statement("I saw a cat", 0.9, 1000.0, topic="animals"))
    assert detector.check_consistency("animals") == 1.0


def test_detect_contradictions_needs_confidence_diff():
    detector = DeceptionDetector(contradiction_threshold=0.5)
    detector.record_statement(Statement("Apples grow on trees", 0.9, 1000.0, topic="facts"))
    detector.record_statement(Statement("Apples grow on trees", 0.91, 1001.0, topic="facts"))
    signals = detector.detect_contradictions("facts")
    assert len(signals) == 0


def test_calculate_risk_score_with_contradictions():
    detector = DeceptionDetector(contradiction_threshold=0.1)
    detector.record_statement(Statement("Apples grow on trees", 0.9, 1000.0, topic="facts"))
    detector.record_statement(Statement("Cats sleep during day", 0.1, 1001.0, topic="facts"))
    risk = detector.calculate_risk_score("facts")
    assert 0.0 <= risk <= 1.0
    assert risk > 0.0


def test_topic_default():
    detector = DeceptionDetector()
    detector.record_statement(Statement("I saw a cat", 0.9, 1000.0))
    assert "__default__" in detector.topic_claims


def test_generate_report_fields():
    detector = DeceptionDetector(contradiction_threshold=0.1)
    detector.record_statement(Statement("Apples grow on trees", 0.9, 1000.0, topic="facts"))
    detector.record_statement(Statement("Cats sleep during day", 0.1, 1001.0, topic="facts"))
    report = detector.generate_report("facts")
    assert isinstance(report, DeceptionReport)
    assert len(report.signals) > 0
    assert report.signals[0].signal_type == "contradiction"
