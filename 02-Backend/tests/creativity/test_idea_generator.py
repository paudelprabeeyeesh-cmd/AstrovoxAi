from creativity.idea_generator import IdeaGenerator, Idea


class TestIdeaGenerator:
    def test_generate_returns_list(self):
        gen = IdeaGenerator()
        ideas = gen.generate("build a house", n=3)
        assert len(ideas) == 3

    def test_generate_domain(self):
        gen = IdeaGenerator()
        ideas = gen.generate("test", n=2, domain="science")
        assert all(idea.domain == "science" for idea in ideas)

    def test_scores_in_range(self):
        gen = IdeaGenerator()
        ideas = gen.generate("idea", n=2)
        for idea in ideas:
            assert 0.0 <= idea.novelty <= 1.0
            assert 0.0 <= idea.utility <= 1.0
            assert 0.0 <= idea.feasibility <= 1.0

    def test_novelty_increases_with_history(self):
        gen = IdeaGenerator()
        gen.history = ["this is a sample text for testing novelty"]
        ideas = gen.generate("test content", n=1)
        assert ideas[0].novelty >= 0.0

    def test_deterministic_with_seed(self):
        gen_a = IdeaGenerator(seed=42)
        gen_b = IdeaGenerator(seed=42)
        ideas_a = gen_a.generate("prompt", n=2)
        ideas_b = gen_b.generate("prompt", n=2)
        assert [idea.content for idea in ideas_a] == [idea.content for idea in ideas_b]

    def test_empty_prompt(self):
        gen = IdeaGenerator()
        ideas = gen.generate("", n=1)
        assert len(ideas) == 1
