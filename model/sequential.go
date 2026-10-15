package model

import (
	"fmt"

	"github.com/astrovox/astrovox/autograd"
	"github.com/astrovox/astrovox/internal/errors"
)

// Sequential chains modules in order. It is a container, not a copy:
// the child modules own their parameters, and Sequential reports them in
// chain order so optimizer state ordering is stable.
type Sequential struct {
	name    string
	modules []Module
}

// Compile-time interface satisfaction.
var _ Module = (*Sequential)(nil)

// NewSequential builds a sequential container.
func NewSequential(name string, modules ...Module) (*Sequential, error) {
	if len(modules) == 0 {
		return nil, errors.New(errors.CodeInvalidArgument, "sequential requires at least one module")
	}
	for i, m := range modules {
		if m == nil {
			return nil, errors.New(errors.CodeInvalidArgument, "nil module").
				WithField("index", i)
		}
	}
	return &Sequential{name: name, modules: append([]Module(nil), modules...)}, nil
}

// Name implements Module.
func (s *Sequential) Name() string { return s.name }

// Modules exposes the children, in order.
func (s *Sequential) Modules() []Module { return s.modules }

// Parameters implements Module.
func (s *Sequential) Parameters() []*autograd.Variable {
	var out []*autograd.Variable
	for _, m := range s.modules {
		out = append(out, m.Parameters()...)
	}
	return out
}

// NamedParameters implements Module: the container itself contributes no
// parameters; Flatten recurses into children.
func (s *Sequential) NamedParameters() []Parameter { return nil }

// Forward implements Module, applying each child in order.
func (s *Sequential) Forward(tape *autograd.Tape, x *autograd.Variable) (*autograd.Variable, error) {
	cur := x
	for _, m := range s.modules {
		out, err := m.Forward(tape, cur)
		if err != nil {
			return nil, errors.Wrap(err, errors.CodeInvalidArgument, "sequential forward").
				WithField("module", m.Name())
		}
		cur = out
	}
	return cur, nil
}

// MLP is a stack of linear layers with a shared activation between them
// and no activation on the output. It is the deterministic demonstration
// model used by the end-to-end acceptance scenario.
type MLP struct {
	seq *Sequential
}

// Compile-time interface satisfaction.
var _ Module = (*MLP)(nil)

// NewMLP builds an MLP with layer sizes dims[0] -> dims[1] -> ... ->
// dims[n-1]. Activation applies to every hidden layer output; the output
// layer stays linear so the model can represent regression targets of
// either sign.
func NewMLP(name string, dims []int, act Activation, seed int64) (*MLP, error) {
	if len(dims) < 2 {
		return nil, errors.New(errors.CodeInvalidArgument,
			"MLP requires at least an input and an output size")
	}
	for i, d := range dims {
		if d <= 0 {
			return nil, errors.New(errors.CodeInvalidArgument, "MLP sizes must be positive").
				WithField("index", i).WithField("size", d)
		}
	}
	modules := make([]Module, 0, len(dims)-1)
	for i := 0; i+1 < len(dims); i++ {
		l, err := NewLinear(fmt.Sprintf("fc%d", i), dims[i], dims[i+1], seed+int64(i)*7919)
		if err != nil {
			return nil, err
		}
		if i+2 < len(dims) {
			// Hidden layer: wrap the linear layer with its activation.
			a := act
			modules = append(modules, &activated{linear: l, act: a})
			continue
		}
		modules = append(modules, l)
	}
	seq, err := NewSequential(name, modules...)
	if err != nil {
		return nil, err
	}
	return &MLP{seq: seq}, nil
}

// Name implements Module.
func (m *MLP) Name() string { return m.seq.Name() }

// Parameters implements Module.
func (m *MLP) Parameters() []*autograd.Variable { return m.seq.Parameters() }

// NamedParameters implements Module.
func (m *MLP) NamedParameters() []Parameter { return nil }

// Forward implements Module.
func (m *MLP) Forward(tape *autograd.Tape, x *autograd.Variable) (*autograd.Variable, error) {
	return m.seq.Forward(tape, x)
}

// Modules exposes the underlying sequence.
func (m *MLP) Modules() []Module { return m.seq.Modules() }

// activated pairs a module with an activation applied to its output.
// It is transparent for parameter naming: the wrapper is the layer, so
// parameters keep the layer's name and the activation stays a property
// of the module rather than a path segment.
type activated struct {
	linear *Linear
	act    Activation
}

// Name implements Module.
func (a *activated) Name() string { return a.linear.Name() }

// Parameters implements Module.
func (a *activated) Parameters() []*autograd.Variable { return a.linear.Parameters() }

// NamedParameters implements Module.
func (a *activated) NamedParameters() []Parameter { return a.linear.NamedParameters() }

// Forward implements Module.
func (a *activated) Forward(tape *autograd.Tape, x *autograd.Variable) (*autograd.Variable, error) {
	h, err := a.linear.Forward(tape, x)
	if err != nil {
		return nil, err
	}
	return applyActivation(tape, a.act, h)
}
