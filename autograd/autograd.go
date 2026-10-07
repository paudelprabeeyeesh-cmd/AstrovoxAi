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
// in forward order. A tape represents one forward
// pass; Backward may be called exactly once per pass.
type Tape struct {
	nodes []*Variable
}

// NewTape creates an empty tape.
func NewTape() *Tape { return &Tape{} }

// Record appends a produced variable to the tape.
func (t *Tape) Record(v *Variable) {
	if v != nil && v.Creator {
		t.nodes = append(t.nodes, v)
	}
}

// Reset clears the tape.
func (t *Tape) Reset() { t.nodes = nil }

// Len returns the number of recorded nodes.
func (t *Tape) Len() int { return len(t.nodes) }

// Backward propagates the seed gradient through the
// tape in reverse order, accumulating gradients on
// tracked variables. A nil seed defaults to ones.
// Intermediate node gradients are taken from the
// gradients accumulated by their consumers.
func (t *Tape) Backward(seed *tensor.Tensor) error {
	for i := len(t.nodes) - 1; i >= 0; i-- {
		node := t.nodes[i]
		g := seed
		if i != len(t.nodes)-1 || g == nil {
			if node.Grad != nil {
				g = node.Grad
			} else {
				ones, err := tensor.Ones(node.Value.DType(), node.Value.Shape().Dims())
				if err != nil {
					return errors.Wrap(err, errors.CodeInternal, "seed allocation")
				}
				g = ones
			}
		}
		if node.backward == nil {
			continue
		}
		if err := node.backward(g); err != nil {
			return errors.Wrap(err, errors.CodeInternal, "backward pass").
				WithField("node", i)
		}
	}
	return nil
}
