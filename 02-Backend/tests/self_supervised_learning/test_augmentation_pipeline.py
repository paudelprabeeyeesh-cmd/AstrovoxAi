import math
import random

import pytest

from self_supervised_learning.augmentation_pipeline import (
    AugmentationPipeline,
    DEFAULT_PIPELINE,
    Dropout,
    GaussianNoise,
    RandomRescale,
)


class TestGaussianNoise:
    def test_returns_same_length(self):
        transform = GaussianNoise(std=0.01)
        x = [1.0, 2.0, 3.0]
        result = transform(x)
        assert len(result) == len(x)

    def test_deterministic_with_seed(self):
        transform = GaussianNoise(std=0.1, seed=42)
        x = [1.0, 2.0, 3.0]
        first = transform(x)
        second = transform(x)
        assert first == second

    def test_different_seeds_give_different_results(self):
        transform_a = GaussianNoise(std=0.1, seed=1)
        transform_b = GaussianNoise(std=0.1, seed=2)
        x = [1.0, 2.0, 3.0]
        assert transform_a(x) != transform_b(x)


class TestDropout:
    def test_returns_same_length(self):
        transform = Dropout(p=0.5, seed=42)
        x = [1.0, 2.0, 3.0, 4.0]
        result = transform(x)
        assert len(result) == len(x)

    def test_deterministic_with_seed(self):
        transform = Dropout(p=0.5, seed=42)
        x = [1.0, 2.0, 3.0]
        first = transform(x)
        second = transform(x)
        assert first == second

    def test_zero_prob_preserves_values(self):
        transform = Dropout(p=0.0, seed=42)
        x = [1.0, 2.0, 3.0]
        result = transform(x)
        assert result == x


class TestRandomRescale:
    def test_returns_same_length(self):
        transform = RandomRescale(low=0.8, high=1.2, seed=42)
        x = [1.0, 2.0, 3.0]
        result = transform(x)
        assert len(result) == len(x)

    def test_deterministic_with_seed(self):
        transform = RandomRescale(low=0.8, high=1.2, seed=42)
        x = [1.0, 2.0, 3.0]
        first = transform(x)
        second = transform(x)
        assert first == second

    def test_scale_within_range(self):
        transform = RandomRescale(low=0.8, high=1.2, seed=42)
        x = [1.0, 2.0, 3.0]
        result = transform(x)
        for orig, scaled in zip(x, result):
            assert scaled == pytest.approx(orig * transform(x)[0] / x[0])


class TestAugmentationPipeline:
    def test_empty_pipeline(self):
        pipeline = AugmentationPipeline(transforms=[])
        x = [1.0, 2.0, 3.0]
        assert pipeline(x) == x

    def test_default_pipeline_returns_same_length(self):
        x = [1.0, 2.0, 3.0]
        result = DEFAULT_PIPELINE(x)
        assert len(result) == len(x)

    def test_append_transform(self):
        pipeline = AugmentationPipeline(transforms=[])
        pipeline.append(GaussianNoise(std=0.0, seed=42))
        x = [1.0, 2.0, 3.0]
        result = pipeline(x)
        assert len(result) == len(x)

    def test_chained_transforms(self):
        pipeline = AugmentationPipeline(
            transforms=[
                RandomRescale(low=1.0, high=1.0, seed=42),
                GaussianNoise(std=0.0, seed=42),
            ]
        )
        x = [1.0, 2.0, 3.0]
        result = pipeline(x)
        assert result == x
