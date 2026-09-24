from creativity.metaphor_engine import MetaphorEngine, Metaphor


class TestMetaphorEngine:
    def test_generate_returns_metaphors(self):
        engine = MetaphorEngine()
        results = engine.generate("thought", n=3)
        assert len(results) == 3
        assert all(isinstance(m, Metaphor) for m in results)

    def test_metaphor_fields(self):
        engine = MetaphorEngine()
        results = engine.generate("knowledge", n=1)
        m = results[0]
        assert m.source
        assert m.target == "knowledge"
        assert m.text
        assert 0.0 <= m.strength <= 1.0
        assert 0.0 <= m.clarity <= 1.0

    def test_domain_filter(self):
        engine = MetaphorEngine()
        results = engine.generate("code", source_domain="technology", n=2)
        tech_sources = engine.domains["technology"]
        assert all(m.source in tech_sources for m in results)

    def test_map_domain(self):
        engine = MetaphorEngine()
        results = engine.map_domain("fear", domain="nature", n=2)
        assert len(results) == 2
        assert all(m.source in engine.domains["nature"] for m in results)

    def test_deterministic_with_seed(self):
        engine_a = MetaphorEngine(seed=9)
        engine_b = MetaphorEngine(seed=9)
        r_a = engine_a.generate("life", n=2)
        r_b = engine_b.generate("life", n=2)
        assert [m.text for m in r_a] == [m.text for m in r_b]
