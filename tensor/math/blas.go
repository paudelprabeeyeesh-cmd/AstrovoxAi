package math

import (
	"math"

	"github.com/astrovox/astrovox/internal/errors"
	"github.com/astrovox/astrovox/tensor"
)

// Axpy computes y = alpha*x + y (BLAS Level 1).
func Axpy(alpha float64, x, y *tensor.Tensor) error {
	if x == nil || y == nil {
		return errors.New(errors.CodeInvalidArgument, "nil tensor")
	}
	if x.Shape().Rank() != 1 || y.Shape().Rank() != 1 || x.Shape().Dim(0) != y.Shape().Dim(0) {
		return errors.New(errors.CodeShapeMismatch, "axpy length mismatch")
	}
	xv := x.Float64()
	yv := y.Float64()
	for i := range xv {
		yv[i] += alpha * xv[i]
	}
	return nil
}

// Dot computes the inner product of two 1-D float64 tensors.
func Dot(x, y *tensor.Tensor) (float64, error) {
	if x == nil || y == nil {
		return 0, errors.New(errors.CodeInvalidArgument, "nil tensor")
	}
	if x.Shape().Rank() != 1 || y.Shape().Rank() != 1 {
		return 0, errors.New(errors.CodeInvalidArgument, "dot requires 1-D tensors")
	}
	if x.Shape().Dim(0) != y.Shape().Dim(0) {
		return 0, errors.New(errors.CodeShapeMismatch, "dot length mismatch")
	}
	return VecDot(x.Float64(), y.Float64())
}

// Nrm2 returns the L2 norm of a 1-D tensor.
func Nrm2(x *tensor.Tensor) (float64, error) {
	if x == nil {
		return 0, errors.New(errors.CodeInvalidArgument, "nil tensor")
	}
	if x.Shape().Rank() != 1 {
		return 0, errors.New(errors.CodeInvalidArgument, "nrm2 requires 1-D tensor")
	}
	xv := x.Float64()
	var scale float64
	var ssq float64 = 1
	for _, v := range xv {
		if v == 0 {
			continue
		}
		av := math.Abs(v)
		if scale < av {
			ssq = 1 + ssq*(scale/av)*(scale/av)
			scale = av
		} else {
			ssq += (av / scale) * (av / scale)
		}
	}
	return scale * math.Sqrt(ssq), nil
}

// Scal computes x = alpha*x in place.
func Scal(alpha float64, x *tensor.Tensor) error {
	if x == nil {
		return errors.New(errors.CodeInvalidArgument, "nil tensor")
	}
	if x.Shape().Rank() != 1 {
		return errors.New(errors.CodeInvalidArgument, "scal requires 1-D tensor")
	}
	xv := x.Float64()
	for i := range xv {
		xv[i] *= alpha
	}
	return nil
}

// Swap exchanges the contents of two 1-D tensors.
func Swap(x, y *tensor.Tensor) error {
	if x == nil || y == nil {
		return errors.New(errors.CodeInvalidArgument, "nil tensor")
	}
	if x.Shape().Rank() != 1 || y.Shape().Rank() != 1 || x.Shape().Dim(0) != y.Shape().Dim(0) {
		return errors.New(errors.CodeShapeMismatch, "swap length mismatch")
	}
	xv := x.Float64()
	yv := y.Float64()
	for i := range xv {
		xv[i], yv[i] = yv[i], xv[i]
	}
	return nil
}

// Copy overwrites dst with src (1-D, same length).
func Copy(dst, src *tensor.Tensor) error {
	if dst == nil || src == nil {
		return errors.New(errors.CodeInvalidArgument, "nil tensor")
	}
	if dst.Shape().Rank() != 1 || src.Shape().Rank() != 1 || dst.Shape().Dim(0) != src.Shape().Dim(0) {
		return errors.New(errors.CodeShapeMismatch, "copy length mismatch")
	}
	copy(dst.Float64(), src.Float64())
	return nil
}

// Gemv computes y = alpha*A*x + beta*y (BLAS Level 2).
func Gemv(transA bool, alpha float64, A, x, y *tensor.Tensor, beta float64) error {
	if A == nil || x == nil || y == nil {
		return errors.New(errors.CodeInvalidArgument, "nil tensor")
	}
	if A.Shape().Rank() != 2 || x.Shape().Rank() != 1 || y.Shape().Rank() != 1 {
		return errors.New(errors.CodeInvalidArgument, "gemv rank mismatch")
	}
	rows := A.Shape().Dim(0)
	cols := A.Shape().Dim(1)
	if transA {
		rows, cols = cols, rows
	}
	if x.Shape().Dim(0) != cols || y.Shape().Dim(0) != rows {
		return errors.New(errors.CodeShapeMismatch, "gemv shape mismatch")
	}
	a := A.Float64()
	xv := x.Float64()
	yv := y.Float64()
	for i := range yv {
		yv[i] *= beta
	}
	for i := 0; i < rows; i++ {
		var acc float64
		for j := 0; j < cols; j++ {
			var av float64
			if transA {
				av = a[j*cols+i]
			} else {
				av = a[i*cols+j]
			}
			acc += av * xv[j]
		}
		yv[i] += alpha * acc
	}
	return nil
}

// Ger computes A = alpha*x*yᵀ (BLAS Level 2 rank-1 update).
func Ger(alpha float64, x, y, A *tensor.Tensor) error {
	if x == nil || y == nil || A == nil {
		return errors.New(errors.CodeInvalidArgument, "nil tensor")
	}
	if x.Shape().Rank() != 1 || y.Shape().Rank() != 1 || A.Shape().Rank() != 2 {
		return errors.New(errors.CodeInvalidArgument, "ger rank mismatch")
	}
	if A.Shape().Dim(0) != x.Shape().Dim(0) || A.Shape().Dim(1) != y.Shape().Dim(0) {
		return errors.New(errors.CodeShapeMismatch, "ger shape mismatch")
	}
	a := A.Float64()
	xv := x.Float64()
	yv := y.Float64()
	for i := range xv {
		for j := range yv {
			a[i*len(yv)+j] += alpha * xv[i] * yv[j]
		}
	}
	return nil
}
