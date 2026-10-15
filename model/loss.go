package model

import (
	"github.com/astrovox/astrovox/autograd"
	"github.com/astrovox/astrovox/internal/errors"
)

// MSELoss computes mean((pred - target)^2) over all elements, as a
// differentiable variable on the tape. The gradient wrt pred is
// 2*(pred - target)/n, and the target is treated as a constant.
//
// Mean (not sum) keeps the loss scale independent of batch size, so one
// learning rate is valid across batch sizes.
func MSELoss(tape *autograd.Tape, pred, target *autograd.Variable) (*autograd.Variable, error) {
	if pred == nil || target == nil {
		return nil, errors.New(errors.CodeInvalidArgument, "nil loss argument")
	}
	if !pred.Value.Shape().Equal(target.Value.Shape()) {
		return nil, errors.New(errors.CodeShapeMismatch, "MSE shape mismatch").
			WithField("pred", pred.Value.Shape().String()).
			WithField("target", target.Value.Shape().String())
	}
	diff, err := autograd.Sub(tape, pred, target)
	if err != nil {
		return nil, errors.Wrap(err, errors.CodeInvalidArgument, "mse diff")
	}
	sq, err := autograd.Mul(tape, diff, diff)
	if err != nil {
		return nil, errors.Wrap(err, errors.CodeInvalidArgument, "mse square")
	}
	loss, err := autograd.Mean(tape, sq, nil, false)
	if err != nil {
		return nil, errors.Wrap(err, errors.CodeInvalidArgument, "mse mean")
	}
	return loss, nil
}
