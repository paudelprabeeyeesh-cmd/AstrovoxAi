package math

import (
	"math"
	"runtime"
	"sync"

	"github.com/astrovox/astrovox/internal/errors"
	"github.com/astrovox/astrovox/tensor"
)

// SIMD feature set detected at init. Pure-Go builds expose the
// auto-vectorizable scalar kernels; hand-written assembly kernels
// (AVX2/Neon) plug in via RegisterKernel and are selected by
// the dispatch table below.
type SIMDFeature int

// SIMD feature classes.
const (
	SIMDScalar SIMDFeature = iota
	SIMD_AVX
	SIMD_AVX2
	SIMD_AVX512
	SIMD_NEON
)

func (f SIMDFeature) String() string {
	switch f {
	case SIMD_AVX:
		return "avx"
	case SIMD_AVX2:
		return "avx2"
	case SIMD_AVX512:
		return "avx512"
	case SIMD_NEON:
		return "neon"
	default:
		return "scalar"
	}
}

// Kernel is a SIMD-dispatchable elementwise kernel.
type Kernel struct {
	Name    string
	Feature SIMDFeature
	Fn      func(dst, a []float64)
	Binary  func(dst, a, b []float64)
	Reduce  func(xs []float64) float64
}

var (
	kernelMu      sync.RWMutex
	kernelTable   = map[string]*Kernel{}
	activeFeature = detectFeature()
)

// detectFeature resolves the best kernel class for the host.
// On amd64 the Go compiler auto-vectorizes the scalar kernels;
// the classification drives kernel selection and reporting.
func detectFeature() SIMDFeature {
	switch runtime.GOARCH {
	case "amd64":
		return SIMD_AVX2
	case "arm64":
		return SIMD_NEON
	default:
		return SIMDScalar
	}
}

// ActiveFeature returns the detected SIMD class.
func ActiveFeature() SIMDFeature { return activeFeature }

// RegisterKernel installs a kernel implementation, replacing
// any prior registration for the same name.
func RegisterKernel(k *Kernel) error {
	if k == nil || k.Name == "" {
		return errors.New(errors.CodeInvalidArgument, "kernel requires a name")
	}
	kernelMu.Lock()
	kernelTable[k.Name] = k
	kernelMu.Unlock()
	return nil
}

// GetKernel returns the registered kernel by name.
func GetKernel(name string) (*Kernel, bool) {
	kernelMu.RLock()
	defer kernelMu.RUnlock()
	k, ok := kernelTable[name]
	return k, ok
}

// VecAdd computes dst = a + b with the registered kernel.
func VecAdd(dst, a, b []float64) error { return callBinary("vec_add", dst, a, b) }

// VecMul computes dst = a * b with the registered kernel.
func VecMul(dst, a, b []float64) error { return callBinary("vec_mul", dst, a, b) }

// VecExp computes dst = exp(a) with the registered kernel.
func VecExp(dst, a []float64) error { return callUnary("vec_exp", dst, a) }

// VecTanh computes dst = tanh(a) with the registered kernel.
func VecTanh(dst, a []float64) error { return callUnary("vec_tanh", dst, a) }

// VecSum returns the sum of xs with the registered kernel.
func VecSum(xs []float64) (float64, error) { return callReduce("vec_sum", xs) }

// VecDot returns the dot product of a and b.
func VecDot(a, b []float64) (float64, error) {
	if len(a) != len(b) {
		return 0, errors.New(errors.CodeShapeMismatch, "dot length mismatch")
	}
	if k, ok := GetKernel("vec_dot"); ok && k.Binary != nil {
		// Binary kernels accumulate into dst; use a 1-element dst.
		dst := make([]float64, 1)
		k.Binary(dst, a, b)
		return dst[0], nil
	}
	var sum float64
	for i := range a {
		sum += a[i] * b[i]
	}
	return sum, nil
}

func callUnary(name string, dst, a []float64) error {
	if len(dst) != len(a) {
		return errors.New(errors.CodeShapeMismatch, "unary length mismatch")
	}
	if k, ok := GetKernel(name); ok && k.Fn != nil {
		k.Fn(dst, a)
		return nil
	}
	return errors.New(errors.CodeNotFound, "kernel not registered").WithField("kernel", name)
}

func callBinary(name string, dst, a, b []float64) error {
	if len(dst) != len(a) || len(a) != len(b) {
		return errors.New(errors.CodeShapeMismatch, "binary length mismatch")
	}
	if k, ok := GetKernel(name); ok && k.Binary != nil {
		k.Binary(dst, a, b)
		return nil
	}
	return errors.New(errors.CodeNotFound, "kernel not registered").WithField("kernel", name)
}

func callReduce(name string, xs []float64) (float64, error) {
	if k, ok := GetKernel(name); ok && k.Reduce != nil {
		return k.Reduce(xs), nil
	}
	return 0, errors.New(errors.CodeNotFound, "kernel not registered").WithField("kernel", name)
}

func init() {
	// Default scalar/auto-vectorizable kernels. These are the
	// baseline implementations; ISA-specific kernels replace
	// them via RegisterKernel.
	mustRegister(&Kernel{
		Name: "vec_add",
		Binary: func(dst, a, b []float64) {
			for i := range dst {
				dst[i] = a[i] + b[i]
			}
		},
	})
	mustRegister(&Kernel{
		Name: "vec_mul",
		Binary: func(dst, a, b []float64) {
			for i := range dst {
				dst[i] = a[i] * b[i]
			}
		},
	})
	mustRegister(&Kernel{
		Name: "vec_exp",
		Fn: func(dst, a []float64) {
			for i := range dst {
				dst[i] = math.Exp(a[i])
			}
		},
	})
	mustRegister(&Kernel{
		Name: "vec_tanh",
		Fn: func(dst, a []float64) {
			for i := range dst {
				dst[i] = math.Tanh(a[i])
			}
		},
	})
	mustRegister(&Kernel{
		Name: "vec_sum",
		Reduce: func(xs []float64) float64 {
			var sum float64
			for _, x := range xs {
				sum += x
			}
			return sum
		},
	})
	mustRegister(&Kernel{
		Name: "vec_dot",
		Binary: func(dst, a, b []float64) {
			// Full dot product accumulated into dst[0].
			var sum float64
			for i := range a {
				sum += a[i] * b[i]
			}
			dst[0] = sum
		},
	})
}

func mustRegister(k *Kernel) {
	if err := RegisterKernel(k); err != nil {
		panic(err)
	}
}

// VecAddTensor applies VecAdd over tensor storage segments.
func VecAddTensor(a, b *tensor.Tensor) (*tensor.Tensor, error) {
	if a == nil || b == nil {
		return nil, errors.New(errors.CodeInvalidArgument, "nil tensor")
	}
	if a.DType() != tensor.Float64 || b.DType() != tensor.Float64 {
		return nil, errors.New(errors.CodeDTypeMismatch, "requires float64")
	}
	if a.Shape().Rank() != 1 || b.Shape().Rank() != 1 {
		return nil, errors.New(errors.CodeInvalidArgument, "requires 1-D tensors")
	}
	if a.Shape().Dim(0) != b.Shape().Dim(0) {
		return nil, errors.New(errors.CodeShapeMismatch, "length mismatch")
	}
	out, err := tensor.New(tensor.Float64, []int{a.Shape().Dim(0)})
	if err != nil {
		return nil, err
	}
	if err := VecAdd(out.Float64(), a.Float64(), b.Float64()); err != nil {
		return nil, err
	}
	return out, nil
}
