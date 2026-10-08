// Package iterator implements the broadcasting execution iterator: an
// odometer over the output shape with O(1) amortized offset updates
// per input, plus a contiguous fast-path detector.
package iterator

import (
	"github.com/astrovox/astrovox/internal/errors"
	"github.com/astrovox/astrovox/tensor/broadcast"
)

// InputSpec describes one input tensor's shape and element strides.
type InputSpec struct {
	Shape   []int
	Strides []int
}

// Iterator traverses every element of the broadcast output shape,
// yielding the corresponding input offsets for each input.
type Iterator struct {
	shape      []int
	rank       int
	inStride   [][]int
	idx        []int
	inOff      []int
	outOff     int
	outStrides []int
	done       bool
	total      int
	visited    int
}

// NewIterator builds an execution plan over the given inputs,
// broadcasting them to a common output shape.
func NewIterator(inputs ...InputSpec) (*Iterator, error) {
	if len(inputs) == 0 {
		return nil, errors.New(errors.CodeInvalidArgument, "iterator requires at least one input")
	}
	shapes := make([][]int, len(inputs))
	for i, in := range inputs {
		if len(in.Shape) != len(in.Strides) {
			return nil, errors.New(errors.CodeInvalidArgument, "shape/stride rank mismatch").
				WithField("input", i)
		}
		shapes[i] = in.Shape
	}
	out, err := broadcast.OutputShape(shapes...)
	if err != nil {
		return nil, err
	}
	it := &Iterator{
		shape:      out,
		rank:       len(out),
		inStride:   make([][]int, len(inputs)),
		outStrides: broadcast.RowMajorStrides(out),
		total:      numel(out),
	}
	for i, in := range inputs {
		strides, err := broadcast.BroadcastStrides(in.Shape, in.Strides, out)
		if err != nil {
			return nil, err
		}
		it.inStride[i] = strides
	}
	if it.rank > 0 {
		it.idx = make([]int, it.rank)
	}
	it.inOff = make([]int, len(inputs))
	return it, nil
}

// Shape returns the broadcast output shape.
func (it *Iterator) Shape() []int { return it.shape }

// NumInputs returns the number of inputs.
func (it *Iterator) NumInputs() int { return len(it.inStride) }

// Total returns the total number of elements to visit.
func (it *Iterator) Total() int { return it.total }

// Reset rewinds the iterator to the first element.
func (it *Iterator) Reset() {
	for i := range it.idx {
		it.idx[i] = 0
	}
	for i := range it.inOff {
		it.inOff[i] = 0
	}
	it.outOff = 0
	it.done = it.total == 0
	it.visited = 0
}

// Next advances to the next element. Returns false when exhausted.
func (it *Iterator) Next() bool {
	if it.done {
		return false
	}
	if it.visited > 0 {
		if !it.advance() {
			it.done = true
			return false
		}
	}
	it.visited++
	return true
}

// advance increments the odometer and updates offsets incrementally.
func (it *Iterator) advance() bool {
	for d := it.rank - 1; d >= 0; d-- {
		it.idx[d]++
		if it.idx[d] < it.shape[d] {
			step := it.outStrides[d]
			it.outOff += step
			for i := range it.inOff {
				it.inOff[i] += it.inStride[i][d]
			}
			return true
		}
		it.idx[d] = 0
		roll := it.outStrides[d] * (it.shape[d] - 1)
		it.outOff -= roll
		for i := range it.inOff {
			it.inOff[i] -= it.inStride[i][d] * (it.shape[d] - 1)
		}
	}
	return false
}

// InputOffset returns the current element offset for input i.
func (it *Iterator) InputOffset(i int) int {
	if i < 0 || i >= len(it.inOff) {
		return 0
	}
	return it.inOff[i]
}

// OutputOffset returns the current element offset in the output.
func (it *Iterator) OutputOffset() int { return it.outOff }

// Index returns the current multi-dimensional output index.
func (it *Iterator) Index() []int { return it.idx }

// Contiguous reports whether the iteration plan admits a linear
// fast path: all inputs and the output are contiguous with identical
// shape, so offsets advance by 1.
func (it *Iterator) Contiguous() bool {
	for _, strides := range it.inStride {
		for d, s := range strides {
			if s != it.outStrides[d] {
				return false
			}
		}
	}
	return true
}

func numel(shape []int) int {
	n := 1
	for _, d := range shape {
		if d <= 0 {
			return 0
		}
		n *= d
	}
	return n
}
