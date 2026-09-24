import math
from advanced_optimization.particle_swarm_optimizer import particle_swarm_optimization


def _sum_sq(x, target):
    return sum((xi - t) ** 2 for xi, t in zip(x, target))


def test_particle_swarm_optimization_converges():
    target = [3.0]
    f = lambda x: _sum_sq(x, target)
    x = particle_swarm_optimization(f, [(-10, 10)], n_particles=30, max_iter=100)
    assert abs(x[0] - target[0]) < 0.5


def test_particle_swarm_optimization_multidim():
    target = [2.0, -1.0]
    f = lambda x: _sum_sq(x, target)
    x = particle_swarm_optimization(f, [(-5, 5), (-5, 5)], n_particles=30, max_iter=100)
    assert all(abs(xi - ti) < 0.5 for xi, ti in zip(x, target))
