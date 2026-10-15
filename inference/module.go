package inference

import (
	"context"

	"github.com/astrovox/astrovox/autograd"
	"github.com/astrovox/astrovox/internal/errors"
	"github.com/astrovox/astrovox/model"
	"github.com/astrovox/astrovox/tensor"
)

// ModuleExecutable adapts a model.Module to Executable. The forward
// pass runs without a tape: inference does not record gradients, so no
// tape is built and no parameters are marked dirty.
//
// Inputs are read from InputKey and the result is written to OutputKey;
// a request missing the input is a typed error, not a zero-filled
// tensor.
type ModuleExecutable struct {
	Module model.Module
}

// Compile-time interface satisfaction.
var _ Executable = (*ModuleExecutable)(nil)

// Forward implements Executable.
func (m *ModuleExecutable) Forward(ctx context.Context, inputs map[string]*tensor.Tensor) (map[string]*tensor.Tensor, error) {
	x, ok := inputs[InputKey]
	if !ok {
		return nil, errors.New(errors.CodeInvalidArgument, "request is missing the input tensor").
			WithField("expected_key", InputKey)
	}
	if x == nil {
		return nil, errors.New(errors.CodeInvalidArgument, "input tensor is nil")
	}
	if err := ctx.Err(); err != nil {
		return nil, errors.Wrap(err, errors.CodeCancelled, "cancelled before forward")
	}
	out, err := m.Module.Forward(nil, autograd.NewVariable(x, false))
	if err != nil {
		return nil, err
	}
	return map[string]*tensor.Tensor{OutputKey: out.Value}, nil
}
