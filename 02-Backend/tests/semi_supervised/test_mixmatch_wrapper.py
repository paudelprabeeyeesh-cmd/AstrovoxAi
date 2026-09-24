import random
import math
from typing import List
from semi_supervised.mixmatch_wrapper import MixMatchWrapper


def _deterministic_model(x: List[List[float]]) -> List[List[float]]:
    return [[math.sin(sum(sample) + i) for i in range(3)] for sample in x]


def _augment(x: List[float]) -> List[float]:
    return [v + 0.01 for v in x]


def test_mixmatch_output_keys():
    wrapper = MixMatchWrapper(num_augmentations=2, alpha=0.75)
    labeled_x = [[1.0, 2.0], [3.0, 4.0]]
    labeled_y = [0, 1]
    unlabeled_x = [[5.0, 6.0]]
    result = wrapper.process(labeled_x, labeled_y, unlabeled_x, _deterministic_model, _augment)
    assert "mixed_x" in result
    assert "mixed_y" in result
    assert "labeled_weight" in result
    assert "unlabeled_weight" in result


def test_mixmatch_no_unlabeled():
    wrapper = MixMatchWrapper(num_augmentations=2)
    labeled_x = [[1.0, 2.0], [3.0, 4.0]]
    labeled_y = [0, 1]
    result = wrapper.process(labeled_x, labeled_y, [], _deterministic_model)
    assert result["unlabeled_weight"] == 0.0
    assert len(result["mixed_x"]) == 4


def test_mixmatch_mixed_shapes():
    wrapper = MixMatchWrapper(num_augmentations=1, alpha=0.75)
    labeled_x = [[1.0, 2.0]]
    labeled_y = [0]
    unlabeled_x = [[3.0, 4.0]]
    random.seed(0)
    result = wrapper.process(labeled_x, labeled_y, unlabeled_x, _deterministic_model)
    assert len(result["mixed_x"]) == 2
    assert len(result["mixed_y"]) == 2
