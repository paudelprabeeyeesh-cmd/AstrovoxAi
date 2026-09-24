import numpy as np

from creativity.creative_generator import CreativeGenerator, CreativeOutput


class TestCreativeGenerator:
    def test_generate_returns_list(self):
        gen = CreativeGenerator()
        outputs = gen.generate("create a novel app")
        assert isinstance(outputs, list)
        assert all(isinstance(o, CreativeOutput) for o in outputs)

    def test_generate_output_count(self):
        gen = CreativeGenerator()
        outputs = gen.generate("design a game", n=5)
        assert len(outputs) == 5

    def test_outputs_sorted_by_combined_score(self):
        gen = CreativeGenerator()
        outputs = gen.generate("build a bridge", n=4)
        scores = [o.combined_score for o in outputs]
        assert scores == sorted(scores, reverse=True)

    def test_scores_in_range(self):
        gen = CreativeGenerator()
        outputs = gen.generate("invent a tool", n=3)
        for o in outputs:
            assert 0.0 <= o.novelty <= 1.0
            assert 0.0 <= o.utility <= 1.0
            assert 0.0 <= o.surprise <= 1.0
            assert 0.0 <= o.combined_score <= 1.0

    def test_combined_score_formula(self):
        gen = CreativeGenerator(novelty_weight=0.5, utility_weight=0.3, surprise_weight=0.2)
        outputs = gen.generate("plan a party", n=3)
        for o in outputs:
            expected = 0.5 * o.novelty + 0.3 * o.utility + 0.2 * o.surprise
            assert abs(o.combined_score - expected) < 1e-6

    def test_content_contains_prompt(self):
        gen = CreativeGenerator()
        outputs = gen.generate("write a story", n=2)
        for o in outputs:
            assert "write a story" in o.content

    def test_history_updated(self):
        gen = CreativeGenerator()
        gen.history = ["sample"]
        gen.generate("paint a mural", n=2)
        assert len(gen.history) == 3

    def test_history_capped(self):
        gen = CreativeGenerator()
        for _ in range(120):
            gen.generate("sing a song", n=1)
        assert len(gen.history) <= 100

    def test_novelty_decreases_with_repeats(self):
        gen = CreativeGenerator()
        gen.history = ["this is a sample text for testing novelty"]
        first = gen.generate("test content", n=1)
        repeat = gen.generate("test content", n=1)
        assert repeat[0].novelty <= first[0].novelty

    def test_utility_length_score(self):
        gen = CreativeGenerator()
        outputs = gen.generate("run a marathon", n=2)
        for o in outputs:
            assert 0.0 <= o.utility <= 1.0

    def test_surprise_low_for_short(self):
        gen = CreativeGenerator()
        outputs = gen.generate("", n=1)
        assert outputs[0].surprise == 0.0

    def test_domain_context(self):
        gen = CreativeGenerator()
        outputs = gen.generate("compose music", n=2, domain_context=["jazz", "blues"])
        for o in outputs:
            assert "compose music" in o.content

    def test_combine_max_novelty(self):
        gen = CreativeGenerator()
        outputs = gen.generate("design a device", n=4)
        combined = gen.combine_outputs(outputs, strategy="max_novelty")
        assert combined.novelty == max(o.novelty for o in outputs)

    def test_combine_max_utility(self):
        gen = CreativeGenerator()
        outputs = gen.generate("write a poem", n=4)
        combined = gen.combine_outputs(outputs, strategy="max_utility")
        assert combined.utility == max(o.utility for o in outputs)

    def test_combine_pareto(self):
        gen = CreativeGenerator()
        outputs = gen.generate("build a network", n=4)
        combined = gen.combine_outputs(outputs, strategy="pareto")
        assert combined.combined_score == max(o.combined_score for o in outputs)

    def test_combine_empty(self):
        gen = CreativeGenerator()
        combined = gen.combine_outputs([], strategy="pareto")
        assert combined.content == ""
        assert combined.novelty == 0.0
        assert combined.utility == 0.0
        assert combined.surprise == 0.0

    def test_combine_unknown_strategy(self):
        gen = CreativeGenerator()
        outputs = gen.generate("learn to code", n=3)
        combined = gen.combine_outputs(outputs, strategy="unknown")
        assert combined.content == outputs[0].content
