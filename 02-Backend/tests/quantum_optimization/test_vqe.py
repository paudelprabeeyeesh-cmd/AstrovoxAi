from quantum_optimization.vqe import VQE


def test_vqe_energy_is_float():
    vqe = VQE(2, ansatz_depth=2)
    params = [0.1, 0.2, 0.3, 0.4]
    energy = vqe.energy(params)
    assert isinstance(energy, float)


def test_vqe_optimize_returns_better_energy():
    vqe = VQE(2, ansatz_depth=2)
    params = [0.5, 0.5, 0.5, 0.5]
    initial_energy = vqe.energy(params)
    best_params, best_energy = vqe.optimize(max_iter=20, lr=0.05)
    assert isinstance(best_params, list)
    assert isinstance(best_energy, float)
    assert best_energy <= initial_energy + 1e-4
