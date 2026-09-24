from quantum_optimization.quantum_annealing import simulated_quantum_annealing


def test_quantum_annealing_converges():
    f = lambda x: sum((xi - 2.0) ** 2 for xi in x)
    x = simulated_quantum_annealing(f, [0.0], steps=500)
    assert abs(x[0] - 2.0) < 1.0


def test_quantum_annealing_multidim():
    f = lambda x: sum((xi - 1.0) ** 2 for xi in x)
    x = simulated_quantum_annealing(f, [0.0, 0.0], steps=500)
    assert abs(x[0] - 1.0) < 1.0
    assert abs(x[1] - 1.0) < 1.0
