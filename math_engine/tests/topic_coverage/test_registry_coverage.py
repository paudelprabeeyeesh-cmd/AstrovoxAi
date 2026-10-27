"""Topic coverage test: every registered topic has an honest status."""

from math_engine.registry.loader import load_registry

VALID_STATUSES = {"planned", "scaffolded", "implemented", "tested", "verified", "blocked"}


def test_registry_nonempty():
    reg = load_registry()
    assert reg["count"] > 0
    assert len(reg["topics"]) == reg["count"]


def test_topic_statuses_valid():
    reg = load_registry()
    for t in reg["topics"]:
        assert t["status"] in VALID_STATUSES, f"Bad status for {t['id']}: {t['status']}"
        assert "id" in t and "name" in t and "section" in t


def test_all_sections_present():
    reg = load_registry()
    sections = {t["section"] for t in reg["topics"]}
    assert set(range(1, 20)) <= sections, f"Missing sections: {set(range(1,20)) - sections}"
