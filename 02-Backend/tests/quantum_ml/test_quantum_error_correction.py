import numpy as np
from quantum_ml.quantum_error_correction import NoiseModel, ErrorMitigation


class TestNoiseModel:
    def test_depolarizing_channel_trace(self):
        model = NoiseModel(2)
        rho = np.array([[1, 0], [0, 0]], dtype=np.complex128)
        result = model.depolarizing_channel(rho, 0.1)
        assert abs(np.trace(result) - 1.0) < 1e-10

    def test_amplitude_damping_zero(self):
        model = NoiseModel(1)
        rho = np.array([[1, 0], [0, 0]], dtype=np.complex128)
        result = model.amplitude_damping(rho, 0.0)
        np.testing.assert_allclose(result, rho, atol=1e-10)

    def test_phase_damping_zero(self):
        model = NoiseModel(1)
        rho = np.array([[1, 0], [0, 0]], dtype=np.complex128)
        result = model.phase_damping(rho, 0.0)
        np.testing.assert_allclose(result, rho, atol=1e-10)

    def test_readout_error_matrix_shape(self):
        model = NoiseModel(1)
        m00, m11 = model.readout_error(0.05)
        assert m00.shape == (2, 2)
        assert m11.shape == (2, 2)

    def test_apply_noise_to_state(self):
        model = NoiseModel(2)
        state = np.array([1, 0, 0, 0], dtype=np.complex128)
        rho = model.apply_noise_to_state(state)
        assert abs(np.trace(rho) - 1.0) < 1e-10


class TestErrorMitigation:
    def test_zero_noise_extrapolation(self):
        def fn(noise):
            return 1.0 + noise * 2
        result = ErrorMitigation.zero_noise_extrapolation(fn, noises=[0.0, 0.1, 0.2], order=1)
        assert abs(result - 1.0) < 1e-10

    def test_measurement_error_mitigation_shape(self):
        counts = {"00": 50, "01": 50}
        error_matrix = np.array([[0.95, 0.05, 0.05, 0.0], [0.05, 0.95, 0.0, 0.05], [0.05, 0.0, 0.95, 0.05], [0.0, 0.05, 0.05, 0.95]])
        result = ErrorMitigation.measurement_error_mitigation(counts, error_matrix)
        assert "00" in result
        assert "01" in result

    def test_virtual_distillation(self):
        counts_list = [{"00": 10, "01": 5}, {"00": 8, "01": 7}]
        result = ErrorMitigation.virtual_distillation(counts_list)
        total = sum(result.values())
        assert abs(total - 1.0) < 1e-10

    def test_learning_dequantizing(self):
        np.random.seed(42)
        samples = [1.0, 1.1, 0.9, 1.05, 0.95]
        result = ErrorMitigation.learning_dequantizing(lambda: np.random.choice(samples), num_samples=10)
        assert isinstance(result, float)
        assert not np.isnan(result)
