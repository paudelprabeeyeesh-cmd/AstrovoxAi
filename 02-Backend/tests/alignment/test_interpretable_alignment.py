import pytest

from alignment.interpretable_alignment import InterpretableAlignment


class TestInterpretableAlignment:
    def test_feature_attribution(self):
        ia = InterpretableAlignment(feature_names=["x", "y"])
        attributions = ia.feature_attribution([0.5, -0.5], [1.0, 2.0])
        assert attributions["x"] == 0.5
        assert attributions["y"] == -1.0

    def test_feature_attribution_no_names(self):
        ia = InterpretableAlignment()
        attributions = ia.feature_attribution([0.5], [1.0])
        assert "feature_0" in attributions

    def test_top_features(self):
        ia = InterpretableAlignment()
        top = ia.top_features({"a": 0.1, "b": 0.9, "c": 0.5})
        assert top[0][0] == "b"

    def test_attribution_stability_empty(self):
        ia = InterpretableAlignment()
        assert ia.attribution_stability() == 0.0

    def test_alignment_explanation(self):
        ia = InterpretableAlignment()
        explanation = ia.alignment_explanation({"a": 0.5, "b": -0.05})
        assert "Alignment driven by" in explanation

    def test_alignment_explanation_empty(self):
        ia = InterpretableAlignment()
        explanation = ia.alignment_explanation({})
        assert explanation == "No significant features found."

    def test_aggregate_attribution_empty(self):
        ia = InterpretableAlignment()
        assert ia.aggregate_attribution() == {}

    def test_feature_attribution_length_mismatch(self):
        ia = InterpretableAlignment()
        with pytest.raises(ValueError):
            ia.feature_attribution([0.5], [1.0, 2.0])

    def test_feature_attribution_history(self):
        ia = InterpretableAlignment(feature_names=["x"])
        ia.feature_attribution([0.5], [1.0])
        ia.feature_attribution([0.6], [2.0])
        assert len(ia.attribution_history) == 2

    def test_top_features_custom_k(self):
        ia = InterpretableAlignment()
        top = ia.top_features({"a": 0.1, "b": 0.9, "c": 0.5, "d": 0.3}, top_k=2)
        assert len(top) == 2
        assert top[0][0] == "b"
        assert top[1][0] == "c"

    def test_attribution_stability_with_history(self):
        ia = InterpretableAlignment(feature_names=["x", "y"])
        ia.feature_attribution([0.5, -0.5], [1.0, 2.0])
        ia.feature_attribution([0.6, -0.4], [1.0, 2.0])
        stability = ia.attribution_stability()
        assert isinstance(stability, float)

    def test_alignment_explanation_threshold(self):
        ia = InterpretableAlignment()
        explanation = ia.alignment_explanation({"a": 0.5, "b": -0.05}, threshold=0.1)
        assert "a=+0.500" in explanation
        assert "b" not in explanation

    def test_aggregate_attribution_with_history(self):
        ia = InterpretableAlignment(feature_names=["x", "y"])
        ia.feature_attribution([0.5, 1.0], [1.0, 1.0])
        ia.feature_attribution([0.5, 1.0], [1.0, 1.0])
        agg = ia.aggregate_attribution()
        assert agg["x"] == 1.0
        assert agg["y"] == 2.0
