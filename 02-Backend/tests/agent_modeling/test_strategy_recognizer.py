from agent_modeling.strategy_recognizer import StrategyMatch, StrategyRecognizer, StrategySignature


def test_register_strategy():
    recognizer = StrategyRecognizer()
    recognizer.register_strategy("patrol", ["move", "scan", "move"])
    known = recognizer.known_strategies()
    assert len(known) == 1
    assert known[0].strategy_id == "patrol"


def test_observe_sequence_no_match():
    recognizer = StrategyRecognizer()
    recognizer.register_strategy("patrol", ["move", "scan", "move"])
    matches = recognizer.observe_sequence(["grab", "run"])
    assert len(matches) == 0


def test_observe_sequence_match():
    recognizer = StrategyRecognizer()
    recognizer.register_strategy("patrol", ["move", "scan", "move"])
    matches = recognizer.observe_sequence(["move", "scan", "move"])
    assert len(matches) == 1
    assert matches[0].strategy_id == "patrol"
    assert matches[0].confidence == 1.0


def test_recognize_no_strategies():
    recognizer = StrategyRecognizer()
    matches = recognizer.recognize()
    assert matches == []


def test_pattern_frequency():
    recognizer = StrategyRecognizer()
    recognizer.observe_sequence(["move", "scan", "move", "move", "scan", "move"])
    freq = recognizer.pattern_frequency(["move", "scan", "move"])
    assert freq == 2


def test_pattern_frequency_no_match():
    recognizer = StrategyRecognizer()
    recognizer.observe_sequence(["grab", "run"])
    freq = recognizer.pattern_frequency(["move", "scan"])
    assert freq == 0


def test_strategy_transitions():
    recognizer = StrategyRecognizer()
    recognizer.observe_sequence(["move", "scan", "grab", "run"])
    transitions = recognizer.strategy_transitions()
    assert "move" in transitions
    assert "scan" in transitions["move"]


def test_strategy_transitions_empty():
    recognizer = StrategyRecognizer()
    transitions = recognizer.strategy_transitions()
    assert transitions == {}


def test_history_size_cap():
    recognizer = StrategyRecognizer(history_size=5)
    recognizer.observe_sequence(["a", "b", "c", "d", "e", "f"])
    assert len(recognizer.action_sequence) == 5


def test_register_strategy_updates_existing():
    recognizer = StrategyRecognizer()
    recognizer.register_strategy("patrol", ["move", "scan", "move"])
    recognizer.register_strategy("patrol", ["move", "scan", "grab"])
    known = recognizer.known_strategies()
    assert len(known) == 1
    assert known[0].pattern == ["move", "scan", "grab"]


def test_recognize_confidence_exact_match():
    recognizer = StrategyRecognizer()
    recognizer.register_strategy("patrol", ["move", "scan", "move"])
    matches = recognizer.observe_sequence(["grab", "run", "move", "scan", "move"])
    assert len(matches) == 1
    assert matches[0].confidence == 1.0


def test_strategy_transitions_counts():
    recognizer = StrategyRecognizer()
    recognizer.observe_sequence(["move", "scan", "move", "scan"])
    transitions = recognizer.strategy_transitions()
    assert transitions["move"]["scan"] == 2


def test_known_strategies_empty():
    recognizer = StrategyRecognizer()
    assert recognizer.known_strategies() == []


def test_observe_sequence_updates_matches():
    recognizer = StrategyRecognizer()
    recognizer.register_strategy("patrol", ["move", "scan", "move"])
    recognizer.observe_sequence(["grab", "run"])
    assert len(recognizer.matches) == 0
    recognizer.observe_sequence(["move", "scan", "move"])
    assert len(recognizer.matches) == 1
