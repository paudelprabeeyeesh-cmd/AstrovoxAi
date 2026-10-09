"""
Tests for product_polish.feature_toggle

Uses only stdlib.
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from product_polish.feature_toggle import FeatureToggle, FeatureToggleStore  # noqa: E402


@pytest.fixture()
def store():
    return FeatureToggleStore()


class TestFeatureToggleDataclass:
    def test_defaults(self):
        t = FeatureToggle(key="flag_a", enabled=True)
        assert t.key == "flag_a"
        assert t.enabled is True
        assert t.environment == "default"
        assert t.description == ""
        assert t.updated_at != ""

    def test_updated_at_iso_format(self):
        t = FeatureToggle(key="flag_b", enabled=False)
        assert "T" in t.updated_at

    def test_custom_environment(self):
        t = FeatureToggle(key="flag_c", enabled=True, environment="staging")
        assert t.environment == "staging"

    def test_custom_description(self):
        t = FeatureToggle(key="flag_d", enabled=False, description="test desc")
        assert t.description == "test desc"

    def test_to_dict_keys(self):
        t = FeatureToggle(key="flag_e", enabled=True)
        d = t.to_dict()
        assert set(d.keys()) == {"key", "enabled", "environment", "description", "updated_at"}


class TestFeatureToggleStoreSet:
    def test_set_returns_toggle(self, store):
        t = store.set("new_flag", True)
        assert isinstance(t, FeatureToggle)

    def test_set_enabled_true(self, store):
        t = store.set("flag_a", True)
        assert t.enabled is True

    def test_set_enabled_false(self, store):
        t = store.set("flag_b", False)
        assert t.enabled is False

    def test_set_sets_description(self, store):
        t = store.set("flag_c", True, description="controls dark mode")
        assert t.description == "controls dark mode"

    def test_set_overwrites_existing(self, store):
        store.set("flag_d", True)
        t = store.set("flag_d", False)
        assert t.enabled is False


class TestFeatureToggleStoreGet:
    def test_get_existing(self, store):
        store.set("flag_a", True)
        t = store.get("flag_a")
        assert t is not None
        assert t.enabled is True

    def test_get_missing_returns_none(self, store):
        assert store.get("missing") is None

    def test_get_environment_match(self, store):
        store.set("flag_a", True, environment="staging")
        t = store.get("flag_a", environment="staging")
        assert t is not None
        assert t.enabled is True

    def test_get_environment_mismatch(self, store):
        store.set("flag_a", True, environment="staging")
        t = store.get("flag_a", environment="production")
        assert t is None


class TestFeatureToggleStoreIsEnabled:
    def test_is_enabled_true(self, store):
        store.set("flag_a", True)
        assert store.is_enabled("flag_a") is True

    def test_is_enabled_false(self, store):
        store.set("flag_b", False)
        assert store.is_enabled("flag_b") is False

    def test_is_enabled_default_when_missing(self, store):
        assert store.is_enabled("missing", default=True) is True

    def test_is_enabled_default_false_when_missing(self, store):
        assert store.is_enabled("missing", default=False) is False


class TestFeatureToggleStoreList:
    def test_list_empty(self, store):
        assert store.list_toggles() == []

    def test_list_after_set(self, store):
        store.set("flag_a", True)
        assert len(store.list_toggles()) == 1

    def test_list_filter_by_environment(self, store):
        store.set("flag_a", True, environment="staging")
        store.set("flag_b", False, environment="production")
        toggles = store.list_toggles(environment="staging")
        assert len(toggles) == 1
        assert toggles[0].key == "flag_a"

    def test_list_sorted_by_key(self, store):
        store.set("b", True)
        store.set("a", False)
        keys = [t.key for t in store.list_toggles()]
        assert keys == sorted(keys)


class TestFeatureToggleStoreDelete:
    def test_delete_existing_returns_true(self, store):
        store.set("flag_a", True)
        assert store.delete("flag_a") is True

    def test_delete_removes_from_store(self, store):
        store.set("flag_a", True)
        store.delete("flag_a")
        assert store.get("flag_a") is None

    def test_delete_missing_returns_false(self, store):
        assert store.delete("missing") is False
