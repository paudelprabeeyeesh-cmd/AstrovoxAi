"""
Tests for product_polish.style_customization

Uses only stdlib.
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from product_polish.style_customization import (  # noqa: E402
    StyleCustomization,
    StyleTheme,
)


@pytest.fixture()
def sc():
    return StyleCustomization()


class TestStyleThemeDataclass:
    def test_default_created_at_set(self):
        t = StyleTheme(id="t1", name="Dark")
        assert t.created_at != ""

    def test_default_description_empty(self):
        t = StyleTheme(id="t1", name="Dark")
        assert t.description == ""

    def test_default_meta_empty(self):
        t = StyleTheme(id="t1", name="Dark")
        assert t.meta == {}

    def test_to_dict_keys(self):
        t = StyleTheme(id="t1", name="Dark")
        d = t.to_dict()
        for key in ("id", "name", "description", "meta", "created_at"):
            assert key in d

    def test_custom_created_at_preserved(self):
        ts = "2024-01-01T00:00:00+00:00"
        t = StyleTheme(id="t1", name="Dark", created_at=ts)
        assert t.created_at == ts

    def test_meta_stored(self):
        t = StyleTheme(id="t1", name="Dark", meta={"color": "#000"})
        assert t.meta["color"] == "#000"

    def test_description_stored(self):
        t = StyleTheme(id="t1", name="Dark", description="Night mode")
        assert t.description == "Night mode"


class TestStyleCustomizationInit:
    def test_initial_themes_empty(self, sc):
        assert sc.list_themes() == []

    def test_initial_active_empty(self, sc):
        assert sc.get_summary()["active_styles"] == {}

    def test_initial_overrides_empty(self, sc):
        assert sc.get_summary()["overrides"] == {}


class TestRegisterTheme:
    def test_register_adds_to_list(self, sc):
        t = StyleTheme(id="dark", name="Dark Theme")
        sc.register_theme(t)
        themes = sc.list_themes()
        assert len(themes) == 1

    def test_register_get_returns_theme(self, sc):
        t = StyleTheme(id="dark", name="Dark Theme")
        sc.register_theme(t)
        got = sc.get_theme("dark")
        assert got is not None
        assert got.name == "Dark Theme"

    def test_get_missing_returns_none(self, sc):
        assert sc.get_theme("missing") is None

    def test_register_multiple(self, sc):
        sc.register_theme(StyleTheme(id="d", name="Dark"))
        sc.register_theme(StyleTheme(id="l", name="Light"))
        assert len(sc.list_themes()) == 2

    def test_register_overwrites(self, sc):
        t1 = StyleTheme(id="d", name="Old")
        t2 = StyleTheme(id="d", name="New")
        sc.register_theme(t1)
        sc.register_theme(t2)
        assert sc.get_theme("d").name == "New"


class TestActiveStyles:
    def test_set_then_get_active(self, sc):
        sc.set_active("btn", {"bg": "blue"})
        assert sc.get_active("btn") == {"bg": "blue"}

    def test_get_missing_returns_empty_dict(self, sc):
        assert sc.get_active("missing") == {}

    def test_set_returns_independent_copies(self, sc):
        sc.set_active("btn", {"bg": "blue"})
        sc.set_active("btn", {"bg": "red"})
        assert sc.get_active("btn") == {"bg": "red"}

    def test_set_active_multiple_components(self, sc):
        sc.set_active("btn", {"bg": "blue"})
        sc.set_active("card", {"shadow": "md"})
        assert sc.get_active("btn") == {"bg": "blue"}
        assert sc.get_active("card") == {"shadow": "md"}

    def test_reset_active_clears(self, sc):
        sc.set_active("btn", {"bg": "blue"})
        sc.reset_active("btn")
        assert sc.get_active("btn") == {}


class TestGlobalOverrides:
    def test_set_then_get_override(self, sc):
        sc.set_override("primary_color", "#ff0")
        assert sc.get_override("primary_color") == "#ff0"

    def test_get_missing_returns_none(self, sc):
        assert sc.get_override("missing") is None

    def test_override_overwrites(self, sc):
        sc.set_override("k", "v1")
        sc.set_override("k", "v2")
        assert sc.get_override("k") == "v2"


class TestSummary:
    def test_summary_has_keys(self, sc):
        s = sc.get_summary()
        assert "themes" in s
        assert "active_styles" in s
        assert "overrides" in s

    def test_summary_empty_themes(self, sc):
        assert sc.get_summary()["themes"] == 0

    def test_summary_after_register(self, sc):
        sc.register_theme(StyleTheme(id="d", name="Dark"))
        assert sc.get_summary()["themes"] == 1

    def test_summary_includes_active_styles(self, sc):
        sc.set_active("btn", {"bg": "blue"})
        assert sc.get_summary()["active_styles"] == {"btn": {"bg": "blue"}}

    def test_summary_includes_overrides(self, sc):
        sc.set_override("k", "v")
        assert sc.get_summary()["overrides"] == {"k": "v"}


class TestThreadSafety:
    def test_concurrent_registers(self, sc):
        import threading
        errors = []
        lock = threading.Lock()
        counter = [0]

        def register_many(prefix):
            for i in range(20):
                try:
                    sc.register_theme(StyleTheme(id=f"t-{prefix}-{i}", name="N"))
                except Exception as e:
                    with lock:
                        errors.append(e)

        threads = [threading.Thread(target=register_many, args=(j,)) for j in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert errors == []
        assert sc.get_summary()["themes"] == 80
