// Package model provides typed neural-network building blocks on top of
// the tensor core and the autograd tape.
//
// A model is parameters plus a forward function: it owns no hidden
// global state, every layer keeps its own weights, and forward always
// takes the tape explicitly so a caller controls which pass a graph
// belongs to. Linear weight layout is [in, out], so the forward pass is
// a plain x @ W + b with no transposed views and the autograd adjoints
// flow directly to the stored parameters.
package model

import (
	"github.com/astrovox/astrovox/autograd"
	"github.com/astrovox/astrovox/internal/errors"
)

// Parameter is a named trainable variable.
type Parameter struct {
	// Name is the hierarchical name, e.g. "mlp.fc1.W".
	Name string
	Var  *autograd.Variable
}

// Module is a composable differentiable component.
//
// Forward appends to tape when tape is non-nil and returns the result
// variable. Modules train sequentially by construction and carry no
// internal locking; sharing a module across goroutines is the caller's
// responsibility, as with parameter tensors themselves.
type Module interface {
	// Forward applies the module to x.
	Forward(tape *autograd.Tape, x *autograd.Variable) (*autograd.Variable, error)
	// Parameters returns the module's trainable variables in a stable
	// order, so optimizer state and checkpoints are reproducible.
	Parameters() []*autograd.Variable
	// NamedParameters returns the same variables with stable names.
	NamedParameters() []Parameter
	// Name identifies the module in traces and checkpoints.
	Name() string
}

// Flatten walks a module tree and returns every parameter exactly once,
// with hierarchical names. A variable reachable twice is an error: shared
// modules would duplicate parameter state under two names and silently
// corrupt checkpoint round-trips.
func Flatten(m Module) ([]Parameter, error) {
	var out []Parameter
	seen := map[*autograd.Variable]string{}
	if err := flatten(m, "", seen, &out); err != nil {
		return nil, err
	}
	return out, nil
}

func flatten(m Module, prefix string, seen map[*autograd.Variable]string, out *[]Parameter) error {
	full := prefix + m.Name()
	for _, p := range m.NamedParameters() {
		if prev, ok := seen[p.Var]; ok {
			return errors.New(errors.CodeInvalidArgument,
				"a parameter is reachable twice in the module tree").
				WithField("name", full+"."+p.Name).
				WithField("also_under", prev)
		}
		seen[p.Var] = full + "." + p.Name
		p.Name = full + "." + p.Name
		*out = append(*out, p)
	}
	// Recurse through any container exposing children, so nesting is not
	// limited to one container type.
	if c, ok := m.(interface{ Modules() []Module }); ok {
		for _, child := range c.Modules() {
			if err := flatten(child, full+".", seen, out); err != nil {
				return err
			}
		}
	}
	return nil
}
