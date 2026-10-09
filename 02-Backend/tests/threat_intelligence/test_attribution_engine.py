from datetime import datetime

import pytest

from threat_intelligence.attribution_engine import AttributionEngine
from threat_intelligence.indicator_manager import Indicator, IndicatorManager
from threat_intelligence.ioc_matcher import IOCMatcher, Match


@pytest.fixture
def engine():
    manager = IndicatorManager()
    manager.add(Indicator(value="1.2.3.4", type="ip", confidence=0.9))
    manager.add(Indicator(value="d41d8cd98f00b204e9800998ecf8427e", type="hash", confidence=0.7))
    return AttributionEngine(manager)


def test_register_and_get(engine):
    engine.register("APT-X")
    candidate = engine.get("APT-X")
    assert candidate is not None
    assert candidate.actor == "APT-X"
    assert candidate.score == 0.0


def test_link_indicator(engine):
    engine.link_indicator("APT-X", Indicator(value="1.2.3.4", type="ip", confidence=0.9))
    candidate = engine.get("APT-X")
    assert candidate is not None
    assert candidate.score == pytest.approx(9.0)
    assert len(candidate.matched_indicators) == 1


def test_score_from_matches(engine):
    matcher = IOCMatcher(engine.manager)
    matches = matcher.match_text("1.2.3.4 d41d8cd98f00b204e9800998ecf8427e")
    engine.score_from_matches("APT-X", matches)
    candidate = engine.get("APT-X")
    assert candidate is not None
    assert candidate.score == pytest.approx(16.0)


def test_ranked(engine):
    engine.link_indicator("A", Indicator(value="1.2.3.4", type="ip", confidence=0.5))
    engine.link_indicator("B", Indicator(value="1.2.3.4", type="ip", confidence=0.9))
    ranked = engine.ranked()
    assert ranked[0].actor == "B"
    assert ranked[1].actor == "A"


def test_prune_below(engine):
    engine.register("Low")
    engine.link_indicator("Low", Indicator(value="1.2.3.4", type="ip", confidence=0.1))
    removed = engine.prune_below(1.1)
    assert removed == ["Low"]
    assert len(engine) == 0


def test_invalid_candidate():
    with pytest.raises(ValueError):
        AttributionCandidate(actor="")
    with pytest.raises(ValueError):
        AttributionCandidate(actor="APT-X", score=101.0)


def test_link_indicator_duplicate(engine):
    engine.register("APT-X")
    ind = Indicator(value="1.2.3.4", type="ip", confidence=0.9)
    engine.link_indicator("APT-X", ind)
    engine.link_indicator("APT-X", ind)
    candidate = engine.get("APT-X")
    assert candidate is not None
    assert len(candidate.matched_indicators) == 1


def test_score_from_matches_no_indicators(engine):
    engine.register("APT-X")
    engine.score_from_matches("APT-X", [])
    assert engine.get("APT-X").score == 0.0


def test_get_missing_actor(engine):
    assert engine.get("Missing") is None


def test_ranked_equal_scores(engine):
    engine.register("A")
    engine.register("B")
    engine.link_indicator("A", Indicator(value="1.2.3.4", type="ip", confidence=0.5))
    engine.link_indicator("B", Indicator(value="1.2.3.4", type="ip", confidence=0.5))
    ranked = engine.ranked()
    assert [c.actor for c in ranked] == ["A", "B"]


def test_len(engine):
    engine.register("X")
    engine.register("Y")
    assert len(engine) == 2


def test_prune_below_empty(engine):
    assert engine.prune_below(1.0) == []
