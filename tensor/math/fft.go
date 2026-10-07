package math

import (
	"math"
	"math/bits"

	"github.com/astrovox/astrovox/internal/errors"
	"github.com/astrovox/astrovox/tensor"
)

// FFT computes the 1-D complex-to-complex radix-2 Cooley-Tukey
// FFT of a float64 tensor, zero-padding to the next power of
// two. The result is returned as a complex128-valued tensor.
func FFT(x *tensor.Tensor, inverse bool) (*tensor.Tensor, error) {
	if x == nil {
		return nil, errors.New(errors.CodeInvalidArgument, "nil tensor")
	}
	if x.Shape().Rank() != 1 {
		return nil, errors.New(errors.CodeInvalidArgument, "FFT requires 1-D tensor")
	}
	n := x.Shape().Dim(0)
	if n < 1 {
		return nil, errors.New(errors.CodeInvalidArgument, "FFT requires non-empty tensor")
	}
	padded := nextPow2(n)
	work := make([]complex128, padded)
	xv := x.Float64()
	for i := 0; i < n; i++ {
		work[i] = complex(xv[i], 0)
	}
	fft(work, inverse)
	out, err := tensor.New(tensor.Complex128, []int{padded})
	if err != nil {
		return nil, err
	}
	ov := out.Complex128()
	copy(ov, work)
	return out, nil
}

// FFT2 computes the 2-D FFT of a rank-2 tensor by composing
// 1-D FFTs over rows and columns.
func FFT2(x *tensor.Tensor, inverse bool) (*tensor.Tensor, error) {
	if x == nil {
		return nil, errors.New(errors.CodeInvalidArgument, "nil tensor")
	}
	if x.Shape().Rank() != 2 {
		return nil, errors.New(errors.CodeInvalidArgument, "FFT2 requires rank-2 tensor")
	}
	h := x.Shape().Dim(0)
	w := x.Shape().Dim(1)
	ph := nextPow2(h)
	pw := nextPow2(w)
	rows := make([]complex128, ph*pw)
	xv := x.Float64()
	for i := 0; i < h; i++ {
		for j := 0; j < w; j++ {
			rows[i*pw+j] = complex(xv[i*w+j], 0)
		}
	}
	rowBuf := make([]complex128, pw)
	for i := 0; i < ph; i++ {
		copy(rowBuf, rows[i*pw:(i+1)*pw])
		fft(rowBuf, inverse)
		copy(rows[i*pw:(i+1)*pw], rowBuf)
	}
	colBuf := make([]complex128, ph)
	for j := 0; j < pw; j++ {
		for i := 0; i < ph; i++ {
			colBuf[i] = rows[i*pw+j]
		}
		fft(colBuf, inverse)
		for i := 0; i < ph; i++ {
			rows[i*pw+j] = colBuf[i]
		}
	}
	out, err := tensor.New(tensor.Complex128, []int{ph, pw})
	if err != nil {
		return nil, err
	}
	ov := out.Complex128()
	copy(ov, rows)
	return out, nil
}

// RFFT computes the real-input FFT and returns the packed
// half-spectrum (N/2+1 complex values for even N).
func RFFT(x *tensor.Tensor) (*tensor.Tensor, error) {
	full, err := FFT(x, false)
	if err != nil {
		return nil, err
	}
	n := full.Shape().Dim(0)
	half := n/2 + 1
	out, err := tensor.New(tensor.Complex128, []int{half})
	if err != nil {
		return nil, err
	}
	src := full.Complex128()
	dst := out.Complex128()
	copy(dst, src[:half])
	return out, nil
}

// fft performs the in-place iterative radix-2 FFT.
func fft(x []complex128, inverse bool) {
	n := len(x)
	if n <= 1 {
		return
	}
	// Bit-reversal permutation.
	for i, j := 1, 0; i < n; i++ {
		bit := n >> 1
		for ; j&bit != 0; bit >>= 1 {
			j ^= bit
		}
		j |= bit
		if i < j {
			x[i], x[j] = x[j], x[i]
		}
	}
	sign := -1.0
	if inverse {
		sign = 1.0
	}
	for size := 2; size <= n; size <<= 1 {
		half := size >> 1
		angle := sign * 2 * math.Pi / float64(size)
		wStep := complex(math.Cos(angle), math.Sin(angle))
		for start := 0; start < n; start += size {
			w := complex(1, 0)
			for i := 0; i < half; i++ {
				even := x[start+i]
				odd := x[start+i+half] * w
				x[start+i] = even + odd
				x[start+i+half] = even - odd
				w *= wStep
			}
		}
	}
	if inverse {
		scale := 1 / float64(n)
		for i := range x {
			x[i] *= complex(scale, 0)
		}
	}
}

// nextPow2 returns the smallest power of two >= n.
func nextPow2(n int) int {
	if n <= 1 {
		return 1
	}
	return 1 << (bits.Len(uint(n-1)))
}

// IsPow2 reports whether n is a positive power of two.
func IsPow2(n int) bool { return n > 0 && n&(n-1) == 0 }

// DCT computes the type-II discrete cosine transform via the
// FFT (zero-padded even extension).
func DCT(x *tensor.Tensor) (*tensor.Tensor, error) {
	if x == nil {
		return nil, errors.New(errors.CodeInvalidArgument, "nil tensor")
	}
	n := x.Shape().Dim(0)
	if n < 1 {
		return nil, errors.New(errors.CodeInvalidArgument, "DCT requires non-empty tensor")
	}
	// Even extension: y = [x[0..n-1], x[n-1]..x[0]] of length 2n.
	ext := make([]float64, 2*n)
	xv := x.Float64()
	copy(ext, xv)
	for i := 0; i < n; i++ {
		ext[n+i] = xv[n-1-i]
	}
	extT, err := tensor.New(tensor.Float64, []int{2 * n})
	if err != nil {
		return nil, err
	}
	copy(extT.Float64(), ext)
	spec, err := FFT(extT, false)
	if err != nil {
		return nil, err
	}
	out, err := tensor.New(tensor.Float64, []int{n})
	if err != nil {
		return nil, err
	}
	src := spec.Complex128()
	dst := out.Float64()
	for k := 0; k < n; k++ {
		dst[k] = real(src[k]) / math.Sqrt(float64(2*n))
	}
	return out, nil
}
