
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
