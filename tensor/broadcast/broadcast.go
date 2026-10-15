// Package broadcast implements shape reconciliation for broadcasting:
// right-aligned dimension matching with size-1 expansion, producing
// stride-0 virtual expansion without materialization.
package broadcast

import (
	"fmt"

	"github.com/astrovox/astrovox/internal/errors"
)

// BroadcastShapes reconciles two shapes under NumPy broadcasting rules:
// dimensions are aligned from the right; sizes must be equal or one
// of them must be 1 (or absent).
func BroadcastShapes(a, b []int) ([]int, error) {
	rank := len(a)
	if len(b) > rank {
		rank = len(b)
	}
	out := make([]int, rank)
	for i := 0; i < rank; i++ {
		// i counts from the right; the output slot is mirrored to the
		// left. Writing out[i] instead of out[rank-1-i] reverses the
		// output whenever the ranks differ, which is precisely the case
		// broadcasting exists for.
		idx := rank - 1 - i
		da := dimAt(a, i)
		db := dimAt(b, i)
		switch {
		case da == db:
			out[idx] = da
		case da == 1:
			out[idx] = db
		case db == 1:
			out[idx] = da
		default:
			return nil, errors.New(errors.CodeShapeMismatch, "dimensions not broadcastable").
				WithField("a", fmt.Sprint(a)).
				WithField("b", fmt.Sprint(b)).
				WithField("dim", idx).
				WithField("a_size", da).
				WithField("b_size", db)
		}
	}
	return out, nil
}

// OutputShape computes the N-way broadcast shape of all input shapes.
func OutputShape(shapes ...[]int) ([]int, error) {
	if len(shapes) == 0 {
		return nil, nil
	}
	out := shapes[0]
	for _, s := range shapes[1:] {
		var err error
		out, err = BroadcastShapes(out, s)
		if err != nil {
			return nil, err
		}
	}
	return out, nil
}

// BroadcastStrides computes per-dimension element strides for a tensor
// of the given shape and strides, virtually expanded to target.
// Broadcast dimensions receive stride 0 (no allocation).
func BroadcastStrides(shape, strides, target []int) ([]int, error) {
	if len(shape) > len(target) {
		return nil, errors.New(errors.CodeShapeMismatch, "shape rank exceeds target rank")
	}
	out := make([]int, len(target))
	offset := len(target) - len(shape)
	for i := range target {
		if i < offset {
			out[i] = 0
			continue
		}
		si := i - offset
		if shape[si] == target[i] {
			out[i] = strides[si]
		} else if shape[si] == 1 && target[i] != 1 {
			out[i] = 0
		} else if target[i] == 1 {
			out[i] = 0
		} else {
			return nil, errors.New(errors.CodeShapeMismatch, "cannot broadcast dimension").
				WithField("dim", i).
				WithField("size", shape[si]).
				WithField("target", target[i])
		}
	}
	return out, nil
}

// IsBroadcast reports whether shape is virtually expanded in target.
func IsBroadcast(shape, target []int) bool {
	if len(shape) == len(target) {
		for i := range shape {
			if shape[i] != target[i] {
				return true
			}
		}
		return false
	}
	return true
}

// ExpandStrides returns the strides of shape virtually expanded to
// target, assuming row-major contiguous input.
func ExpandStrides(shape, target []int) ([]int, error) {
	strides := RowMajorStrides(shape)
	return BroadcastStrides(shape, strides, target)
}

// RowMajorStrides computes element strides for a row-major shape.
func RowMajorStrides(shape []int) []int {
	rank := len(shape)
	strides := make([]int, rank)
	acc := 1
	for i := rank - 1; i >= 0; i-- {
		strides[i] = acc
		if shape[i] > 0 {
			acc *= shape[i]
		}
	}
	return strides
}

func dimAt(shape []int, fromRight int) int {
	i := len(shape) - 1 - fromRight
	if i < 0 {
		return 1
	}
	return shape[i]
}
