// Package math provides normalization layers.
package math

import (
	"math"

	"github.com/astrovox/astrovox/internal/errors"
	"github.com/astrovox/astrovox/tensor"
)

// LayerNorm normalizes over the last dimension (features).
// Input: [*, D] where D is the normalized dimension.
// Weight and bias are optional, shape [D].
func LayerNorm(x, weight, bias *tensor.Tensor, eps float64) (*tensor.Tensor, error) {
	if x == nil {
		return nil, errors.New(errors.CodeInvalidArgument, "nil tensor")
	}
	if x.DType() != tensor.Float64 {
		return nil, errors.New(errors.CodeDTypeMismatch, "layernorm requires float64")
	}

	rank := x.Shape().Rank()
	D := x.Shape().Dim(rank - 1)
	numel := x.NumElements()
	outer := numel / D

	if weight != nil {
		if weight.Shape().Rank() != 1 || weight.Shape().Dim(0) != D {
			return nil, errors.New(errors.CodeShapeMismatch, "weight shape mismatch")
		}
		if weight.DType() != tensor.Float64 {
			return nil, errors.New(errors.CodeDTypeMismatch, "weight requires float64")
		}
	}
	if bias != nil {
		if bias.Shape().Rank() != 1 || bias.Shape().Dim(0) != D {
			return nil, errors.New(errors.CodeShapeMismatch, "bias shape mismatch")
		}
		if bias.DType() != tensor.Float64 {
			return nil, errors.New(errors.CodeDTypeMismatch, "bias requires float64")
		}
	}

	out, err := tensor.New(tensor.Float64, x.Shape().Dims())
	if err != nil {
		return nil, err
	}

	xv := x.Float64()
	ov := out.Float64()
	wv := weight.Float64()
	bv := bias.Float64()

	// Process each slice of size D
	for i := 0; i < outer; i++ {
		base := i * D

		// Compute mean
		var mean float64
		for d := 0; d < D; d++ {
			mean += xv[base+d]
		}
		mean /= float64(D)

		// Compute variance
		var varSum float64
		for d := 0; d < D; d++ {
			diff := xv[base+d] - mean
			varSum += diff * diff
		}
		variance := varSum / float64(D)

		invStd := 1.0 / math.Sqrt(variance+eps)

		// Normalize and scale/shift
		for d := 0; d < D; d++ {
			norm := (xv[base+d] - mean) * invStd
			if wv != nil {
				norm *= wv[d]
			}
			if bv != nil {
				norm += bv[d]
			}
			ov[base+d] = norm
		}
	}

	return out, nil
}

// LayerNormBackward computes gradients for LayerNorm.
// Returns (dx, dw, db) where dw/db can be nil if weight/bias not provided.
func LayerNormBackward(gradOut, x, weight, bias *tensor.Tensor, eps float64) (*tensor.Tensor, *tensor.Tensor, *tensor.Tensor, error) {
	if gradOut == nil || x == nil {
		return nil, nil, nil, errors.New(errors.CodeInvalidArgument, "nil tensor")
	}
	if gradOut.NumElements() != x.NumElements() {
		return nil, nil, nil, errors.New(errors.CodeShapeMismatch, "grad_out/x shape mismatch")
	}

	rank := x.Shape().Rank()
	D := x.Shape().Dim(rank - 1)
	numel := x.NumElements()
	outer := numel / D

	dx, err := tensor.New(tensor.Float64, x.Shape().Dims())
	if err != nil {
		return nil, nil, nil, err
	}

	var dw, db *tensor.Tensor
	if weight != nil {
		dw, err = tensor.New(tensor.Float64, []int{D})
		if err != nil {
			return nil, nil, nil, err
		}
	}
	if bias != nil {
		db, err = tensor.New(tensor.Float64, []int{D})
		if err != nil {
			return nil, nil, nil, err
		}
	}

	goVal := gradOut.Float64()
	xv := x.Float64()
	dv := dx.Float64()
	wv := weight.Float64()
	var dwv, dbv []float64
	if dw != nil {
		dwv = dw.Float64()
	}
	if db != nil {
		dbv = db.Float64()
	}

	for i := 0; i < outer; i++ {
		base := i * D

		// Compute mean
		var mean float64
		for d := 0; d < D; d++ {
			mean += xv[base+d]
		}
		mean /= float64(D)

		// Compute variance
		var varSum float64
		for d := 0; d < D; d++ {
			diff := xv[base+d] - mean
			varSum += diff * diff
		}
		variance := varSum / float64(D)
		invStd := 1.0 / math.Sqrt(variance+eps)

		// Compute intermediate gradients
		var sumDy float64
		var sumDyX float64
		for d := 0; d < D; d++ {
			dy := goVal[base+d]
			sumDy += dy
			sumDyX += dy * xv[base+d]
		}

		for d := 0; d < D; d++ {
			dy := goVal[base+d]
			xHat := (xv[base+d] - mean) * invStd

			// dx = (dy - sumDy/D - xHat * sumDyX/D) * invStd
			dxVal := (dy - sumDy/float64(D) - xHat*sumDyX/float64(D)) * invStd
			dv[base+d] = dxVal

			// dw = sum over outer of dy * xHat
			if dwv != nil && wv != nil {
				dwv[d] += dy * xHat
			}
			if dbv != nil {
				dbv[d] += dy
			}
		}
	}

	return dx, dw, db, nil
}

// GroupNorm normalizes over groups of channels.
// Input: [N, C, *spatial] where C is divisible by num_groups.
// Weight and bias optional, shape [C].
func GroupNorm(x, weight, bias *tensor.Tensor, numGroups int, eps float64) (*tensor.Tensor, error) {
	if x == nil {
		return nil, errors.New(errors.CodeInvalidArgument, "nil tensor")
	}
	if x.DType() != tensor.Float64 {
		return nil, errors.New(errors.CodeDTypeMismatch, "groupnorm requires float64")
	}
	if x.Shape().Rank() < 3 {
		return nil, errors.New(errors.CodeInvalidArgument, "groupnorm requires rank >= 3 [N, C, ...]")
	}

	N := x.Shape().Dim(0)
	C := x.Shape().Dim(1)
	if C%numGroups != 0 {
		return nil, errors.New(errors.CodeInvalidArgument, "C must be divisible by num_groups")
	}
	channelsPerGroup := C / numGroups

	// Compute spatial dimensions product
	spatial := 1
	for i := 2; i < x.Shape().Rank(); i++ {
		spatial *= x.Shape().Dim(i)
	}
	groupSize := channelsPerGroup * spatial

	if weight != nil {
		if weight.Shape().Rank() != 1 || weight.Shape().Dim(0) != C {
			return nil, errors.New(errors.CodeShapeMismatch, "weight shape mismatch")
		}
	}
	if bias != nil {
		if bias.Shape().Rank() != 1 || bias.Shape().Dim(0) != C {
			return nil, errors.New(errors.CodeShapeMismatch, "bias shape mismatch")
		}
	}

	out, err := tensor.New(tensor.Float64, x.Shape().Dims())
	if err != nil {
		return nil, err
	}

	xv := x.Float64()
	ov := out.Float64()
	wv := weight.Float64()
	bv := bias.Float64()

	// Process each sample and group
	for n := 0; n < N; n++ {
		for g := 0; g < numGroups; g++ {
			// Compute mean over group
			var sum float64
			for c := 0; c < channelsPerGroup; c++ {
				cIdx := g*channelsPerGroup + c
				base := (n*C + cIdx) * spatial
				for s := 0; s < spatial; s++ {
					sum += xv[base+s]
				}
			}
			mean := sum / float64(groupSize)

			// Compute variance
			var varSum float64
			for c := 0; c < channelsPerGroup; c++ {
				cIdx := g*channelsPerGroup + c
				base := (n*C + cIdx) * spatial
				for s := 0; s < spatial; s++ {
					diff := xv[base+s] - mean
					varSum += diff * diff
				}
			}
			variance := varSum / float64(groupSize)
			invStd := 1.0 / math.Sqrt(variance+eps)

			// Normalize
			for c := 0; c < channelsPerGroup; c++ {
				cIdx := g*channelsPerGroup + c
				base := (n*C + cIdx) * spatial
				w := float64(1)
				b := float64(0)
				if wv != nil {
					w = wv[cIdx]
				}
				if bv != nil {
					b = bv[cIdx]
				}
				for s := 0; s < spatial; s++ {
					norm := (xv[base+s] - mean) * invStd
					ov[base+s] = norm*w + b
				}
			}
		}
	}

	return out, nil
}

// GroupNormBackward computes gradients for GroupNorm.
func GroupNormBackward(gradOut, x, weight, bias *tensor.Tensor, numGroups int, eps float64) (*tensor.Tensor, *tensor.Tensor, *tensor.Tensor, error) {
	if gradOut == nil || x == nil {
		return nil, nil, nil, errors.New(errors.CodeInvalidArgument, "nil tensor")
	}

	N := x.Shape().Dim(0)
	C := x.Shape().Dim(1)
	if C%numGroups != 0 {
		return nil, nil, nil, errors.New(errors.CodeInvalidArgument, "C must be divisible by num_groups")
	}
	channelsPerGroup := C / numGroups

	spatial := 1
	for i := 2; i < x.Shape().Rank(); i++ {
		spatial *= x.Shape().Dim(i)
	}
	groupSize := channelsPerGroup * spatial

	dx, err := tensor.New(tensor.Float64, x.Shape().Dims())
	if err != nil {
		return nil, nil, nil, err
	}

	var dw, db *tensor.Tensor
	if weight != nil {
		dw, err = tensor.New(tensor.Float64, []int{C})
		if err != nil {
			return nil, nil, nil, err
		}
	}
	if bias != nil {
		db, err = tensor.New(tensor.Float64, []int{C})
		if err != nil {
			return nil, nil, nil, err
		}
	}

	goVal := gradOut.Float64()
	xv := x.Float64()
	dv := dx.Float64()
	wv := weight.Float64()
	var dwv, dbv []float64
	if dw != nil {
		dwv = dw.Float64()
	}
	if db != nil {
		dbv = db.Float64()
	}

	for n := 0; n < N; n++ {
		for g := 0; g < numGroups; g++ {
			// Compute mean
			var sum float64
			for c := 0; c < channelsPerGroup; c++ {
				cIdx := g*channelsPerGroup + c
				base := (n*C + cIdx) * spatial
				for s := 0; s < spatial; s++ {
					sum += xv[base+s]
				}
			}
			mean := sum / float64(groupSize)

			// Compute variance
			var varSum float64
			for c := 0; c < channelsPerGroup; c++ {
				cIdx := g*channelsPerGroup + c
				base := (n*C + cIdx) * spatial
				for s := 0; s < spatial; s++ {
					diff := xv[base+s] - mean
					varSum += diff * diff
				}
			}
			variance := varSum / float64(groupSize)
			invStd := 1.0 / math.Sqrt(variance+eps)

			// Compute intermediate gradients
			var sumDy float64
			var sumDyX float64
			for c := 0; c < channelsPerGroup; c++ {
				cIdx := g*channelsPerGroup + c
				base := (n*C + cIdx) * spatial
				for s := 0; s < spatial; s++ {
					dy := goVal[base+s]
					sumDy += dy
					sumDyX += dy * xv[base+s]
				}
			}

			for c := 0; c < channelsPerGroup; c++ {
				cIdx := g*channelsPerGroup + c
				base := (n*C + cIdx) * spatial
				for s := 0; s < spatial; s++ {
					dy := goVal[base+s]
					xHat := (xv[base+s] - mean) * invStd

					dxVal := (dy - sumDy/float64(groupSize) - xHat*sumDyX/float64(groupSize)) * invStd
					dv[base+s] = dxVal

					if dwv != nil && wv != nil {
						dwv[cIdx] += dy * xHat
					}
					if dbv != nil {
						dbv[cIdx] += dy
					}
				}
			}
		}
	}

	return dx, dw, db, nil
}

// RMSNorm applies Root Mean Square Layer Normalization.
// Simpler than LayerNorm: no mean subtraction, only RMS scaling.
// x_hat = x / RMS(x) * weight + bias
func RMSNorm(x, weight, bias *tensor.Tensor, eps float64) (*tensor.Tensor, error) {
	if x == nil {
		return nil, errors.New(errors.CodeInvalidArgument, "nil tensor")
	}
	if x.DType() != tensor.Float64 {
		return nil, errors.New(errors.CodeDTypeMismatch, "rmsnorm requires float64")
	}

	rank := x.Shape().Rank()
	D := x.Shape().Dim(rank - 1)
	numel := x.NumElements()
	outer := numel / D

	if weight != nil {
		if weight.Shape().Rank() != 1 || weight.Shape().Dim(0) != D {
			return nil, errors.New(errors.CodeShapeMismatch, "weight shape mismatch")
		}
	}
	if bias != nil {
		if bias.Shape().Rank() != 1 || bias.Shape().Dim(0) != D {
			return nil, errors.New(errors.CodeShapeMismatch, "bias shape mismatch")
		}
	}

	out, err := tensor.New(tensor.Float64, x.Shape().Dims())
	if err != nil {
		return nil, err
	}

	xv := x.Float64()
	ov := out.Float64()
	wv := weight.Float64()
	bv := bias.Float64()

	for i := 0; i < outer; i++ {
		base := i * D

		// Compute RMS
		var sumSq float64
		for d := 0; d < D; d++ {
			sumSq += xv[base+d] * xv[base+d]
		}
		rms := math.Sqrt(sumSq/float64(D) + eps)
		invRms := 1.0 / rms

		for d := 0; d < D; d++ {
			norm := xv[base+d] * invRms
			if wv != nil {
				norm *= wv[d]
			}
			if bv != nil {
				norm += bv[d]
			}
			ov[base+d] = norm
		}
	}

	return out, nil
}
