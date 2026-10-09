// Package math provides fused activation kernels.
package math

import (
	"math"

	"github.com/astrovox/astrovox/internal/errors"
	"github.com/astrovox/astrovox/tensor"
)

// ActivationType represents the activation function.
type ActivationType int

const (
	ActReLU ActivationType = iota
	ActGELU
	ActSiLU
	ActSwish
	ActMish
	ActTanh
	ActSigmoid
	ActGeLUApprox
	ActHardSwish
	ActHardSigmoid
	ActELU
	ActLeakyReLU
	ActReLU6
)

// FusedActApply applies an activation function in-place.
// Supports fused multiply-add-activate patterns.
func FusedActApply(x *tensor.Tensor, act ActivationType, alpha, beta float64) error {
	if x == nil {
		return errors.New(errors.CodeInvalidArgument, "nil tensor")
	}
	if x.DType() != tensor.Float64 {
		return errors.New(errors.CodeDTypeMismatch, "fused act requires float64")
	}

	xv := x.Float64()
	n := len(xv)

	switch act {
	case ActReLU:
		for i := 0; i < n; i++ {
			v := alpha*xv[i] + beta
			if v < 0 {
				v = 0
			}
			xv[i] = v
		}
	case ActGELU:
		for i := 0; i < n; i++ {
			v := alpha*xv[i] + beta
			// GELU: x * Phi(x) where Phi is CDF of standard normal
			cdf := 0.5 * (1 + math.Erf(v/math.Sqrt2))
			xv[i] = v * cdf
		}
	case ActSiLU:
		for i := 0; i < n; i++ {
			v := alpha*xv[i] + beta
			// SiLU/Swish: x * sigmoid(x)
			sig := 1.0 / (1.0 + math.Exp(-v))
			xv[i] = v * sig
		}
	case ActSwish:
		for i := 0; i < n; i++ {
			v := alpha*xv[i] + beta
			sig := 1.0 / (1.0 + math.Exp(-v))
			xv[i] = v * sig
		}
	case ActMish:
		for i := 0; i < n; i++ {
			v := alpha*xv[i] + beta
			// Mish: x * tanh(softplus(x))
			sp := math.Log1p(math.Exp(v))
			xv[i] = v * math.Tanh(sp)
		}
	case ActTanh:
		for i := 0; i < n; i++ {
			v := alpha*xv[i] + beta
			xv[i] = math.Tanh(v)
		}
	case ActSigmoid:
		for i := 0; i < n; i++ {
			v := alpha*xv[i] + beta
			xv[i] = 1.0 / (1.0 + math.Exp(-v))
		}
	case ActGeLUApprox:
		for i := 0; i < n; i++ {
			v := alpha*xv[i] + beta
			// Fast GELU approximation: 0.5 * x * (1 + tanh(sqrt(2/pi) * (x + 0.044715 * x^3)))
			const k = 0.7978845608028654 // sqrt(2/pi)
			x3 := v * v * v
			t := math.Tanh(k * (v + 0.044715*x3))
			xv[i] = 0.5 * v * (1 + t)
		}
	case ActHardSwish:
		for i := 0; i < n; i++ {
			v := alpha*xv[i] + beta
			// Hard Swish: x * ReLU6(x+3) / 6
			h := v + 3
			if h < 0 {
				h = 0
			} else if h > 6 {
				h = 6
			}
			xv[i] = v * h / 6
		}
	case ActHardSigmoid:
		for i := 0; i < n; i++ {
			v := alpha*xv[i] + beta
			// Hard Sigmoid: ReLU6(x+3) / 6
			h := v + 3
			if h < 0 {
				h = 0
			} else if h > 6 {
				h = 6
			}
			xv[i] = h / 6
		}
	case ActELU:
		for i := 0; i < n; i++ {
			v := alpha*xv[i] + beta
			if v < 0 {
				v = math.Exp(v) - 1
			}
			xv[i] = v
		}
	case ActLeakyReLU:
		for i := 0; i < n; i++ {
			v := alpha*xv[i] + beta
			if v < 0 {
				v = 0.01 * v // alpha=0.01
			}
			xv[i] = v
		}
	case ActReLU6:
		for i := 0; i < n; i++ {
			v := alpha*xv[i] + beta
			if v < 0 {
				v = 0
			} else if v > 6 {
				v = 6
			}
			xv[i] = v
		}
	default:
		return errors.New(errors.CodeInvalidArgument, "unknown activation").WithField("act", act)
	}

	return nil
}

// FusedLinearAct computes y = act(x @ W^T + b) in a fused kernel.
// x: [M, K], W: [N, K], b: [N], out: [M, N]
func FusedLinearAct(x, W, b *tensor.Tensor, out *tensor.Tensor, act ActivationType) error {
	if x == nil || W == nil || out == nil {
		return errors.New(errors.CodeInvalidArgument, "nil tensor")
	}
	if x.DType() != tensor.Float64 || W.DType() != tensor.Float64 || out.DType() != tensor.Float64 {
		return errors.New(errors.CodeDTypeMismatch, "fused linear act requires float64")
	}
	if x.Shape().Rank() != 2 || W.Shape().Rank() != 2 || out.Shape().Rank() != 2 {
		return errors.New(errors.CodeInvalidArgument, "requires 2-D tensors")
	}
	M, K := x.Shape().Dim(0), x.Shape().Dim(1)
	N, KW := W.Shape().Dim(0), W.Shape().Dim(1)
	if K != KW {
		return errors.New(errors.CodeShapeMismatch, "contracting dims mismatch")
	}
	if out.Shape().Dim(0) != M || out.Shape().Dim(1) != N {
		return errors.New(errors.CodeShapeMismatch, "out shape mismatch")
	}
	if b != nil {
		if b.Shape().Rank() != 1 || b.Shape().Dim(0) != N {
			return errors.New(errors.CodeShapeMismatch, "bias shape mismatch")
		}
	}

	xv := x.Float64()
	Wv := W.Float64()
	ov := out.Float64()
	var bv []float64
	if b != nil {
		bv = b.Float64()
	}

	// Blocked GEMM + fused activation
	const BM = 64
	const BN = 64
	const BK = 64

	for i := 0; i < M; i += BM {
		iEnd := min(i+BM, M)
		for j := 0; j < N; j += BN {
			jEnd := min(j+BN, N)
			for k := 0; k < K; k += BK {
				kEnd := min(k+BK, K)
				for ii := i; ii < iEnd; ii++ {
					for jj := j; jj < jEnd; jj++ {
						var acc float64
						if k == 0 {
							if bv != nil {
								acc = bv[jj]
							} else {
								acc = 0
							}
						} else {
							acc = ov[ii*N+jj]
						}
						baseX := ii * K
						baseW := jj * K
						for kk := k; kk < kEnd; kk++ {
							acc += xv[baseX+kk] * Wv[baseW+kk]
						}
						ov[ii*N+jj] = acc
					}
				}
			}
			// Apply activation to this output tile
			for ii := i; ii < iEnd; ii++ {
				for jj := j; jj < jEnd; jj++ {
					v := ov[ii*N+jj]
					switch act {
					case ActReLU:
						if v < 0 {
							v = 0
						}
					case ActGELU:
						cdf := 0.5 * (1 + math.Erf(v/math.Sqrt2))
						v = v * cdf
					case ActSiLU, ActSwish:
						sig := 1.0 / (1.0 + math.Exp(-v))
						v = v * sig
					case ActTanh:
						v = math.Tanh(v)
					case ActSigmoid:
						v = 1.0 / (1.0 + math.Exp(-v))
					case ActGeLUApprox:
						const k = 0.7978845608028654
						x3 := v * v * v
						t := math.Tanh(k * (v + 0.044715*x3))
						v = 0.5 * v * (1 + t)
					case ActHardSwish:
						h := v + 3
						if h < 0 {
							h = 0
						} else if h > 6 {
							h = 6
						}
						v = v * h / 6
					}
					ov[ii*N+jj] = v
				}
			}
		}
	}

	return nil
}

// FusedConvAct applies convolution followed by activation.
// Supports 2D convolution + ReLU/GELU/SiLU in one pass.
func FusedConvAct(x, W, b *tensor.Tensor, out *tensor.Tensor,
	strideH, strideW, padH, padW int, act ActivationType) error {
	if x == nil || W == nil || out == nil {
		return errors.New(errors.CodeInvalidArgument, "nil tensor")
	}
	// Use existing Conv2d then apply activation
	_, err := Conv2d(x, W, strideH, strideW, padH, padW, ConvDirect)
	if err != nil {
		return err
	}
	// Add bias if provided
	if b != nil {
		ov := out.Float64()
		bv := b.Float64()
		N, C, OH, OW := out.Shape().Dim(0), out.Shape().Dim(1), out.Shape().Dim(2), out.Shape().Dim(3)
		for n := 0; n < N; n++ {
			for c := 0; c < C; c++ {
				base := ((n*C+c)*OH)*OW
				for i := 0; i < OH*OW; i++ {
					ov[base+i] += bv[c]
				}
			}
		}
	}
	return FusedActApply(out, act, 1, 0)
}

// FusedAddAct computes out = act(x + y) element-wise.
func FusedAddAct(x, y *tensor.Tensor, act ActivationType) (*tensor.Tensor, error) {
	if x == nil || y == nil {
		return nil, errors.New(errors.CodeInvalidArgument, "nil tensor")
	}
	if x.DType() != tensor.Float64 || y.DType() != tensor.Float64 {
		return nil, errors.New(errors.CodeDTypeMismatch, "requires float64")
	}
	if !x.Shape().Equal(y.Shape()) {
		return nil, errors.New(errors.CodeShapeMismatch, "shape mismatch")
	}

	out, err := tensor.New(tensor.Float64, x.Shape().Dims())
	if err != nil {
		return nil, err
	}

	xv := x.Float64()
	yv := y.Float64()
	ov := out.Float64()

	for i := range xv {
		v := xv[i] + yv[i]
		switch act {
		case ActReLU:
			if v < 0 {
				v = 0
			}
		case ActGELU:
			cdf := 0.5 * (1 + math.Erf(v/math.Sqrt2))
			v = v * cdf
		case ActSiLU, ActSwish:
			sig := 1.0 / (1.0 + math.Exp(-v))
			v = v * sig
		case ActTanh:
			v = math.Tanh(v)
		case ActSigmoid:
			v = 1.0 / (1.0 + math.Exp(-v))
		case ActGeLUApprox:
			const k = 0.7978845608028654
			x3 := v * v * v
			t := math.Tanh(k * (v + 0.044715*x3))
			v = 0.5 * v * (1 + t)
		}
		ov[i] = v
	}

	return out, nil
}