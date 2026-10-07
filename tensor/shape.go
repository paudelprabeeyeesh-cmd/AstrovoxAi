package tensor

import (
	"fmt"
	"strings"

	"github.com/astrovox/astrovox/internal/errors"
	"github.com/astrovox/astrovox/tensor/broadcast"
)

// MaxRank is the maximum supported tensor rank.
const MaxRank = 16

// Shape is an immutable tensor shape with non-negative dims.
type Shape struct {
	dims []int
}

// NewShape validates and creates a shape.
func NewShape(dims ...int) (Shape, error) {
	if len(dims) > MaxRank {
		return Shape{}, errors.New(errors.CodeInvalidArgument, "rank exceeds maximum").
			WithField("rank", len(dims)).WithField("max", MaxRank)
	}
	for i, d := range dims {
		if d < 0 {
			return Shape{}, errors.New(errors.CodeInvalidArgument, "negative dimension").
				WithField("dim", i).WithField("size", d)
		}
	}
	return Shape{dims: append([]int(nil), dims...)}, nil
}

// MustShape creates a shape, panicking on invalid input.
// Intended for tests and constant construction only.
func MustShape(dims ...int) Shape {
	s, err := NewShape(dims...)
	if err != nil {
		panic(err)
	}
	return s
}

// Dims returns the dimension sizes.
func (s Shape) Dims() []int { return s.dims }

// Dim returns the size of dimension i.
func (s Shape) Dim(i int) int {
	if i < 0 || i >= len(s.dims) {
		return 1
	}
	return s.dims[i]
}

// Rank returns the number of dimensions.
func (s Shape) Rank() int { return len(s.dims) }

// NumElements returns the total element count.
func (s Shape) NumElements() int {
	n := 1
	for _, d := range s.dims {
		if d == 0 {
			return 0
		}
		n *= d
	}
	return n
}

// IsScalar reports whether the shape is rank 0.
func (s Shape) IsScalar() bool { return len(s.dims) == 0 }

// IsVector reports whether the shape is rank 1.
func (s Shape) IsVector() bool { return len(s.dims) == 1 }

// IsMatrix reports whether the shape is rank 2.
func (s Shape) IsMatrix() bool { return len(s.dims) == 2 }

// Equal reports whether two shapes are identical.
func (s Shape) Equal(o Shape) bool {
	if len(s.dims) != len(o.dims) {
		return false
	}
	for i := range s.dims {
		if s.dims[i] != o.dims[i] {
			return false
		}
	}
	return true
}

// String renders the shape as [d0 d1 ... dn].
func (s Shape) String() string {
	if len(s.dims) == 0 {
		return "[]"
	}
	var b strings.Builder
	b.WriteByte('[')
	for i, d := range s.dims {
		if i > 0 {
			b.WriteByte(' ')
		}
		fmt.Fprintf(&b, "%d", d)
	}
	b.WriteByte(']')
	return b.String()
}

// Broadcast returns the shape virtually expanded to target.
func (s Shape) Broadcast(target Shape) (Shape, error) {
	out, err := broadcast.BroadcastShapes(s.dims, target.dims)
	if err != nil {
		return Shape{}, err
	}
	return Shape{dims: out}, nil
}
