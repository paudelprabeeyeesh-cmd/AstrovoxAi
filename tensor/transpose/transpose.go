// Package transpose implements permutation validation and the
// stride/shape arithmetic for zero-copy transposes and permutes.
package transpose

import (
	"github.com/astrovox/astrovox/internal/errors"
)

// ValidatePerm checks that perm is a bijection over [0, rank).
func ValidatePerm(rank int, perm []int) error {
	if len(perm) != rank {
		return errors.New(errors.CodeInvalidArgument, "permutation length must equal rank").
			WithField("rank", rank).WithField("len", len(perm))
	}
	seen := make([]bool, rank)
	for _, p := range perm {
		if p < 0 || p >= rank {
			return errors.New(errors.CodeInvalidArgument, "permutation index out of range").
				WithField("index", p).WithField("rank", rank)
		}
		if seen[p] {
			return errors.New(errors.CodeInvalidArgument, "permutation is not a bijection").
				WithField("index", p)
		}
		seen[p] = true
	}
	return nil
}

// PermutedShape returns the shape under permutation perm: result dim i
// equals shape[perm[i]].
func PermutedShape(shape, perm []int) []int {
	out := make([]int, len(perm))
	for i, p := range perm {
		out[i] = shape[p]
	}
	return out
}

// PermutedStrides returns the strides under permutation perm.
func PermutedStrides(strides, perm []int) []int {
	out := make([]int, len(perm))
	for i, p := range perm {
		out[i] = strides[p]
	}
	return out
}

// InversePerm returns the inverse permutation.
func InversePerm(perm []int) []int {
	inv := make([]int, len(perm))
	for i, p := range perm {
		inv[p] = i
	}
	return inv
}

// SwapDims returns the permutation swapping d0 and d1.
func SwapDims(rank, d0, d1 int) ([]int, error) {
	if d0 < 0 || d0 >= rank || d1 < 0 || d1 >= rank {
		return nil, errors.New(errors.CodeInvalidArgument, "dimension index out of range").
			WithField("d0", d0).WithField("d1", d1).WithField("rank", rank)
	}
	perm := make([]int, rank)
	for i := range perm {
		perm[i] = i
	}
	perm[d0], perm[d1] = perm[d1], perm[d0]
	return perm, nil
}

// ReversePerm returns the full reversal permutation (d0=0, d1=rank-1
// generalizations for higher ranks reverse all dims).
func ReversePerm(rank int) []int {
	perm := make([]int, rank)
	for i := range perm {
		perm[i] = rank - 1 - i
	}
	return perm
}
