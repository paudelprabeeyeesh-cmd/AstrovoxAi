// Package ops implements elementwise and matrix operations
// over tensors, dispatched through the broadcasting iterator.
package ops

import (
	"math"

	"github.com/astrovox/astrovox/internal/errors"
	"github.com/astrovox/astrovox/tensor"
	"github.com/astrovox/astrovox/tensor/iterator"
)

// Add returns a + b with broadcasting.
func Add(a, b *tensor.Tensor) (*tensor.Tensor, error) {
	return binaryOp(a, b, func(x, y float64) float64 { return x + y })
}

// Sub returns a - b with broadcasting.
func Sub(a, b *tensor.Tensor) (*tensor.Tensor, error) {
	return binaryOp(a, b, func(x, y float64) float64 { return x - y })
}

// Mul returns a * b with broadcasting.
func Mul(a, b *tensor.Tensor) (*tensor.Tensor, error) {
	return binaryOp(a, b, func(x, y float64) float64 { return x * y })
}

// Div returns a / b with broadcasting.
func Div(a, b *tensor.Tensor) (*tensor.Tensor, error) {
	return binaryOp(a, b, func(x, y float64) float64 { return x / y })
}

// Pow returns a ** b with broadcasting.
func Pow(a, b *tensor.Tensor) (*tensor.Tensor, error) {
	return binaryOp(a, b, math.Pow)
}

// Min returns element-wise minimum with broadcasting.
func Min(a, b *tensor.Tensor) (*tensor.Tensor, error) {
	return binaryOp(a, b, math.Min)
}

// Max returns element-wise maximum with broadcasting.
func Max(a, b *tensor.Tensor) (*tensor.Tensor, error) {
	return binaryOp(a, b, math.Max)
}

// Neg returns -a.
func Neg(a *tensor.Tensor) (*tensor.Tensor, error) {
	return unaryOp(a, func(x float64) float64 { return -x })
}

// Scale returns a * scalar.
func Scale(a *tensor.Tensor, scalar float64) (*tensor.Tensor, error) {
	return unaryOp(a, func(x float64) float64 { return x * scalar })
}

// Exp returns e ** a.
func Exp(a *tensor.Tensor) (*tensor.Tensor, error) {
	return unaryOp(a, math.Exp)
}

// Log returns ln(a).
func Log(a *tensor.Tensor) (*tensor.Tensor, error) {
	return unaryOp(a, math.Log)
}

// Sqrt returns sqrt(a).
func Sqrt(a *tensor.Tensor) (*tensor.Tensor, error) {
	return unaryOp(a, math.Sqrt)
}

// Tanh returns tanh(a).
func Tanh(a *tensor.Tensor) (*tensor.Tensor, error) {
	return unaryOp(a, math.Tanh)
}

// Sigmoid returns 1 / (1 + e ** -a).
func Sigmoid(a *tensor.Tensor) (*tensor.Tensor, error) {
	return unaryOp(a, func(x float64) float64 { return 1 / (1 + math.Exp(-x)) })
}

// Relu returns max(0, a).
func Relu(a *tensor.Tensor) (*tensor.Tensor, error) {
	return unaryOp(a, func(x float64) float64 {
		if x < 0 {
			return 0
		}
		return x
	})
}

// Abs returns |a|.
func Abs(a *tensor.Tensor) (*tensor.Tensor, error) {
	return unaryOp(a, math.Abs)
}

// AddScalar returns a + c element-wise.
func AddScalar(a *tensor.Tensor, c float64) (*tensor.Tensor, error) {
	return unaryOp(a, func(x float64) float64 { return x + c })
}

// SubScalar returns a - c element-wise.
func SubScalar(a *tensor.Tensor, c float64) (*tensor.Tensor, error) {
	return unaryOp(a, func(x float64) float64 { return x - c })
}

// MulScalar returns a * c element-wise. It is Scale with a name that
// matches the arithmetic it performs.
func MulScalar(a *tensor.Tensor, c float64) (*tensor.Tensor, error) {
	return unaryOp(a, func(x float64) float64 { return x * c })
}

// DivScalar returns a / c element-wise.
func DivScalar(a *tensor.Tensor, c float64) (*tensor.Tensor, error) {
	if c == 0 {
		return nil, errors.New(errors.CodeInvalidArgument, "division by zero")
	}
	return unaryOp(a, func(x float64) float64 { return x / c })
}

// Softmax returns the softmax of a along dim, computed stably: the row
// maximum is subtracted before exponentiation, so large inputs do not
// overflow to +Inf/NaN. dim may be any rank in range, including negative
// for Python-style indexing from the end.
func Softmax(a *tensor.Tensor, dim int) (*tensor.Tensor, error) {
	if a == nil {
		return nil, errors.New(errors.CodeInvalidArgument, "nil tensor")
	}
	if a.DType() != tensor.Float64 {
		return nil, errors.New(errors.CodeDTypeMismatch, "softmax requires float64").
			WithField("dtype", a.DType())
	}
	rank := a.Shape().Rank()
	if rank < 1 {
		return nil, errors.New(errors.CodeInvalidArgument, "softmax requires rank >= 1")
	}
	if dim < 0 {
		dim += rank
	}
	if dim < 0 || dim >= rank {
		return nil, errors.New(errors.CodeInvalidArgument, "softmax dim out of range").
			WithField("dim", dim).WithField("rank", rank)
	}
	var err error
	if !a.IsContiguous() {
		if a, err = a.Contiguous(); err != nil {
			return nil, err
		}
	}
	d := a.Shape().Dim(dim)
	outer := 1
	for i := 0; i < dim; i++ {
		outer *= a.Shape().Dim(i)
	}
	inner := 1
	for i := dim + 1; i < rank; i++ {
		inner *= a.Shape().Dim(i)
	}
	src := a.Float64()
	out, err := tensor.New(tensor.Float64, a.Shape().Dims())
	if err != nil {
		return nil, err
	}
	dst := out.Float64()
	for o := 0; o < outer; o++ {
		for in := 0; in < inner; in++ {
			base := o*d*inner + in
			// Max over the softmax dim for numerical stability.
			maxV := src[base]
			for i := 1; i < d; i++ {
				if v := src[base+i*inner]; v > maxV {
					maxV = v
				}
			}
			var sum float64
			for i := 0; i < d; i++ {
				e := math.Exp(src[base+i*inner] - maxV)
				dst[base+i*inner] = e
				sum += e
			}
			inv := 1 / sum
			for i := 0; i < d; i++ {
				dst[base+i*inner] *= inv
			}
		}
	}
	return out, nil
}

// Concat concatenates tensors along dim. All inputs must share rank,
// dtype, and every dimension except dim.
func Concat(ts []*tensor.Tensor, dim int) (*tensor.Tensor, error) {
	if len(ts) == 0 {
		return nil, errors.New(errors.CodeInvalidArgument, "concat requires at least one tensor")
	}
	for _, t := range ts {
		if t == nil {
			return nil, errors.New(errors.CodeInvalidArgument, "nil tensor in concat")
		}
		if t.DType() != tensor.Float64 {
			return nil, errors.New(errors.CodeDTypeMismatch, "concat requires float64").
				WithField("dtype", t.DType())
		}
	}
	rank := ts[0].Shape().Rank()
	if dim < 0 {
		dim += rank
	}
	if dim < 0 || dim >= rank {
		return nil, errors.New(errors.CodeInvalidArgument, "concat dim out of range").
			WithField("dim", dim).WithField("rank", rank)
	}
	outDims := make([]int, rank)
	copy(outDims, ts[0].Shape().Dims())
	total := 0
	for i, t := range ts {
		if t.Shape().Rank() != rank {
			return nil, errors.New(errors.CodeShapeMismatch, "concat rank mismatch").
				WithField("index", i).WithField("rank", t.Shape().Rank())
		}
		for d := 0; d < rank; d++ {
			if d != dim && t.Shape().Dim(d) != outDims[d] {
				return nil, errors.New(errors.CodeShapeMismatch, "concat dim mismatch").
					WithField("index", i).WithField("dim", d)
			}
		}
		total += t.Shape().Dim(dim)
	}
	outDims[dim] = total
	out, err := tensor.New(tensor.Float64, outDims)
	if err != nil {
		return nil, err
	}
	// Copy block by block: the slices outside dim form a rectangular block
	// of size (prod(dims[:dim]) * dims[dim] * prod(dims[dim+1:])).
	outer := 1
	for i := 0; i < dim; i++ {
		outer *= outDims[i]
	}
	inner := 1
	for i := dim + 1; i < rank; i++ {
		inner *= outDims[i]
	}
	dst := out.Float64()
	offset := 0
	for _, t := range ts {
		var src []float64
		if t.IsContiguous() {
			src = t.Float64()
		} else {
			c, err := t.Contiguous()
			if err != nil {
				return nil, err
			}
			src = c.Float64()
		}
		dn := t.Shape().Dim(dim)
		for o := 0; o < outer; o++ {
			for id := 0; id < dn; id++ {
				for iin := 0; iin < inner; iin++ {
					dst[o*total*inner+(offset+id)*inner+iin] = src[o*dn*inner+id*inner+iin]
				}
			}
		}
		offset += dn
	}
	return out, nil
}

// Dot returns the inner product of two 1-D tensors.
func Dot(a, b *tensor.Tensor) (float64, error) {
	if a == nil || b == nil {
		return 0, errors.New(errors.CodeInvalidArgument, "nil tensor")
	}
	if a.Shape().Rank() != 1 || b.Shape().Rank() != 1 {
		return 0, errors.New(errors.CodeInvalidArgument, "dot requires 1-D tensors").
			WithField("a_rank", a.Shape().Rank()).WithField("b_rank", b.Shape().Rank())
	}
	if a.Shape().Dim(0) != b.Shape().Dim(0) {
		return 0, errors.New(errors.CodeShapeMismatch, "dot length mismatch").
			WithField("a_len", a.Shape().Dim(0)).WithField("b_len", b.Shape().Dim(0))
	}
	if a.DType() != tensor.Float64 || b.DType() != tensor.Float64 {
		return 0, errors.New(errors.CodeDTypeMismatch, "dot requires float64").
			WithField("a_dtype", a.DType()).WithField("b_dtype", b.DType())
	}
	var err error
	if !a.IsContiguous() {
		a, err = a.Contiguous()
		if err != nil {
			return 0, err
		}
	}
	if !b.IsContiguous() {
		b, err = b.Contiguous()
		if err != nil {
			return 0, err
		}
	}
	x, y := a.Float64(), b.Float64()
	var sum float64
	for i := range x {
		sum += x[i] * y[i]
	}
	return sum, nil
}

// MatMul returns the matrix product of two 2-D tensors.
// Non-contiguous views (transposes, slices, broadcasts)
// are materialized first so the blocked kernels read
// row-major data.
func MatMul(a, b *tensor.Tensor) (*tensor.Tensor, error) {
	if a == nil || b == nil {
		return nil, errors.New(errors.CodeInvalidArgument, "nil tensor")
	}
	if a.Shape().Rank() != 2 || b.Shape().Rank() != 2 {
		return nil, errors.New(errors.CodeInvalidArgument, "matmul requires 2-D tensors").
			WithField("a_rank", a.Shape().Rank()).WithField("b_rank", b.Shape().Rank())
	}
	m := a.Shape().Dim(0)
	k := a.Shape().Dim(1)
	kb := b.Shape().Dim(0)
	n := b.Shape().Dim(1)
	if k != kb {
		return nil, errors.New(errors.CodeShapeMismatch, "matmul contracting dims mismatch").
			WithField("k", k).WithField("k_b", kb)
	}
	if a.DType() != tensor.Float64 || b.DType() != tensor.Float64 {
		return nil, errors.New(errors.CodeDTypeMismatch, "matmul requires float64").
			WithField("a_dtype", a.DType()).WithField("b_dtype", b.DType())
	}
	var err error
	if !a.IsContiguous() {
		a, err = a.Contiguous()
		if err != nil {
			return nil, err
		}
	}
	if !b.IsContiguous() {
		b, err = b.Contiguous()
		if err != nil {
			return nil, err
		}
	}
	out, err := tensor.New(tensor.Float64, []int{m, n})
	if err != nil {
		return nil, err
	}
	A := a.Float64()
	B := b.Float64()
	C := out.Float64()
	const block = 64
	for ii := 0; ii < m; ii += block {
		iEnd := min(ii+block, m)
		for jj := 0; jj < n; jj += block {
			jEnd := min(jj+block, n)
			for kk := 0; kk < k; kk += block {
				kEnd := min(kk+block, k)
				for i := ii; i < iEnd; i++ {
					for j := jj; j < jEnd; j++ {
						var acc float64
						baseA := i * k
						baseC := i * n
						for p := kk; p < kEnd; p++ {
							acc += A[baseA+p] * B[p*n+j]
						}
						C[baseC+j] += acc
					}
				}
			}
		}
	}
	return out, nil
}

func min(a, b int) int {
	if a < b {
		return a
	}
	return b
}

// unaryOp applies fn element-wise, producing a new tensor.
// Non-contiguous views are materialized first.
func unaryOp(a *tensor.Tensor, fn func(float64) float64) (*tensor.Tensor, error) {
	if a == nil {
		return nil, errors.New(errors.CodeInvalidArgument, "nil tensor")
	}
	if a.DType() != tensor.Float64 {
		return nil, errors.New(errors.CodeDTypeMismatch, "unary ops require float64").
			WithField("dtype", a.DType())
	}
	var err error
	if !a.IsContiguous() {
		a, err = a.Contiguous()
		if err != nil {
			return nil, err
		}
	}
	out, err := tensor.New(tensor.Float64, a.Shape().Dims())
	if err != nil {
		return nil, err
	}
	src := a.Float64()
	dst := out.Float64()
	for i := range src {
		dst[i] = fn(src[i])
	}
	return out, nil
}

// binaryOp applies fn element-wise with broadcasting.
// Non-contiguous views (slices, transposes, broadcasts)
// are materialized first so the typed accessors are
// valid; the iterator then handles any remaining
// broadcast expansion.
func binaryOp(a, b *tensor.Tensor, fn func(x, y float64) float64) (*tensor.Tensor, error) {
	if a == nil || b == nil {
		return nil, errors.New(errors.CodeInvalidArgument, "nil tensor")
	}
	if a.DType() != tensor.Float64 || b.DType() != tensor.Float64 {
		return nil, errors.New(errors.CodeDTypeMismatch, "binary ops require float64").
			WithField("a_dtype", a.DType()).WithField("b_dtype", b.DType())
	}
	var err error
	if !a.IsContiguous() {
		a, err = a.Contiguous()
		if err != nil {
			return nil, err
		}
	}
	if !b.IsContiguous() {
		b, err = b.Contiguous()
		if err != nil {
			return nil, err
		}
	}
	outShape, err := a.Shape().Broadcast(b.Shape())
	if err != nil {
		return nil, err
	}
	out, err := tensor.New(tensor.Float64, outShape.Dims())
	if err != nil {
		return nil, err
	}
	it, err := iterator.NewIterator(
		iterator.InputSpec{Shape: a.Shape().Dims(), Strides: a.Strides()},
		iterator.InputSpec{Shape: b.Shape().Dims(), Strides: b.Strides()},
		iterator.InputSpec{Shape: outShape.Dims(), Strides: out.Strides()},
	)
	if err != nil {
		return nil, err
	}
	x := a.Float64()
	y := b.Float64()
	z := out.Float64()
	for it.Next() {
		z[it.InputOffset(2)] = fn(x[it.InputOffset(0)], y[it.InputOffset(1)])
	}
	return out, nil
}
