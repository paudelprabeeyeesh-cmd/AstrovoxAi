package autograd

import (
	"math"

	"github.com/astrovox/astrovox/internal/errors"
	"github.com/astrovox/astrovox/tensor/ops"
)

// GradNorm returns the L2 norm of the concatenated gradients of the
// given variables. Variables without gradients contribute zero, so the
// norm is well defined before the first backward pass too (it is 0).
//
// The norm is computed in float64 from the stored gradient values; it is
// a monitoring quantity, not a kernel, so it favors clarity over speed.
func GradNorm(vars []*Variable) (float64, error) {
	var sumSquares float64
	for _, v := range vars {
		if v == nil || v.Grad == nil {
			continue
		}
		for _, g := range v.Grad.Float64() {
			sumSquares += g * g
		}
	}
	if math.IsInf(sumSquares, 1) {
		return math.Inf(1), nil
	}
	return math.Sqrt(sumSquares), nil
}

// ClipGradients scales the gradients of the given variables so their
// global L2 norm is at most maxNorm, and returns the norm before
// clipping. Gradients are modified in place; the returned norm lets a
// caller record the pre-clip value.
//
// Variables without gradients are skipped. A non-finite or non-positive
// maxNorm is a configuration error: clipping to a NaN threshold would
// silently destroy every gradient.
func ClipGradients(vars []*Variable, maxNorm float64) (float64, error) {
	if math.IsNaN(maxNorm) || maxNorm <= 0 {
		return 0, errors.New(errors.CodeInvalidArgument,
			"gradient clip threshold must be positive").
			WithField("max_norm", maxNorm)
	}
	norm, err := GradNorm(vars)
	if err != nil {
		return 0, err
	}
	if math.IsNaN(norm) || math.IsInf(norm, 1) {
		// A non-finite gradient norm means the backward pass already
		// produced garbage. Zeroing is the documented policy here: the
		// caller's step is skipped in the trainer, which surfaces the
		// event rather than corrupting parameters.
		for _, v := range vars {
			if v == nil || v.Grad == nil {
				continue
			}
			for i := range v.Grad.Float64() {
				v.Grad.Float64()[i] = 0
			}
		}
		return norm, nil
	}
	if norm <= maxNorm {
		return norm, nil
	}
	scale := maxNorm / norm
	for _, v := range vars {
		if v == nil || v.Grad == nil {
			continue
		}
		scaled, err := ops.Scale(v.Grad, scale)
		if err != nil {
			return norm, errors.Wrap(err, errors.CodeInternal, "clip scale")
		}
		v.Grad = scaled
	}
	return norm, nil
}

// GradNumel reports the element count of the variable's gradient, or 0
// when no gradient has been accumulated. Useful in training logs.
func (v *Variable) GradNumel() int {
	if v == nil || v.Grad == nil {
		return 0
	}
	return v.Grad.NumElements()
}
