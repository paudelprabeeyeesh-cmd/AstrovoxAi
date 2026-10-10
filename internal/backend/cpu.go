package backend

import "errors"

// CPUBackend is a reference CPU implementation.
type CPUBackend struct{}

// NewCPUBackend creates a new CPU backend.
func NewCPUBackend() *CPUBackend {
	return &CPUBackend{}
}

// Name returns the backend name.
func (c *CPUBackend) Name() string {
	return "cpu"
}

// SupportedDtypes returns supported data types.
func (c *CPUBackend) SupportedDtypes() []string {
	return []string{"float32", "float64", "int32", "int64"}
}

// MatMul performs matrix multiplication on CPU.
func (c *CPUBackend) MatMul(a, b []float64, m, n, k int) ([]float64, error) {
	if len(a) != m*k || len(b) != n*k {
		return nil, errors.New("invalid matrix dimensions")
	}
	out := make([]float64, m*n)
	for i := 0; i < m; i++ {
		for j := 0; j < n; j++ {
			sum := 0.0
			for l := 0; l < k; l++ {
				sum += a[i*k+l] * b[l*n+j]
			}
			out[i*n+j] = sum
		}
	}
	return out, nil
}

// Add performs element-wise addition.
func (c *CPUBackend) Add(a, b []float64) ([]float64, error) {
	if len(a) != len(b) {
		return nil, errors.New("shape mismatch")
	}
	out := make([]float64, len(a))
	for i := range a {
		out[i] = a[i] + b[i]
	}
	return out, nil
}

// Relu applies the ReLU activation function.
func (c *CPUBackend) Relu(x []float64) []float64 {
	out := make([]float64, len(x))
	for i, v := range x {
		if v > 0 {
			out[i] = v
		} else {
			out[i] = 0
		}
	}
	return out
}

// Softmax applies the softmax function along a dimension.
//
// The backend operates on flat slices, so dim=0 and dim=1 are equivalent
// and both are accepted.
func (c *CPUBackend) Softmax(x []float64, dim int) ([]float64, error) {
	return softmaxValues(x, dim)
}
