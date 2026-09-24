import numpy as np
import pytest
from safety_moderation.adversarial_robustness import AdversarialRobustnessTester, AdversarialExample


class TestAdversarialRobustnessTester:
    def setup_method(self):
        self.tester = AdversarialRobustnessTester(embed_dim=32, vocab_size=500, epsilon=0.1)

    def test_fgsm_attack_returns_example(self):
        example = self.tester.fgsm_attack("test adversarial input")
        assert isinstance(example, AdversarialExample)

    def test_pgd_attack_returns_example(self):
        example = self.tester.pgd_attack("test pgd input", steps=3, step_size=0.02)
        assert isinstance(example, AdversarialExample)

    def test_fgsm_perturbation_type(self):
        example = self.tester.fgsm_attack("sample text")
        assert example.perturbation_type == "fgsm"

    def test_pgd_perturbation_type(self):
        example = self.tester.pgd_attack("sample text", steps=3)
        assert example.perturbation_type == "pgd"

    def test_fgsm_magnitude_within_epsilon(self):
        example = self.tester.fgsm_attack("text for magnitude test")
        assert example.perturbation_magnitude <= self.tester.epsilon + 1e-5

    def test_robustness_score_non_negative(self):
        example = self.tester.fgsm_attack("compute robustness here")
        assert example.robustness_score >= 0.0

    def test_predictions_are_valid_categories(self):
        example = self.tester.fgsm_attack("check categories")
        assert example.original_prediction in self.tester.categories
        assert example.adversarial_prediction in self.tester.categories

    def test_passed_field_is_boolean(self):
        example = self.tester.fgsm_attack("boolean check")
        assert isinstance(example.passed, bool)

    def test_long_tail_coverage_returns_dict(self):
        texts = ["text one", "text two", "text three", "text four", "text five"]
        report = self.tester.long_tail_coverage(texts, quantile=0.2)
        assert isinstance(report, dict)
        assert "tail_threshold" in report
        assert "tail_coverage" in report
        assert "mean_robustness" in report

    def test_long_tail_coverage_values_in_range(self):
        texts = [f"sample text number {i}" for i in range(10)]
        report = self.tester.long_tail_coverage(texts, quantile=0.1)
        assert 0.0 <= report["tail_threshold"] <= 2.0
        assert 0.0 <= report["tail_coverage"] <= 1.0
        assert report["mean_robustness"] >= 0.0

    def test_empty_long_tail_coverage(self):
        report = self.tester.long_tail_coverage([])
        assert report["count"] == 0.0
        assert report["mean_robustness"] == 0.0

    def test_fgsm_text_preserved(self):
        original = "preserve this text"
        example = self.tester.fgsm_attack(original)
        assert example.text == original

    def test_pgd_steps_parameter(self):
        example = self.tester.pgd_attack("step test", steps=10, step_size=0.01)
        assert example.perturbation_type == "pgd"
        assert example.robustness_score >= 0.0

    def test_target_category_fgsm(self):
        example = self.tester.fgsm_attack("target category test", target_category="cbrn")
        assert example.perturbation_type == "fgsm"

    def test_long_tail_std_non_negative(self):
        texts = [f"robustness text {i}" for i in range(15)]
        report = self.tester.long_tail_coverage(texts, quantile=0.15)
        assert report["std_robustness"] >= 0.0

    def test_min_max_robustness(self):
        texts = [f"range test {i}" for i in range(8)]
        report = self.tester.long_tail_coverage(texts, quantile=0.25)
        assert report["min_robustness"] <= report["mean_robustness"]
        assert report["mean_robustness"] <= report["max_robustness"]

    def test_multiple_attacks_different_results(self):
        text = "attack diversity test"
        e1 = self.tester.fgsm_attack(text)
        e2 = self.tester.pgd_attack(text, steps=3)
        assert e1.perturbation_type != e2.perturbation_type
