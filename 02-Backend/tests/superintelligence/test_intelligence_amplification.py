import numpy as np
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from superintelligence.intelligence_amplification import (
    IntelligenceAmplifier,
    CognitiveEnhancer,
    AmplificationProfile,
)


class TestIntelligenceAmplifier:
    def test_amplify_returns_profile(self):
        amp = IntelligenceAmplifier(base_capacity=1.0)
        profile = amp.amplify(5.0)
        assert isinstance(profile, AmplificationProfile)
        assert profile.amplification_factor == 5.0

    def test_amplification_bounds(self):
        amp = IntelligenceAmplifier(max_amplification=10.0)
        profile = amp.amplify(100.0)
        assert profile.amplification_factor <= 10.0

    def test_efficiency_gain_positive(self):
        amp = IntelligenceAmplifier()
        profile = amp.amplify(3.0)
        assert profile.efficiency_gain > 0.0

    def test_bottlenecks_scale_with_factor(self):
        amp = IntelligenceAmplifier(max_amplification=100.0)
        profile = amp.amplify(60.0)
        assert "compute_bandwidth" in profile.bottlenecks
        assert "memory_bandwidth" in profile.bottlenecks
        assert "communication_latency" in profile.bottlenecks

    def test_stats_after_amplify(self):
        amp = IntelligenceAmplifier()
        amp.amplify(2.0)
        amp.amplify(3.0)
        stats = amp.get_augmentation_stats()
        assert stats["steps"] == 2
        assert stats["max_achieved"] == 3.0


class TestCognitiveEnhancer:
    def test_enhance_returns_correct_shape(self):
        enhancer = CognitiveEnhancer(dimensions=16)
        x = np.random.randn(16)
        out = enhancer.enhance(x, enhancement_level=0.5)
        assert out.shape == (16,)

    def test_enhance_pads_input(self):
        enhancer = CognitiveEnhancer(dimensions=16)
        x = np.random.randn(8)
        out = enhancer.enhance(x)
        assert out.shape == (16,)

    def test_measure_gain_non_negative(self):
        enhancer = CognitiveEnhancer(dimensions=16)
        x = np.random.randn(16)
        out = enhancer.enhance(x, enhancement_level=1.0)
        gain = enhancer.measure_gain(x, out)
        assert gain >= 0.0

    def test_enhancement_stats_keys(self):
        enhancer = CognitiveEnhancer(dimensions=16)
        stats = enhancer.get_enhancement_stats()
        assert "dimensions" in stats
        assert "mean_weight" in stats
