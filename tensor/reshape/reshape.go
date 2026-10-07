// Package reshape implements reshape shape inference and zero-copy
// feasibility analysis for row-major tensors.
package reshape

import (
	"github.com/astrovox/astrovox/internal/errors"
)

// InferShape computes the target shape for a reshape where exactly one
// dimension may be -1 (inferred from the element count).
func InferShape(oldShape, newShape []int) ([]int, error) {
	total := 1
	for _, d := range oldShape {
		if d < 0 {
			return nil, errors.New(errors.CodeInvalidArgument, "source shape has negative dim")
		}
		total *= d
	}
	inferAt := -1
	prod := 1
	for i, d := range newShape {
		if d == -1 {
			if inferAt >= 0 {
				return nil, errors.New(errors.CodeInvalidArgument, "at most one -1 dimension allowed")
			}
			inferAt = i
			continue
		}
		if d < 0 {
			return nil, errors.New(errors.CodeInvalidArgument, "negative dimension other than -1")
		}
		prod *= d
	}
	if inferAt >= 0 {
		if prod == 0 || total%prod != 0 {
			return nil, errors.New(errors.CodeInvalidArgument, "cannot infer dimension").
				WithField("total", total).WithField("known_product", prod)
		}
		newShape = append([]int(nil), newShape...)
		newShape[inferAt] = total / prod
		prod *= newShape[inferAt]
	}
	if prod != total {
		return nil, errors.New(errors.CodeShapeMismatch, "reshape changes element count").
			WithField("old_numel", total).WithField("new_numel", prod)
	}
	return newShape, nil
}

// CanView reports whether a tensor with oldShape/oldStrides can be
// reshaped to newShape without copying: the existing memory layout
// must already satisfy row-major strides for the new shape.
func CanView(oldShape, oldStrides, newShape []int) bool {
	if len(oldShape) == 0 || len(newShape) == 0 {
		return true
	}
	rank := len(newShape)
	if len(oldShape) < rank {
		rank = len(oldShape)
	}
	newStrides := expectedStrides(newShape)
	oldPos := len(oldShape) - 1
	for d := rank - 1; d >= 0; d-- {
		size := newShape[d]
		stride := newStrides[d]
		if size == 1 {
			continue
		}
		if oldPos < 0 {
			return false
		}
		if oldShape[oldPos] == size {
			if oldStrides[oldPos] != stride {
				return false
			}
			oldPos--
			continue
		}
		merged := oldShape[oldPos]
		mergedStride := oldStrides[oldPos]
		ok := oldStrides[oldPos] == stride
		oldPos--
		for ok && oldPos >= 0 && merged < size {
			if oldStrides[oldPos] != merged*mergedStride {
				ok = false
				break
			}
			merged *= oldShape[oldPos]
			oldPos--
		}
		if !ok || merged != size {
			return false
		}
	}
	return true
}

// FlattenDims returns the shape produced by flattening dimensions
// [start, end) into one.
func FlattenDims(shape []int, start, end int) ([]int, error) {
	if start < 0 || end > len(shape) || start > end {
		return nil, errors.New(errors.CodeInvalidArgument, "invalid flatten range").
			WithField("start", start).WithField("end", end).WithField("rank", len(shape))
	}
	if start == end {
		return append([]int(nil), shape...), nil
	}
	merged := 1
	for i := start; i < end; i++ {
		merged *= shape[i]
	}
	out := make([]int, 0, len(shape)-(end-start)+1)
	out = append(out, shape[:start]...)
	out = append(out, merged)
	out = append(out, shape[end:]...)
	return out, nil
}

func expectedStrides(shape []int) []int {
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
