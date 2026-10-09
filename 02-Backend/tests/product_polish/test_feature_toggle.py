
from product_polish.feature_toggle import FeatureToggleStore


def test_set_and_get_toggle():
    store = FeatureToggleStore()
    toggle = store.set("dark_mode", True, environment="web", description="Dark theme")
    assert toggle.key == "dark_mode"
    assert toggle.enabled is True
    assert toggle.environment == "web"
    assert toggle.description == "Dark theme"

    fetched = store.get("dark_mode", environment="web")
    assert fetched is not None
    assert fetched.enabled is True


def test_is_enabled_default_true():
    store = FeatureToggleStore()
    store.set("beta", True)
    assert store.is_enabled("beta") is True


def test_is_enabled_default_false_when_missing():
    store = FeatureToggleStore()
    assert store.is_enabled("missing", default=False) is False
    assert store.is_enabled("missing", default=True) is True


def test_list_toggles_environment_filter():
    store = FeatureToggleStore()
    store.set("alpha", True, environment="web")
    store.set("beta", False, environment="mobile")
    toggles = store.list_toggles(environment="web")
    assert len(toggles) == 1
    assert toggles[0].enabled is True


def test_delete_toggle():
    store = FeatureToggleStore()
    store.set("temp", True)
    assert store.delete("temp") is True
    assert store.get("temp") is None
    assert store.delete("temp") is False


def test_environment_fallback_to_default():
    store = FeatureToggleStore()
    store.set("feature_x", True)
    assert store.is_enabled("feature_x", environment="staging") is True


def test_feature_toggle_to_dict():
    store = FeatureToggleStore()
    toggle = store.set("theme", False, environment="mobile", description="Light")
    data = toggle.to_dict()
    assert data["key"] == "theme"
    assert data["enabled"] is False
    assert data["environment"] == "mobile"
    assert "updated_at" in data


def test_set_updates_existing_toggle():
    store = FeatureToggleStore()
    store.set("flag", True, description="first")
    updated = store.set("flag", False, description="second")
    assert updated.enabled is False
    assert updated.description == "second"
    assert store.is_enabled("flag") is False


def test_list_toggles_returns_all_when_no_filter():
    store = FeatureToggleStore()
    store.set("a", True, environment="web")
    store.set("b", False, environment="mobile")
    all_toggles = store.list_toggles()
    assert len(all_toggles) == 2


def test_delete_returns_false_for_missing_key():
    store = FeatureToggleStore()
    assert store.delete("does_not_exist") is False


def test_get_returns_none_for_environment_no_default():
    store = FeatureToggleStore()
    store.set("flag", True, environment="mobile")
    assert store.get("flag", environment="mobile") is not None
    assert store.get("flag", environment="web") is None
