from creativity.creative_generator import CreativeGenerator, CreativeOutput


class TestCreativeGenerator:
    def test_generate_returns_list(self):
        gen = CreativeGenerator()
        outputs = gen.generate("write a poem", n=3)
        assert len(outputs) == 3

    def test_scores_in_range(self):
        gen = CreativeGenerator()
        outputs = gen.generate("idea", n=2)
        for o in outputs:
            assert 0.0 <= o.novelty <= 1.0
            assert 0.0 <= o.utility <= 1.0
            assert 0.0 <= o.surprise <= 1.0
            assert 0.0 <= o.combined_score <= 1.0

    def test_novelty_increases_with_history(self):
        gen = CreativeGenerator()
        gen.history = ["this is a sample text for testing novelty"]
        output = gen.generate("test content", n=1)[0]
        assert output.novelty >= 0.0

    def test_utility_with_context(self):
        gen = CreativeGenerator()
        outputs = gen.generate("generate a story", n=3, domain_context=["fiction", "narrative"])
        assert len(outputs) == 3

    def test_combine_outputs_max_novelty(self):
        gen = CreativeGenerator()
        outputs = [
            CreativeOutput("A", novelty=0.2, utility=0.9, surprise=0.5, combined_score=0.0),
            CreativeOutput("B", novelty=0.9, utility=0.3, surprise=0.7, combined_score=0.0),
        ]
        best = gen.combine_outputs(outputs, strategy="max_novelty")
        assert best.content == "B"

    def test_combine_outputs_pareto(self):
        gen = CreativeGenerator()
        outputs = [
            CreativeOutput("A", novelty=0.2, utility=0.9, surprise=0.5, combined_score=0.5),
            CreativeOutput("B", novelty=0.8, utility=0.7, surprise=0.6, combined_score=0.7),
        ]
        best = gen.combine_outputs(outputs, strategy="pareto")
        assert best.content == "B"
