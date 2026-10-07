package backend

// Backend defines the interface for execution backends.
type Backend interface {
	// Name returns the backend identifier.
	Name() string
	// SupportedDtypes returns the data types this backend supports.
	SupportedDtypes() []string
	// MatMul performs matrix multiplication.
	MatMul(a, b []float64, m, n, k int) ([]float64, error)
	// Add performs element-wise addition.
	Add(a, b []float64) ([]float64, error)
	// Relu applies the ReLU activation.
	Relu(x []float64) []float64
	// Softmax applies the softmax function.
	Softmax(x []float64, dim int) ([]float64, error)
}
