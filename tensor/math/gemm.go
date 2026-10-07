// Package math provides the Astrovox math library: BLAS-like
// operations, tiled GEMM, SIMD-dispatched kernels, convolution,
// and FFT, all built on the tensor core.
package math

import (
	"github.com/astrovox/astrovox/internal/errors"
	"github.com/astrovox/astrovox/tensor"
)

// GEMM computes C = alpha*op(A)*op(B) + beta*C for 2-D
// float64 tensors, where op(X) is X or Xᵀ, using
// cache-blocked tiling (MC×NC×KC blocks).
func GEMM(transA, transB bool, alpha float64, A, B *tensor.Tensor, beta float64, C *tensor.Tensor) error {
	if A == nil || B == nil || C == nil {
		return errors.New(errors.CodeInvalidArgument, "nil tensor in GEMM")
	}
	if A.DType() != tensor.Float64 || B.DType() != tensor.Float64 || C.DType() != tensor.Float64 {
		return errors.New(errors.CodeDTypeMismatch, "GEMM requires float64")
	}
	if A.Shape().Rank() != 2 || B.Shape().Rank() != 2 || C.Shape().Rank() != 2 {
		return errors.New(errors.CodeInvalidArgument, "GEMM requires 2-D tensors")
	}
	// Stored layout: A stored [ar, ac] with leading dim ac;
	// B stored [br, bc] with leading dim bc.
	ar, ac := A.Shape().Dim(0), A.Shape().Dim(1)
	br, bc := B.Shape().Dim(0), B.Shape().Dim(1)
	var m, kA, kB, n int
	if transA {
		kA, m = ar, ac
	} else {
		m, kA = ar, ac
	}
	if transB {
		n, kB = br, bc
	} else {
		kB, n = br, bc
	}
	if kA != kB {
		return errors.New(errors.CodeShapeMismatch, "GEMM contracting dims mismatch").
			WithField("k_a", kA).WithField("k_b", kB)
	}
	if C.Shape().Dim(0) != m || C.Shape().Dim(1) != n {
		return errors.New(errors.CodeShapeMismatch, "GEMM output shape mismatch").
			WithField("got", C.Shape().String()).
			WithField("want", "["+itoa(m)+" "+itoa(n)+"]")
	}
	if !A.IsContiguous() || !B.IsContiguous() || !C.IsContiguous() {
		return errors.New(errors.CodeInvalidArgument, "GEMM requires contiguous tensors")
	}
	a := A.Float64()
	b := B.Float64()
	c := C.Float64()
	gemmBlocked(transA, transB, alpha, a, ac, b, bc, beta, c, m, n, kA)
	return nil
}

// gemmBlocked executes the tiled GEMM with block sizes
// derived from a fixed cache-hierarchy model (L2-class).
func gemmBlocked(transA, transB bool, alpha float64,
	a []float64, lda int, b []float64, ldb int,
	beta float64, c []float64, m, n, k int) {
	const mc = 96
	const nc = 256
	const kc = 256
	for ii := 0; ii < m; ii += mc {
		iEnd := min(ii+mc, m)
		for jj := 0; jj < n; jj += nc {
			jEnd := min(jj+nc, n)
			for p := 0; p < k; p += kc {
				pEnd := min(p+kc, k)
				for i := ii; i < iEnd; i++ {
					for j := jj; j < jEnd; j++ {
						var acc float64
						for q := p; q < pEnd; q++ {
							var av, bv float64
							if transA {
								av = a[q*lda+i]
							} else {
								av = a[i*lda+q]
							}
							if transB {
								bv = b[j*ldb+q]
							} else {
								bv = b[q*ldb+j]
							}
							acc += av * bv
						}
						idx := i*n + j
						if beta == 0 {
							c[idx] = alpha * acc
						} else {
							c[idx] = alpha*acc + beta*c[idx]
						}
					}
				}
			}
		}
	}
}

// MatMul computes the matrix product of two 2-D tensors.
func MatMul(A, B *tensor.Tensor) (*tensor.Tensor, error) {
	if A == nil || B == nil {
		return nil, errors.New(errors.CodeInvalidArgument, "nil tensor")
	}
	if A.Shape().Rank() != 2 || B.Shape().Rank() != 2 {
		return nil, errors.New(errors.CodeInvalidArgument, "matmul requires 2-D tensors")
	}
	m := A.Shape().Dim(0)
	k := A.Shape().Dim(1)
	if B.Shape().Dim(0) != k {
		return nil, errors.New(errors.CodeShapeMismatch, "matmul contracting dims mismatch")
	}
	n := B.Shape().Dim(1)
	out, err := tensor.New(tensor.Float64, []int{m, n})
	if err != nil {
		return nil, err
	}
	if err := GEMM(false, false, 1, A, B, 0, out); err != nil {
		return nil, err
	}
	return out, nil
}

// BatchMatMul computes batched matrix products over leading
// batch dimensions.
func BatchMatMul(A, B *tensor.Tensor) (*tensor.Tensor, error) {
	if A == nil || B == nil {
		return nil, errors.New(errors.CodeInvalidArgument, "nil tensor")
	}
	if A.Shape().Rank() < 3 || B.Shape().Rank() != A.Shape().Rank() {
		return nil, errors.New(errors.CodeInvalidArgument, "batch matmul requires equal rank >= 3")
	}
	rank := A.Shape().Rank()
	batch := 1
	for i := 0; i < rank-2; i++ {
		if A.Shape().Dim(i) != B.Shape().Dim(i) {
			return nil, errors.New(errors.CodeShapeMismatch, "batch dims mismatch")
		}
		batch *= A.Shape().Dim(i)
	}
	m := A.Shape().Dim(rank - 2)
	k := A.Shape().Dim(rank - 1)
	if B.Shape().Dim(rank-2) != k {
		return nil, errors.New(errors.CodeShapeMismatch, "batch matmul contracting dims mismatch")
	}
	n := B.Shape().Dim(rank - 1)
	outShape := make([]int, rank)
	for i := 0; i < rank-2; i++ {
		outShape[i] = A.Shape().Dim(i)
	}
	outShape[rank-2] = m
	outShape[rank-1] = n
	out, err := tensor.New(tensor.Float64, outShape)
	if err != nil {
		return nil, err
	}
	a := A.Float64()
	b := B.Float64()
	c := out.Float64()
	for i := 0; i < batch; i++ {
		aBatch := a[i*m*k : (i+1)*m*k]
		bBatch := b[i*k*n : (i+1)*k*n]
		cBatch := c[i*m*n : (i+1)*m*n]
		gemmBlocked(false, false, 1, aBatch, k, bBatch, n, 0, cBatch, m, n, k)
	}
	return out, nil
}

// MatVec computes A * x for a 2-D matrix and 1-D vector.
func MatVec(A, x *tensor.Tensor) (*tensor.Tensor, error) {
	if A == nil || x == nil {
		return nil, errors.New(errors.CodeInvalidArgument, "nil tensor")
	}
	if A.Shape().Rank() != 2 || x.Shape().Rank() != 1 {
		return nil, errors.New(errors.CodeInvalidArgument, "matvec requires 2-D x 1-D")
	}
	m := A.Shape().Dim(0)
	k := A.Shape().Dim(1)
	if x.Shape().Dim(0) != k {
		return nil, errors.New(errors.CodeShapeMismatch, "matvec length mismatch")
	}
	out, err := tensor.New(tensor.Float64, []int{m})
	if err != nil {
		return nil, err
	}
	a := A.Float64()
	xv := x.Float64()
	ov := out.Float64()
	for i := 0; i < m; i++ {
		var acc float64
		for j := 0; j < k; j++ {
			acc += a[i*k+j] * xv[j]
		}
		ov[i] = acc
	}
	return out, nil
}

func min(a, b int) int {
	if a < b {
		return a
	}
	return b
}

func itoa(n int) string {
	if n == 0 {
		return "0"
	}
	neg := n < 0
	if neg {
		n = -n
	}
	var buf [20]byte
	pos := len(buf)
	for n > 0 {
		pos--
		buf[pos] = byte('0' + n%10)
		n /= 10
	}
	if neg {
		pos--
		buf[pos] = '-'
	}
	return string(buf[pos:])
}
