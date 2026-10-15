// Package autograd implements reverse-mode automatic
// differentiation over the tensor package: a dynamic
// tape recording differentiable operations, gradient
// accumulation, and classical optimizers.
package autograd

import (
	"github.com/astrovox/astrovox/internal/errors"
	"github.com/astrovox/astrovox/tensor"
	"github.com/astrovox/astrovox/tensor/ops"
)

// Variable is a differentiable value: a tensor plus
// its accumulated gradient and its backward rule.
type Variable struct {
	Value    *tensor.Tensor
	Grad     *tensor.Tensor
	requires bool
	backward func(g *tensor.Tensor) error
	// Creator marks whether this variable was produced
	// by an operation (true) or supplied as a leaf (false).
	Creator bool
}

// NewVariable creates a leaf variable.
func NewVariable(v *tensor.Tensor, requiresGrad bool) *Variable {
	return &Variable{Value: v, requires: requiresGrad}
}

// RequiresGrad reports whether gradients are tracked.
func (v *Variable) RequiresGrad() bool { return v.requires }

// ZeroGrad clears the accumulated gradient.
func (v *Variable) ZeroGrad() { v.Grad = nil }

// Detach returns a leaf copy of v that shares its value but
// is not tracked, cutting v out of any tape it belonged to.
// Use it to freeze a value produced by a differentiable op,
// for example a constant embedding extracted from a model.
func (v *Variable) Detach() *Variable {
	return &Variable{Value: v.Value, requires: false}
}

// AccumGrad adds g to the accumulated gradient.
func (v *Variable) AccumGrad(g *tensor.Tensor) error {
	if !v.requires {
		return nil
	}
	if v.Grad == nil {
		v.Grad = g
		return nil
	}
	sum, err := ops.Add(v.Grad, g)
	if err != nil {
		return errors.Wrap(err, errors.CodeInvalidArgument, "gradient accumulation")
	}
	v.Grad = sum
	return nil
}

// Tape is the reverse-mode execution trace. It records
// every operation that produced a tracked variable,
// in forward order. A tape represents one forward pass.
//
// A tape is single-use. Replaying it is refused rather
// than allowed to accumulate gradients twice or to
// differentiate against values an optimizer has since
// replaced: both failures are silent, and a silent wrong
// gradient is worse than a loud one. Reset clears the
// nodes and the consumed flag, so a fresh pass may reuse
// the same tape object.
type Tape struct {
	nodes []*Variable
	done  bool
}

// NewTape creates an empty tape.
func NewTape() *Tape { return &Tape{} }

// Record appends a produced variable to the tape.
func (t *Tape) Record(v *Variable) {
	if v != nil && v.Creator {
		t.nodes = append(t.nodes, v)
	}
}

// Reset clears the tape for a new pass.
func (t *Tape) Reset() { t.nodes = nil; t.done = false }

// Len returns the number of recorded nodes.
func (t *Tape) Len() int { return len(t.nodes) }

// Backward propagates the seed gradient through the
// tape in reverse order, accumulating gradients on
// tracked variables. A nil seed defaults to ones.
// Intermediate node gradients are taken from the
// gradients accumulated by their consumers.
//
// Failure semantics:
//   - A recorded node with no gradient rule is an error: the
//     operation is unsupported, so its gradient is unknown and
//     skipping it would silently return a wrong (zero) gradient
//     while claiming success.
//   - A node no consumer reached contributes zero: that is the
//     correct gradient of an unreachable branch, and it is what
//     makes a detached (stop-gradient) path usable.
//   - A tape is single-use: replaying it is refused rather than
//     allowed to accumulate gradients twice or to differentiate
//     against values an optimizer has since replaced.
func (t *Tape) Backward(seed *tensor.Tensor) error {
	if t.done {
		return errors.New(errors.CodeInvalidArgument,
			"tape already consumed: a second backward would double-accumulate or differentiate stale values")
	}
	t.done = true
	last := len(t.nodes) - 1
	for i := last; i >= 0; i-- {
		node := t.nodes[i]
		var g *tensor.Tensor
		switch {
		case i == last && seed != nil:
			g = seed
		case node.Grad != nil:
			g = node.Grad
		case i == last:
			// dL/dL = 1 for the loss node when no seed is given.
			ones, err := tensor.Ones(node.Value.DType(), node.Value.Shape().Dims())
			if err != nil {
				return errors.Wrap(err, errors.CodeInternal, "seed allocation")
			}
			g = ones
		default:
			// No consumer produced a gradient: the branch is
			// unreachable (for example behind a Detach), and the
			// true gradient of an unreachable node is zero.
			zeros, err := tensor.Zeros(node.Value.DType(), node.Value.Shape().Dims())
			if err != nil {
				return errors.Wrap(err, errors.CodeInternal, "zero gradient allocation")
			}
			g = zeros
		}
		if node.backward == nil {
			// Refuse instead of skipping: a silently zero gradient
			// claims an operation is differentiable when it is not.
			return errors.New(errors.CodeUnimplemented,
				"recorded operation has no gradient rule").
				WithField("node", i)
		}
		if err := node.backward(g); err != nil {
			return errors.Wrap(err, errors.CodeInternal, "backward pass").
				WithField("node", i)
		}
	}
	return nil
}
