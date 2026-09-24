from typing import List
from semi_supervised.pseudolabel_generator import PseudolabelGenerator


def _high_confidence_model(x: List[List[float]]) -> List[List[float]]:
    return [[10.0, 0.1, 0.1] for _ in x]


def _low_confidence_model(x: List[List[float]]) -> List[List[float]]:
    return [[1.0, 1.0, 1.0] for _ in x]


def test_generate_high_confidence():
    gen = PseudolabelGenerator(threshold=0.9)
    data = [[1.0, 2.0], [3.0, 4.0], [5.0, 6.0]]
    confident, labels = gen.generate(_high_confidence_model, data)
    assert len(confident) == 3
    assert labels == [0, 0, 0]


def test_generate_low_confidence():
    gen = PseudolabelGenerator(threshold=0.9)
    data = [[1.0, 2.0], [3.0, 4.0]]
    confident, labels = gen.generate(_low_confidence_model, data)
    assert len(confident) == 0
    assert labels == []


def test_generate_partial_confidence():
    gen = PseudolabelGenerator(threshold=0.95)
    data = [[1.0, 2.0], [3.0, 4.0], [5.0, 6.0]]
    model = lambda x: [[10.0, 0.1, 0.1] if i == 0 else [1.0, 1.0, 1.0] for i in range(len(x))]
    confident, labels = gen.generate(model, data)
    assert len(confident) == 1
    assert labels == [0]
