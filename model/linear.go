package model

import (
	"math"
	"math/rand"

	"github.com/astrovox/astrovox/autograd"
	"github.com/astrovox/astrovox/internal/errors"
	"github.com/astrovox/astrovox/tensor"
)

// Linear is an affine layer: y = x @ W + b with W of shape [in, out]
// and b of shape [out].
//
// Weights are initialized deterministically from the given seed, so two
// models built with the same seed and shapes are bit-identical and tests
// and checkpoints are reproducible. The seed's sequence is a property of
// the Go toolchain's math/rand; it is stable in practice and is not a
// cross-language or cross-version guarantee.
type Linear struct {
	name        string
	InFeatures  int
	OutFeatures int
	W           *autograd.Variable
	B           *autograd.Variable
}

// Compile-time interface satisfaction.
var _ Module = (*Linear)(nil)

// NewLinear builds a Linear layer with deterministic weight init.
func NewLinear(name string, inFeatures, outFeatures int, seed int64) (*Linear, error) {
	if inFeatures <= 0 || outFeatures <= 0 {
		return nil, errors.New(errors.CodeInvalidArgument,
			"linear layer requires positive feature counts").
			WithField("in", inFeatures).WithField("out", outFeatures)
	}
	wv := make([]float64, inFeatures*outFeatures)
	rng := rand.New(rand.NewSource(seed))
	// LeCun-style uniform init keeps the variance of activations stable
	// through depth.
	limit := 1.0 / math.Sqrt(float64(inFeatures))
	for i := range wv {
		wv[i] = (rng.Float64()*2 - 1) * limit
	}
	w, err := tensor.New(tensor.Float64, []int{inFeatures, outFeatures})
	if err != nil {
		return nil, err
	}
	copy(w.Float64(), wv)
	b, err := tensor.New(tensor.Float64, []int{outFeatures})
	if err != nil {
		return nil, err
	}
	return &Linear{
		name:        name,
		InFeatures:  inFeatures,
		OutFeatures: outFeatures,
		W:           autograd.NewVariable(w, true),
		B:           autograd.NewVariable(b, true),
	}, nil
}

// Name implements Module.
func (l *Linear) Name() string { return l.name }

// Parameters implements Module.
func (l *Linear) Parameters() []*autograd.Variable {
	return []*autograd.Variable{l.W, l.B}
}

// NamedParameters implements Module.
func (l *Linear) NamedParameters() []Parameter {
	return []Parameter{{Name: "W", Var: l.W}, {Name: "b", Var: l.B}}
}

// Forward implements Module. x must be 2-D [batch, inFeatures]; the bias
// is broadcast across the batch, and a mismatched batch width is refused
// rather than silently broadcast to the wrong shape.
func (l *Linear) Forward(tape *autograd.Tape, x *autograd.Variable) (*autograd.Variable, error) {
	if x == nil || x.Value == nil {
		return nil, errors.New(errors.CodeInvalidArgument, "nil input")
	}
	if x.Value.Shape().Rank() != 2 {
		return nil, errors.New(errors.CodeInvalidArgument,
			"linear forward requires a 2-D [batch, in] input").
			WithField("rank", x.Value.Shape().Rank())
	}
	if got := x.Value.Shape().Dim(1); got != l.InFeatures {
		return nil, errors.New(errors.CodeShapeMismatch,
			"linear forward input width mismatch").
			WithField("got", got).WithField("want", l.InFeatures)
	}
	mm, err := autograd.MatMul(tape, x, l.W)
	if err != nil {
		return nil, errors.Wrap(err, errors.CodeInvalidArgument, "linear matmul")
	}
	out, err := autograd.Add(tape, mm, l.B)
	if err != nil {
		return nil, errors.Wrap(err, errors.CodeInvalidArgument, "linear bias")
	}
	return out, nil
}

// Evaluate runs the layer without recording a tape, for inference.
func (l *Linear) Evaluate(x *autograd.Variable) (*autograd.Variable, error) {
	return l.Forward(nil, x)
}

// Activation selects the nonlinearity applied by an activated layer.
type Activation int

// Supported activations.
const (
	ActNone Activation = iota
	ActRelu
	ActTanh
	ActSigmoid
)

// String names the activation for traces and errors.
func (a Activation) String() string {
	switch a {
	case ActNone:
		return "none"
	case ActRelu:
		return "relu"
	case ActTanh:
		return "tanh"
	case ActSigmoid:
		return "sigmoid"
	}
	return "unknown"
}

func applyActivation(tape *autograd.Tape, act Activation, x *autograd.Variable) (*autograd.Variable, error) {
	switch act {
	case ActNone:
		return x, nil
	case ActRelu:
		return autograd.Relu(tape, x)
	case ActTanh:
		return autograd.Tanh(tape, x)
	case ActSigmoid:
		return autograd.Sigmoid(tape, x)
	}
	return nil, errors.New(errors.CodeInvalidArgument, "unknown activation").
		WithField("activation", int(act))
}
