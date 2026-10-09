import numpy as np
from training_engine.silent_corruption import SilentCorruptionDetector


def test_register_and_verify():
    det = SilentCorruptionDetector()
    data = np.array([1.0, 2.0, 3.0])
    det.register("w", data)
    assert det.verify("w", data) is True


def test_detect_corruption():
    det = SilentCorruptionDetector()
    data = np.array([1.0, 2.0, 3.0])
    det.register("w", data)
    corrupted = np.array([1.0, 2.0, 4.0])
    assert det.verify("w", corrupted) is False


def test_checksum_is_deterministic():
    det = SilentCorruptionDetector()
    data = np.array([1.0, 2.0, 3.0])
    c1 = det.verify("x", data)
    det2 = SilentCorruptionDetector()
    c2 = det2.verify("x", data)
    assert c1 is True and c2 is True
