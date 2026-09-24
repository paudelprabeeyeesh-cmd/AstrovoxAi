import pytest

from threat_intelligence.ioc_matcher import IOCMatcher, Match
from threat_intelligence.indicator_manager import Indicator, IndicatorManager


@pytest.fixture
def manager():
    m = IndicatorManager()
    m.add(Indicator(value="1.2.3.4", type="ip", confidence=0.9))
    m.add(Indicator(value="malicious.com", type="domain", confidence=0.8))
    m.add(Indicator(value="d41d8cd98f00b204e9800998ecf8427e", type="hash", confidence=0.7))
    return m


def test_match_text_linked(manager):
    matcher = IOCMatcher(manager)
    text = "Contact 1.2.3.4 or malicious.com. Hash d41d8cd98f00b204e9800998ecf8427e"
    matches = matcher.match_text(text)
    types = [m.type for m in matches]
    assert "ip" in types
    assert "domain" in types
    assert "hash" in types
    assert all(m.indicator is not None for m in matches)


def test_match_values(manager):
    matcher = IOCMatcher(manager)
    matches = matcher.match_values(["1.2.3.4", "unknown", "malicious.com"])
    assert len(matches) == 2
    assert matches[0].indicator is not None
    assert matches[1].indicator is not None


def test_match_by_type(manager):
    matcher = IOCMatcher(manager)
    matches = matcher.match_by_type("1.2.3.4 and 8.8.8.8", "ip")
    assert len(matches) == 2
    assert matches[0].indicator is not None
    assert matches[1].indicator is None


def test_count_matches(manager):
    matcher = IOCMatcher(manager)
    counts = matcher.count_matches("1.2.3.4 malicious.com 1.2.3.4")
    assert counts["ip"] == 2
    assert counts["domain"] == 1


def test_deduplicate_overlap():
    matcher = IOCMatcher(IndicatorManager())
    matches = [
        Match("1.2.3.4", "ip", None, 0, 7),
        Match("2.3.4", "ip", None, 1, 7),
    ]
    deduped = matcher.match_text("1.2.3.4")
    assert len(deduped) == 1


def test_match_text_empty(manager):
    matcher = IOCMatcher(manager)
    assert matcher.match_text("") == []


def test_match_values_empty(manager):
    matcher = IOCMatcher(manager)
    assert matcher.match_values([]) == []


def test_match_by_type_empty(manager):
    matcher = IOCMatcher(manager)
    assert matcher.match_by_type("", "ip") == []


def test_match_by_type_unknown(manager):
    matcher = IOCMatcher(manager)
    assert matcher.match_by_type("1.1.1.1", "url") == []


def test_count_matches_empty(manager):
    matcher = IOCMatcher(manager)
    assert matcher.count_matches("") == {}


def test_match_frozen():
    match = Match("1.1.1.1", "ip", None, 0, 7)
    with pytest.raises(Exception):
        match.value = "2.2.2.2"
