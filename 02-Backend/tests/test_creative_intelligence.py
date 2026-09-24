from agi_core.creative_intelligence import CreativeIntelligence, Idea


class TestCreativeIntelligence:
    def test_generate_ideas(self):
        ci = CreativeIntelligence()
        ideas = ci.generate_ideas("test problem", "science", n=3)
        assert len(ideas) == 3

    def test_evaluate(self):
        ci = CreativeIntelligence()
        idea = Idea(content="idea", domain="d", novelty=0.8, utility=0.9, feasibility=0.7)
        score = ci.evaluate(idea)
        assert 0.0 <= score <= 1.0

    def test_combine(self):
        ci = CreativeIntelligence()
        ideas = [Idea("a", "d", 0.5, 0.5, 0.5), Idea("b", "d", 0.6, 0.7, 0.4)]
        combined = ci.combine(ideas)
        assert combined is not None

    def test_get_best_idea(self):
        ci = CreativeIntelligence()
        ideas = [Idea("a", "d", 0.3, 0.4, 0.3), Idea("b", "d", 0.9, 0.8, 0.7)]
        best = ci.get_best_idea(ideas)
        assert best.novelty >= 0.8
