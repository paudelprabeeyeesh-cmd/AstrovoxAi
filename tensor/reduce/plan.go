// Package reduce implements reduction planning: output shape
// computation and traversal plans for dim-masked reductions.
package reduce

import (
	"sort"

	"github.com/astrovox/astrovox/internal/errors"
)

// Plan describes a reduction over the input shape.
type Plan struct {
	InputShape   []int
	OutputShape  []int
	ReduceDims   []int
	KeepDims     bool
	InputStrides []int
	OuterDims    []int
	ReduceSet    []bool
}

// PlanReduction computes the reduction plan for reducing dims (empty
// reduces all dimensions) with optional keep-dim semantics.
func PlanReduction(inputShape []int, dims []int, keepDims bool) (Plan, error) {
	rank := len(inputShape)
	reduceSet := make([]bool, rank)
	if len(dims) == 0 {
		for i := range reduceSet {
			reduceSet[i] = true
		}
		dims = make([]int, rank)
		for i := range dims {
			dims[i] = i
		}
	} else {
		for _, d := range dims {
			if d < 0 || d >= rank {
				return Plan{}, errors.New(errors.CodeInvalidArgument, "reduction dim out of range").
					WithField("dim", d).WithField("rank", rank)
			}
			reduceSet[d] = true
		}
	}
	sorted := append([]int(nil), dims...)
	sort.Ints(sorted)
	outShape := make([]int, 0, rank)
	for i, size := range inputShape {
		if reduceSet[i] {
			if keepDims {
				outShape = append(outShape, 1)
			}
			continue
		}
		outShape = append(outShape, size)
	}
	inputStrides := rowMajorStrides(inputShape)
	outer := make([]int, 0, rank)
	for i := range inputShape {
		if !reduceSet[i] {
			outer = append(outer, i)
		}
	}
	return Plan{
		InputShape:   inputShape,
		OutputShape:  outShape,
		ReduceDims:   sorted,
		KeepDims:     keepDims,
		InputStrides: inputStrides,
		OuterDims:    outer,
		ReduceSet:    reduceSet,
	}, nil
}

// OutputNumElements returns the number of output elements.
func (p Plan) OutputNumElements() int {
	n := 1
	for _, d := range p.OutputShape {
		n *= d
	}
	return n
}

// ReduceNumElements returns the number of elements reduced per output.
func (p Plan) ReduceNumElements() int {
	n := 1
	for _, d := range p.ReduceDims {
		n *= p.InputShape[d]
	}
	return n
}

func rowMajorStrides(shape []int) []int {
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
