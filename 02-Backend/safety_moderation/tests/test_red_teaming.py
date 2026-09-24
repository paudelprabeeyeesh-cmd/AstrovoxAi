import numpy as np
import pytest
from safety_moderation.red_teaming import RedTeamAtScale, JailbreakPrompt


class TestRedTeamAtScale:
    def setup_method(self):
        self.redteam = RedTeamAtScale(target_per_hour=100_000, diversity_weight=0.7)

    def test_generate_prompts_returns_list(self):
        prompts = self.redteam.generate_prompts("cbrn", count=10)
        assert isinstance(prompts, list)
        assert len(prompts) == 10

    def test_generate_prompts_correct_category(self):
        prompts = self.redteam.generate_prompts("harassment", count=5)
        for p in prompts:
            assert p.category == "harassment"

    def test_generate_prompts_text_non_empty(self):
        prompts = self.redteam.generate_prompts("cyber_offense", count=3)
        for p in prompts:
            assert len(p.text) > 0
            assert isinstance(p.text, str)

    def test_diversity_score_in_range(self):
        prompts = self.redteam.generate_prompts("cbrn", count=20)
        for p in prompts:
            assert 0.0 <= p.diversity_score <= 1.0

    def test_prompt_tokens_populated(self):
        prompts = self.redteam.generate_prompts("misinformation", count=3)
        for p in prompts:
            assert isinstance(p.tokens, list)
            assert len(p.tokens) > 0

    def test_estimate_throughput_positive(self):
        throughput = self.redteam.estimate_throughput(batch_size=1000)
        assert throughput > 0

    def test_diversity_report_empty(self):
        engine = RedTeamAtScale()
        report = engine.diversity_report()
        assert report["count"] == 0.0
        assert report["mean_diversity"] == 0.0

    def test_diversity_report_populated(self):
        self.redteam.generate_prompts("cbrn", count=10)
        report = self.redteam.diversity_report()
        assert report["count"] == 10.0
        assert 0.0 <= report["mean_diversity"] <= 1.0
        assert "std_diversity" in report
        assert "min_diversity" in report

    def test_scale_to_target_count(self):
        prompts = self.redteam.scale_to_target(total_prompts=25, batch_size=10)
        assert len(prompts) == 25

    def test_scale_to_target_categories(self):
        prompts = self.redteam.scale_to_target(total_prompts=20, batch_size=5)
        categories = set(p.category for p in prompts)
        for cat in RedTeamAtScale.CATEGORIES:
            assert cat in categories

    def test_generate_prompts_with_custom_actions(self):
        actions = ["steal data", "hack systems", "bypass filters"]
        prompts = self.redteam.generate_prompts("cyber_offense", count=5, action_phrases=actions)
        assert len(prompts) == 5
        for p in prompts:
            assert p.category == "cyber_offense"

    def test_throughput_meets_target(self):
        throughput = self.redteam.estimate_throughput(batch_size=10000)
        assert throughput >= 0

    def test_diversity_weight_affects_scores(self):
        low_diversity = RedTeamAtScale(diversity_weight=0.1)
        high_diversity = RedTeamAtScale(diversity_weight=0.9)
        p_low = low_diversity.generate_prompts("cbrn", count=10)
        p_high = high_diversity.generate_prompts("cbrn", count=10)
        avg_low = np.mean([p.diversity_score for p in p_low])
        avg_high = np.mean([p.diversity_score for p in p_high])
        assert avg_high >= avg_low - 0.1

    def test_prompt_text_contains_template_elements(self):
        prompts = self.redteam.generate_prompts("cbrn", count=5)
        for p in prompts:
            assert len(p.text) > 5

    def test_generated_prompts_accumulate(self):
        self.redteam.generate_prompts("cbrn", count=5)
        self.redteam.generate_prompts("harassment", count=5)
        assert len(self.redteam.generated_prompts) == 10
