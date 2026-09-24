import numpy as np


def _hv_recursive(points):
    if len(points) == 0:
        return 0.0
    n = points.shape[1]
    if n == 1:
        return float(np.max(points))
    hv = 0.0
    points = points[np.argsort(points[:, 0])]
    prev = 0.0
    for i in range(len(points)):
        remaining = points[i:, 1:]
        hv += (points[i, 0] - prev) * _hv_recursive(remaining)
        prev = points[i, 0]
    return hv


def hypervolume(front, reference_point):
    front = np.asarray(front, dtype=float)
    reference_point = np.asarray(reference_point, dtype=float)
    if front.size == 0:
        return 0.0
    front = front - reference_point
    front = np.maximum(front, 0.0)
    return _hv_recursive(front)
