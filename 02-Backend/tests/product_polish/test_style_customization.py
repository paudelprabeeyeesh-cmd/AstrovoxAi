from product_polish.style_customization import StyleCustomization, StyleTheme


def test_style_theme_auto_created_at():
    theme = StyleTheme(id="1", name="t")
    assert theme.created_at != ""


def test_style_theme_to_dict():
    theme = StyleTheme(id="1", name="t", description="d", meta={"k": 1})
    d = theme.to_dict()
    assert d["id"] == "1"
    assert d["description"] == "d"


def test_register_and_get_theme():
    sc = StyleCustomization()
    theme = StyleTheme(id="t1", name="Theme 1")
    sc.register_theme(theme)
    assert sc.get_theme("t1") is theme
    assert sc.get_theme("missing") is None


def test_list_themes():
    sc = StyleCustomization()
    sc.register_theme(StyleTheme(id="t1", name="A"))
    sc.register_theme(StyleTheme(id="t2", name="B"))
    assert len(sc.list_themes()) == 2


def test_set_and_get_active():
    sc = StyleCustomization()
    sc.set_active("button", {"color": "blue"})
    assert sc.get_active("button") == {"color": "blue"}


def test_get_active_missing_component_empty():
    sc = StyleCustomization()
    assert sc.get_active("missing") == {}


def test_set_and_get_override():
    sc = StyleCustomization()
    sc.set_override("font", "Arial")
    assert sc.get_override("font") == "Arial"


def test_get_override_missing_key_none():
    sc = StyleCustomization()
    assert sc.get_override("missing") is None


def test_get_summary():
    sc = StyleCustomization()
    sc.register_theme(StyleTheme(id="t1", name="A"))
    sc.set_active("button", {"color": "blue"})
    sc.set_override("font", "Arial")
    summary = sc.get_summary()
    assert summary["themes"] == 1
    assert summary["active_styles"]["button"] == {"color": "blue"}
    assert summary["overrides"]["font"] == "Arial"


def test_reset_active():
    sc = StyleCustomization()
    sc.set_active("button", {"color": "blue"})
    sc.reset_active("button")
    assert sc.get_active("button") == {}
