from datetime import datetime

import pytest

from threat_intelligence.indicator_manager import Indicator, IndicatorManager


def test_add_and_get():
    manager = IndicatorManager()
    indicator = Indicator(value="1.2.3.4", type="ip", confidence=0.9)
    manager.add(indicator)
    assert manager.get("ip", "1.2.3.4") is indicator
    assert manager.get("ip", "1.2.3.4").confidence == 0.9


def test_add_merges_on_same_key():
    manager = IndicatorManager()
    first = Indicator(value="example.com", type="domain", confidence=0.6, tags=["phish"])
    second = Indicator(value="example.com", type="domain", confidence=0.8, tags=["malware"])
    manager.add(first)
    manager.add(second)
    stored = manager.get("domain", "example.com")
    assert stored.confidence == 0.8
    assert sorted(stored.tags) == ["malware", "phish"]


def test_remove():
    manager = IndicatorManager()
    manager.add(Indicator(value="abc", type="hash"))
    manager.remove("hash", "abc")
    assert manager.get("hash", "abc") is None
    manager.remove("hash", "missing")


def test_list_and_filters():
    manager = IndicatorManager()
    manager.add(Indicator(value="1.2.3.4", type="ip", confidence=0.5))
    manager.add(Indicator(value="5.6.7.8", type="ip", confidence=0.9))
    manager.add(Indicator(value="evil.com", type="domain", confidence=0.7, tags=["apt"]))
    assert len(manager) == 3
    assert len(manager.filter_by_type("ip")) == 2
    assert len(manager.filter_by_tag("apt")) == 1
    assert len(manager.filter_by_confidence(0.8)) == 1


def test_invalid_indicator():
    with pytest.raises(ValueError):
        Indicator(value="", type="ip")
    with pytest.raises(ValueError):
        Indicator(value="1.2.3.4", type="", confidence=2.0)


def test_list_all():
    manager = IndicatorManager()
    manager.add(Indicator(value="c.com", type="domain"))
    manager.add(Indicator(value="a.com", type="domain"))
    manager.add(Indicator(value="1.1.1.1", type="ip"))
    ordered = manager.list_all()
    assert [i.value for i in ordered] == ["1.1.1.1", "a.com", "c.com"]


def test_add_updates_source():
    manager = IndicatorManager()
    first = Indicator(value="1.1.1.1", type="ip", confidence=0.5, source="feed-a")
    second = Indicator(value="1.1.1.1", type="ip", confidence=0.8, source="feed-b")
    manager.add(first)
    manager.add(second)
    assert manager.get("ip", "1.1.1.1").source == "feed-b"


def test_add_case_insensitive():
    manager = IndicatorManager()
    manager.add(Indicator(value="EXAMPLE.COM", type="Domain", confidence=0.5))
    assert manager.get("domain", "example.com") is not None
    assert manager.get("DOMAIN", "EXAMPLE.COM") is not None


def test_filter_by_type_case_insensitive():
    manager = IndicatorManager()
    manager.add(Indicator(value="1.1.1.1", type="IPv4", confidence=0.5))
    assert len(manager.filter_by_type("ip")) == 1
    assert len(manager.filter_by_type("IPV4")) == 1


def test_filter_by_tag_case_insensitive():
    manager = IndicatorManager()
    manager.add(Indicator(value="1.1.1.1", type="ip", confidence=0.5, tags=["APT"]))
    assert len(manager.filter_by_tag("apt")) == 1


def test_filter_by_confidence_threshold():
    manager = IndicatorManager()
    manager.add(Indicator(value="1.1.1.1", type="ip", confidence=0.4))
    manager.add(Indicator(value="2.2.2.2", type="ip", confidence=0.6))
    manager.add(Indicator(value="3.3.3.3", type="ip", confidence=0.8))
    assert len(manager.filter_by_confidence(0.6)) == 2
