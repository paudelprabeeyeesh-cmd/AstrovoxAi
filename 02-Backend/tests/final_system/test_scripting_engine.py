from final_system.scripting_engine import Script, ScriptingEngine


def test_register_and_run():
    engine = ScriptingEngine()
    engine.register(Script(name="s1", source="result = 1 + 2"))
    result = engine.run("s1")
    assert result.success is True
    assert result.output == 3


def test_missing_script():
    engine = ScriptingEngine()
    result = engine.run("missing")
    assert result.success is False
    assert "not found" in result.error


def test_run_with_context():
    engine = ScriptingEngine()
    engine.register(Script(name="s2", source="result = x * 2"))
    result = engine.run("s2", context={"x": 5})
    assert result.success is True
    assert result.output == 10


def test_list_scripts():
    engine = ScriptingEngine()
    engine.register(Script(name="a"))
    engine.register(Script(name="b"))
    assert set(engine.list_scripts()) == {"a", "b"}


def test_result_stored():
    engine = ScriptingEngine()
    engine.register(Script(name="s", source="result = 7"))
    engine.run("s")
    stored = engine.result("s")
    assert stored is not None
    assert stored.output == 7
