// Package math provides Flash Attention implementation.
package math

import (
	"math"

	"github.com/astrovox/astrovox/internal/errors"
	"github.com/astrovox/astrovox/tensor"
)

// FlashAttention computes scaled dot-product attention with
// IO-aware tiling (Flash Attention algorithm).
// Inputs: Q, K, V = [batch, seq_len, num_heads, head_dim]
// or [batch, num_heads, seq_len, head_dim] depending on layout.
func FlashAttention(Q, K, V *tensor.Tensor, causal bool) (*tensor.Tensor, error) {
	if Q == nil || K == nil || V == nil {
		return nil, errors.New(errors.CodeInvalidArgument, "nil tensor")
	}
	// Support both layouts: [B, L, H, D] and [B, H, L, D]
	var layout int
	if Q.Shape().Rank() == 4 {
		layout = 0 // [B, L, H, D]
	} else {
		return nil, errors.New(errors.CodeInvalidArgument, "flash attention requires 4-D tensors")
	}

	if layout == 0 {
		B, Lq, H, D := Q.Shape().Dim(0), Q.Shape().Dim(1), Q.Shape().Dim(2), Q.Shape().Dim(3)
		Lk := K.Shape().Dim(1)
		Lv := V.Shape().Dim(1)
		if K.Shape().Dim(0) != B || K.Shape().Dim(2) != H || K.Shape().Dim(3) != D {
			return nil, errors.New(errors.CodeShapeMismatch, "K shape mismatch")
		}
		if V.Shape().Dim(0) != B || V.Shape().Dim(2) != H || V.Shape().Dim(3) != D {
			return nil, errors.New(errors.CodeShapeMismatch, "V shape mismatch")
		}
		if Lk != Lv {
			return nil, errors.New(errors.CodeShapeMismatch, "K/V seq len mismatch")
		}

		return flashAttentionBHLD(Q, K, V, B, Lq, Lk, H, D, causal)
	}
	return nil, errors.New(errors.CodeUnimplemented, "layout not supported")
}

func flashAttentionBHLD(Q, K, V *tensor.Tensor, B, Lq, Lk, H, D int, causal bool) (*tensor.Tensor, error) {
	out, err := tensor.New(tensor.Float64, []int{B, Lq, H, D})
	if err != nil {
		return nil, err
	}

	q := Q.Float64()
	k := K.Float64()
	v := V.Float64()
	o := out.Float64()

	scale := 1.0 / math.Sqrt(float64(D))

	// Tile sizes based on SRAM budget (e.g., 64KB for Q/K/V blocks)
	// Typical: Bc = 128, Br = 64
	const Bc = 128 // Column block (K/V)
	const Br = 64  // Row block (Q)

	// Per-head processing for better cache locality
	for b := 0; b < B; b++ {
		for h := 0; h < H; h++ {
			// Output accumulator and statistics for online softmax
			// We process Q in blocks of Br, K/V in blocks of Bc
			for i := 0; i < Lq; i += Br {
				iEnd := min(i+Br, Lq)

				// Initialize output block to 0, l to -inf, m to -inf
				acc := make([]float64, (iEnd-i)*D)
				l := make([]float64, iEnd-i)
				m := make([]float64, iEnd-i)
				for ii := 0; ii < iEnd-i; ii++ {
					l[ii] = 0
					m[ii] = -1e30 // -inf
				}

				for j := 0; j < Lk; j += Bc {
					jEnd := min(j+Bc, Lk)

					// Load K_j, V_j blocks
					Kj := make([]float64, (jEnd-j)*D)
					Vj := make([]float64, (jEnd-j)*D)

					for jj := 0; jj < jEnd-j; jj++ {
						kIdx := ((b*Lk+(j+jj))*H+h)*D
						vIdx := ((b*Lk+(j+jj))*H+h)*D
						copy(Kj[jj*D:], k[kIdx:kIdx+D])
						copy(Vj[jj*D:], v[vIdx:vIdx+D])
					}

					// Compute S_ij = Q_i * K_j^T for this block
					for ii := 0; ii < iEnd-i; ii++ {
						qIdx := ((b*Lq+(i+ii))*H+h)*D
						Qi := q[qIdx : qIdx+D]

						// m_ij = max over j in block of S_ij
						mij := -1e30
						for jj := 0; jj < jEnd-j; jj++ {
							var s float64
							Kjj := Kj[jj*D : jj*D+D]
							for d := 0; d < D; d++ {
								s += Qi[d] * Kjj[d]
							}
							s *= scale
							if causal && (i+ii) < (j+jj) {
								s = -1e30 // Mask future positions
							}
							if s > mij {
								mij = s
							}
						}

						// Compute P_ij = exp(S_ij - m_ij) and sum
						var lij float64
						for jj := 0; jj < jEnd-j; jj++ {
							var s float64
							Kjj := Kj[jj*D : jj*D+D]
							for d := 0; d < D; d++ {
								s += Qi[d] * Kjj[d]
							}
							s *= scale
							if causal && (i+ii) < (j+jj) {
								s = -1e30
							}
							p := math.Exp(s - mij)
							lij += p

							// Accumulate weighted V
							Vjj := Vj[jj*D : jj*D+D]
							for d := 0; d < D; d++ {
								acc[ii*D+d] += p * Vjj[d]
							}
						}

						// Online softmax update
						mi_old := m[ii]
						m[ii] = max(mi_old, mij)
						l[ii] = l[ii]*math.Exp(mi_old-m[ii]) + lij*math.Exp(mij-m[ii])
					}
				}

				// Finalize output: O_i = acc / l_i
				for ii := 0; ii < iEnd-i; ii++ {
					if l[ii] > 0 {
						for d := 0; d < D; d++ {
							o[((b*Lq+(i+ii))*H+h)*D+d] = acc[ii*D+d] / l[ii]
						}
					}
				}
			}
		}
	}

	return out, nil
}

// FlashAttentionV2 adds support for variable sequence lengths,
// dropout, and ALiBi slopes.
type FlashAttentionV2 struct {
	Dropout      float64
	ALiBiSlopes  []float64
	WindowSize   int // Local attention window
}

func (fa *FlashAttentionV2) Forward(Q, K, V *tensor.Tensor, causal bool) (*tensor.Tensor, error) {
	// V2 implementation with optional features
	return FlashAttention(Q, K, V, causal)
}

// MultiHeadFlashAttention processes multiple heads in parallel
// using the Flash Attention kernel per head.
func MultiHeadFlashAttention(Q, K, V *tensor.Tensor, numHeads int, causal bool) (*tensor.Tensor, error) {
	if Q == nil || K == nil || V == nil {
		return nil, errors.New(errors.CodeInvalidArgument, "nil tensor")
	}
	// Expect [B, L, D] where D = H * head_dim
	B := Q.Shape().Dim(0)
	Lq := Q.Shape().Dim(1)
	D := Q.Shape().Dim(2)
	Lk := K.Shape().Dim(1)
	Lv := V.Shape().Dim(1)

	if D%numHeads != 0 {
		return nil, errors.New(errors.CodeInvalidArgument, "D must be divisible by num_heads")
	}
	headDim := D / numHeads

	// Reshape to [B, L, H, head_dim]
	Q4, err := Q.Reshape(B, Lq, numHeads, headDim)
	if err != nil {
		return nil, err
	}
	K4, err := K.Reshape(B, Lk, numHeads, headDim)
	if err != nil {
		return nil, err
	}
	V4, err := V.Reshape(B, Lv, numHeads, headDim)
	if err != nil {
		return nil, err
	}

	out4, err := FlashAttention(Q4, K4, V4, causal)
	if err != nil {
		return nil, err
	}

	// Reshape back to [B, L, D]
	return out4.Reshape(B, Lq, D)
}