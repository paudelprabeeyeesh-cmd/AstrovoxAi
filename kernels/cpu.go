package kernels

import (
	"github.com/astrovox/astrovox/internal/backend"
	"github.com/astrovox/astrovox/internal/errors"
)

// CPU kernels implemented over the tensor ops
// package. Each kernel validates its tensor
// views and operates on float64 slices.

// VecAddKernel computes out = a + b elementwise.
type VecAddKernel struct{}

// Name implements Kernel.
func (VecAddKernel) Name() string { return "vec_add" }

// Device implements Kernel.
func (VecAddKernel) Device() backend.Device { return backend.DeviceCPU }

// Execute implements Kernel.
func (VecAddKernel) Execute(inputs, outputs []TensorView, attrs map[string]any) error {
	if err := checkArity(inputs, 2, outputs, 1); err != nil {
		return err
	}
	a, ok := float64Data(inputs[0])
	if !ok {
		return errNotFloat64(inputs[0])
	}
	b, ok := float64Data(inputs[1])
	if !ok {
		return errNotFloat64(inputs[1])
	}
	out, ok := float64Data(outputs[0])
	if !ok {
		return errNotFloat64(outputs[0])
	}
	if len(a) != len(b) || len(a) != len(out) {
		return errors.New(errors.CodeInvalidArgument, "length mismatch").
			WithField("a", len(a)).WithField("b", len(b)).
			WithField("out", len(out))
	}
	for i := range a {
		out[i] = a[i] + b[i]
	}
	return nil
}

// VecMulKernel computes out = a * b elementwise.
type VecMulKernel struct{}

// Name implements Kernel.
func (VecMulKernel) Name() string { return "vec_mul" }

// Device implements Kernel.
func (VecMulKernel) Device() backend.Device { return backend.DeviceCPU }

// Execute implements Kernel.
func (VecMulKernel) Execute(inputs, outputs []TensorView, attrs map[string]any) error {
	if err := checkArity(inputs, 2, outputs, 1); err != nil {
		return err
	}
	a, ok := float64Data(inputs[0])
	if !ok {
		return errNotFloat64(inputs[0])
	}
	b, ok := float64Data(inputs[1])
	if !ok {
		return errNotFloat64(inputs[1])
	}
	out, ok := float64Data(outputs[0])
	if !ok {
		return errNotFloat64(outputs[0])
	}
	if len(a) != len(b) || len(a) != len(out) {
		return errors.New(errors.CodeInvalidArgument, "length mismatch").
			WithField("a", len(a)).WithField("b", len(b)).
			WithField("out", len(out))
	}
	for i := range a {
		out[i] = a[i] * b[i]
	}
	return nil
}

// ScaleKernel computes out = a * scalar.
type ScaleKernel struct{}

// Name implements Kernel.
func (ScaleKernel) Name() string { return "scale" }

// Device implements Kernel.
func (ScaleKernel) Device() backend.Device { return backend.DeviceCPU }

// Execute implements Kernel.
func (ScaleKernel) Execute(inputs, outputs []TensorView, attrs map[string]any) error {
	if err := checkArity(inputs, 1, outputs, 1); err != nil {
		return err
	}
	scalar, err := attrFloat(attrs, "scalar")
	if err != nil {
		return err
	}
	a, ok := float64Data(inputs[0])
	if !ok {
		return errNotFloat64(inputs[0])
	}
	out, ok := float64Data(outputs[0])
	if !ok {
		return errNotFloat64(outputs[0])
	}
	if len(a) != len(out) {
		return errors.New(errors.CodeInvalidArgument, "length mismatch").
			WithField("in", len(a)).WithField("out", len(out))
	}
	for i := range a {
		out[i] = a[i] * scalar
	}
	return nil
}

// ReluKernel computes the ReLU activation.
type ReluKernel struct{}

// Name implements Kernel.
func (ReluKernel) Name() string { return "relu" }

// Device implements Kernel.
func (ReluKernel) Device() backend.Device { return backend.DeviceCPU }

// Execute implements Kernel.
func (ReluKernel) Execute(inputs, outputs []TensorView, attrs map[string]any) error {
	if err := checkArity(inputs, 1, outputs, 1); err != nil {
		return err
	}
	a, ok := float64Data(inputs[0])
	if !ok {
		return errNotFloat64(inputs[0])
	}
	out, ok := float64Data(outputs[0])
	if !ok {
		return errNotFloat64(outputs[0])
	}
	if len(a) != len(out) {
		return errors.New(errors.CodeInvalidArgument, "length mismatch").
			WithField("in", len(a)).WithField("out", len(out))
	}
	for i := range a {
		if a[i] > 0 {
			out[i] = a[i]
		} else {
			out[i] = 0
		}
	}
	return nil
}

// TanhKernel computes the tanh activation.
type TanhKernel struct{}

// Name implements Kernel.
func (TanhKernel) Name() string { return "tanh" }

// Device implements Kernel.
func (TanhKernel) Device() backend.Device { return backend.DeviceCPU }

// Execute implements Kernel.
func (TanhKernel) Execute(inputs, outputs []TensorView, attrs map[string]any) error {
	if err := checkArity(inputs, 1, outputs, 1); err != nil {
		return err
	}
	a, ok := float64Data(inputs[0])
	if !ok {
		return errNotFloat64(inputs[0])
	}
	out, ok := float64Data(outputs[0])
	if !ok {
		return errNotFloat64(outputs[0])
	}
	if len(a) != len(out) {
		return errors.New(errors.CodeInvalidArgument, "length mismatch").
			WithField("in", len(a)).WithField("out", len(out))
	}
	for i := range a {
		out[i] = mathTanh(a[i])
	}
	return nil
}

// SumKernel computes the sum reduction over
// the flat input.
type SumKernel struct{}

// Name implements Kernel.
func (SumKernel) Name() string { return "sum" }

// Device implements Kernel.
func (SumKernel) Device() backend.Device { return backend.DeviceCPU }

// Execute implements Kernel.
func (SumKernel) Execute(inputs, outputs []TensorView, attrs map[string]any) error {
	if err := checkArity(inputs, 1, outputs, 1); err != nil {
		return err
	}
	a, ok := float64Data(inputs[0])
	if !ok {
		return errNotFloat64(inputs[0])
	}
	out, ok := float64Data(outputs[0])
	if !ok {
		return errNotFloat64(outputs[0])
	}
	if len(out) == 0 {
		return errors.New(errors.CodeInvalidArgument, "empty output")
	}
	var acc float64
	for _, v := range a {
		acc += v
	}
	out[0] = acc
	return nil
}

// MatMulKernel computes out = A @ B using the
// blocked GEMM in the math package.
type MatMulKernel struct{}

// Name implements Kernel.
func (MatMulKernel) Name() string { return "matmul" }

// Device implements Kernel.
func (MatMulKernel) Device() backend.Device { return backend.DeviceCPU }

// Execute implements Kernel.
func (MatMulKernel) Execute(inputs, outputs []TensorView, attrs map[string]any) error {
	if err := checkArity(inputs, 2, outputs, 1); err != nil {
		return err
	}
	a, ok := float64Data(inputs[0])
	if !ok {
		return errNotFloat64(inputs[0])
	}
	b, ok := float64Data(inputs[1])
	if !ok {
		return errNotFloat64(inputs[1])
	}
	out, ok := float64Data(outputs[0])
	if !ok {
		return errNotFloat64(outputs[0])
	}
	m, n, k, err := matmulDims(inputs[0], inputs[1], outputs[0])
	if err != nil {
		return err
	}
	if len(a) != m*k || len(b) != k*n || len(out) != m*n {
		return errors.New(errors.CodeInvalidArgument, "matmul length mismatch").
			WithField("m", m).WithField("n", n).WithField("k", k)
	}
	gemmBlockedCPU(a, b, out, m, n, k)
	return nil
}

// matmulDims extracts the [m, k] @ [k, n] = [m, n]
// dimensions from 2-D tensor views.
func matmulDims(a, b, out TensorView) (m, n, k int, err error) {
	as := a.Shape()
	bs := b.Shape()
	if len(as) != 2 || len(bs) != 2 {
		return 0, 0, 0, errors.New(errors.CodeInvalidArgument, "matmul requires 2-D inputs").
			WithField("a_rank", len(as)).WithField("b_rank", len(bs))
	}
	m, k = as[0], as[1]
	kb, n := bs[0], bs[1]
	if k != kb {
		return 0, 0, 0, errors.New(errors.CodeInvalidArgument, "matmul inner dimension mismatch").
			WithField("k", k).WithField("kb", kb)
	}
	if len(out.Shape()) != 2 || out.Shape()[0] != m || out.Shape()[1] != n {
		return 0, 0, 0, errors.New(errors.CodeInvalidArgument, "matmul output shape mismatch").
			WithField("want", []int{m, n}).WithField("got", out.Shape())
	}
	return m, n, k, nil
}

// gemmBlockedCPU is the cache-blocked GEMM.
func gemmBlockedCPU(a, b, out []float64, m, n, k int) {
	const mc, nc, kc = 96, 256, 256
	for jj := 0; jj < n; jj += nc {
		je := min(jj+nc, n)
		for pp := 0; pp < k; pp += kc {
			pe := min(pp+kc, k)
			for ii := 0; ii < m; ii += mc {
				ie := min(ii+mc, m)
				for j := jj; j < je; j++ {
					for i := ii; i < ie; i++ {
						acc := out[i*n+j]
						for p := pp; p < pe; p++ {
							acc += a[i*k+p] * b[p*n+j]
						}
						out[i*n+j] = acc
					}
				}
			}
		}
	}
}

func min(a, b int) int {
	if a < b {
		return a
	}
	return b
}

// checkArity validates the input/output counts.
func checkArity(inputs []TensorView, wantIn int, outputs []TensorView, wantOut int) error {
	if len(inputs) != wantIn {
		return errors.New(errors.CodeInvalidArgument, "input arity mismatch").
			WithField("got", len(inputs)).WithField("want", wantIn)
	}
	if len(outputs) != wantOut {
		return errors.New(errors.CodeInvalidArgument, "output arity mismatch").
			WithField("got", len(outputs)).WithField("want", wantOut)
	}
	return nil
}

// float64Data extracts the float64 backing slice.
func float64Data(v TensorView) ([]float64, bool) {
	d, _ := v.Data().([]float64)
	return d, d != nil
}

// errNotFloat64 builds a dtype error.
func errNotFloat64(v TensorView) error {
	return errors.New(errors.CodeInvalidArgument, "kernel requires float64 data").
		WithField("dtype", v.DType())
}

// attrFloat reads a float64 attribute.
func attrFloat(attrs map[string]any, key string) (float64, error) {
	v, ok := attrs[key]
	if !ok {
		return 0, errors.New(errors.CodeInvalidArgument, "missing attribute").
			WithField("key", key)
	}
	f, ok := v.(float64)
	if !ok {
		return 0, errors.New(errors.CodeInvalidArgument, "attribute is not float64").
			WithField("key", key)
	}
	return f, nil
}
