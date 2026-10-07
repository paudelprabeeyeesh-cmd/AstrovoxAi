package kernels

import "math"

// mathTanh delegates to the standard library.
func mathTanh(x float64) float64 { return math.Tanh(x) }
