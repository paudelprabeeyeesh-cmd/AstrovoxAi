import numpy as np
import pytest
from tensor_engine.einsum import EinsumEquation, einsum


class TestEinsumEquation:
    def test_parse_two_inputs(self):
        eq = EinsumEquation("ij,jk->ik")
        assert eq.inputs == ["ij", "jk"]
        assert eq.output == "ik"
        assert eq.ninputs == 2

    def test_parse_no_output(self):
        eq = EinsumEquation("ij,jk")
        assert eq.inputs == ["ij", "jk"]
        assert eq.output == ""

    def test_contract_labels(self):
        eq = EinsumEquation("ij,jk->ik")
        assert "j" in eq.contract_labels

    def test_output_labels(self):
        eq = EinsumEquation("ij,jk->ik")
        assert eq.output_labels == ["i", "k"]

    def test_verify_shapes_valid(self):
        eq = EinsumEquation("ij,jk->ik")
        eq.verify_shapes([(2, 3), (3, 4)])

    def test_verify_shapes_invalid(self):
        eq = EinsumEquation("ij,jk->ik")
        with pytest.raises(ValueError):
            eq.verify_shapes([(2, 3), (4, 5)])

    def test_compute_output_shape(self):
        eq = EinsumEquation("ij,jk->ik")
        shape = eq.compute_output_shape([(2, 3), (3, 4)])
        assert shape == (2, 4)


class TestEinsum:
    def test_matrix_multiplication(self):
        A = np.random.randn(2, 3)
        B = np.random.randn(3, 4)
        result = einsum("ij,jk->ik", A, B)
        expected = np.einsum("ij,jk->ik", A, B)
        np.testing.assert_allclose(result, expected)

    def test_batch_matmul(self):
        A = np.random.randn(5, 2, 3)
        B = np.random.randn(5, 3, 4)
        result = einsum("bij,bjk->bik", A, B)
        expected = np.einsum("bij,bjk->bik", A, B)
        np.testing.assert_allclose(result, expected)

    def test_trace(self):
        A = np.random.randn(3, 3)
        result = einsum("ii->", A)
        expected = np.einsum("ii->", A)
        np.testing.assert_allclose(result, expected)

    def test_outer_product(self):
        a = np.random.randn(3)
        b = np.random.randn(4)
        result = einsum("i,j->ij", a, b)
        expected = np.einsum("i,j->ij", a, b)
        np.testing.assert_allclose(result, expected)

    def test_sum_reduction(self):
        A = np.random.randn(2, 3, 4)
        result = einsum("ijk->", A)
        expected = np.einsum("ijk->", A)
        np.testing.assert_allclose(result, expected)

    def test_mean_reduction(self):
        A = np.random.randn(2, 3, 4)
        result = einsum("ijk->k", A) / 6.0
        expected = np.einsum("ijk->k", A) / 6.0
        np.testing.assert_allclose(result, expected)

    def test_diagonal_extraction(self):
        A = np.random.randn(3, 3)
        result = einsum("ii->i", A)
        expected = np.einsum("ii->i", A)
        np.testing.assert_allclose(result, expected)

    def test_hadamard(self):
        A = np.random.randn(2, 3)
        B = np.random.randn(2, 3)
        result = einsum("ij,ij->ij", A, B)
        expected = np.einsum("ij,ij->ij", A, B)
        np.testing.assert_allclose(result, expected)

    def test_bilinear(self):
        A = np.random.randn(2, 3)
        B = np.random.randn(2, 3)
        result = einsum("i,j->ij", A[0], B[0])
        expected = np.einsum("i,j->ij", A[0], B[0])
        np.testing.assert_allclose(result, expected)

    def test_invalid_shapes(self):
        A = np.random.randn(2, 3)
        B = np.random.randn(4, 5)
        with pytest.raises(ValueError):
            einsum("ij,jk->ik", A, B)

    def test_no_operands(self):
        with pytest.raises(ValueError):
            einsum("ij,jk->ik")

    def test_three_operands(self):
        A = np.random.randn(2, 3)
        B = np.random.randn(3, 4)
        C = np.random.randn(4, 5)
        result = einsum("ij,jk,kl->ikl", A, B, C)
        expected = np.einsum("ij,jk,kl->ikl", A, B, C)
        np.testing.assert_allclose(result, expected)
