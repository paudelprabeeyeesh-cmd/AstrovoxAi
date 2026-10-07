package autograd

import (
	"github.com/astrovox/astrovox/internal/errors"
	"github.com/astrovox/astrovox/tensor"
	"github.com/astrovox/astrovox/tensor/ops"
)

// Optimizer updates tracked variables from their
// gradients after a backward pass.
type Optimizer interface {
	// Step applies one update to the given variables.
	Step(vars []*Variable) error
	// ZeroGrad clears gradients on the given variables.
	ZeroGrad(vars []*Variable)
}

// SGD is stochastic gradient descent with optional
// momentum and weight decay.
type SGD struct {
	LR          float64
	Momentum    float64
	WeightDecay float64
	velocity    map[*Variable]*tensor.Tensor
}

// NewSGD creates an SGD optimizer.
func NewSGD(lr, momentum float64) (*SGD, error) {
	if lr <= 0 {
		return nil, errors.New(errors.CodeInvalidArgument, "learning rate must be positive").
			WithField("lr", lr)
	}
	return &SGD{LR: lr, Momentum: momentum, velocity: map[*Variable]*tensor.Tensor{}}, nil
}

// Step implements Optimizer.
func (s *SGD) Step(vars []*Variable) error {
	for _, v := range vars {
		if !v.requires || v.Grad == nil {
			continue
		}
		g := v.Grad
		if s.WeightDecay != 0 {
			wd, err := ops.Scale(v.Value, s.WeightDecay)
			if err != nil {
				return errors.Wrap(err, errors.CodeInternal, "weight decay")
			}
			g, err = ops.Add(g, wd)
			if err != nil {
				return errors.Wrap(err, errors.CodeInternal, "weight decay add")
			}
		}
		if s.Momentum != 0 {
			vel, ok := s.velocity[v]
			if !ok {
				z, err := tensor.Zeros(g.DType(), g.Shape().Dims())
				if err != nil {
					return errors.Wrap(err, errors.CodeInternal, "momentum velocity")
				}
				vel = z
				s.velocity[v] = vel
			}
			scaled, err := ops.Scale(vel, s.Momentum)
			if err != nil {
				return errors.Wrap(err, errors.CodeInternal, "momentum scale")
			}
			updated, err := ops.Add(scaled, g)
			if err != nil {
				return errors.Wrap(err, errors.CodeInternal, "momentum")
			}
			s.velocity[v] = updated
			g = updated
		}
		delta, err := ops.Scale(g, -s.LR)
		if err != nil {
			return errors.Wrap(err, errors.CodeInternal, "sgd delta")
		}
		updated, err := ops.Add(v.Value, delta)
		if err != nil {
			return errors.Wrap(err, errors.CodeInternal, "sgd update")
		}
		v.Value = updated
	}
	return nil
}

// ZeroGrad implements Optimizer.
func (s *SGD) ZeroGrad(vars []*Variable) {
	for _, v := range vars {
		v.ZeroGrad()
		delete(s.velocity, v)
	}
}

// Adam is the adaptive moment estimator.
type Adam struct {
	LR          float64
	Beta1       float64
	Beta2       float64
	Eps         float64
	WeightDecay float64
	StepCount   int64
	m           map[*Variable]*tensor.Tensor
	v           map[*Variable]*tensor.Tensor
}

// NewAdam creates an Adam optimizer.
func NewAdam(lr, beta1, beta2, eps float64) (*Adam, error) {
	if lr <= 0 {
		return nil, errors.New(errors.CodeInvalidArgument, "learning rate must be positive").
			WithField("lr", lr)
	}
	if beta1 <= 0 || beta1 >= 1 || beta2 <= 0 || beta2 >= 1 {
		return nil, errors.New(errors.CodeInvalidArgument, "betas must be in (0, 1)").
			WithField("beta1", beta1).WithField("beta2", beta2)
	}
	return &Adam{
		LR: lr, Beta1: beta1, Beta2: beta2, Eps: eps,
		m: map[*Variable]*tensor.Tensor{},
		v: map[*Variable]*tensor.Tensor{},
	}, nil
}

// Step implements Optimizer.
func (a *Adam) Step(vars []*Variable) error {
	a.StepCount++
	bias1 := 1 - pow(a.Beta1, a.StepCount)
	bias2 := 1 - pow(a.Beta2, a.StepCount)
	for _, v := range vars {
		if !v.requires || v.Grad == nil {
			continue
		}
		g := v.Grad
		if a.WeightDecay != 0 {
			wd, err := ops.Scale(v.Value, a.WeightDecay)
			if err != nil {
				return errors.Wrap(err, errors.CodeInternal, "weight decay")
			}
			g, err = ops.Add(g, wd)
			if err != nil {
				return errors.Wrap(err, errors.CodeInternal, "weight decay add")
			}
		}
		m, ok := a.m[v]
		if !ok {
			m, err := tensor.Zeros(g.DType(), g.Shape().Dims())
			if err != nil {
				return errors.Wrap(err, errors.CodeInternal, "adam m")
			}
			a.m[v] = m
		}
		m = a.m[v]
		vv, ok := a.v[v]
		if !ok {
			vv, err := tensor.Zeros(g.DType(), g.Shape().Dims())
			if err != nil {
				return errors.Wrap(err, errors.CodeInternal, "adam v")
			}
			a.v[v] = vv
		}
		vv = a.v[v]
		// m = beta1*m + (1-beta1)*g
		mScaled, err := ops.Scale(m, a.Beta1)
		if err != nil {
			return errors.Wrap(err, errors.CodeInternal, "adam m scale")
		}
		gScaled, err := ops.Scale(g, 1-a.Beta1)
		if err != nil {
			return errors.Wrap(err, errors.CodeInternal, "adam g scale")
		}
		mNew, err := ops.Add(mScaled, gScaled)
		if err != nil {
			return errors.Wrap(err, errors.CodeInternal, "adam m")
		}
		// v = beta2*v + (1-beta2)*g*g
		g2, err := ops.Mul(g, g)
		if err != nil {
			return errors.Wrap(err, errors.CodeInternal, "adam g2")
		}
		vScaled, err := ops.Scale(vv, a.Beta2)
		if err != nil {
			return errors.Wrap(err, errors.CodeInternal, "adam v scale")
		}
		g2Scaled, err := ops.Scale(g2, 1-a.Beta2)
		if err != nil {
			return errors.Wrap(err, errors.CodeInternal, "adam g2 scale")
		}
		vNew, err := ops.Add(vScaled, g2Scaled)
		if err != nil {
			return errors.Wrap(err, errors.CodeInternal, "adam v")
		}
		a.m[v] = mNew
		a.v[v] = vNew
		// bias-corrected moments
		mHat, err := ops.Scale(mNew, 1/bias1)
		if err != nil {
			return errors.Wrap(err, errors.CodeInternal, "adam mhat")
		}
		vHat, err := ops.Scale(vNew, 1/bias2)
		if err != nil {
			return errors.Wrap(err, errors.CodeInternal, "adam vhat")
		}
		// update = -lr * mhat / (sqrt(vhat) + eps)
		denom, err := ops.Sqrt(vHat)
		if err != nil {
			return errors.Wrap(err, errors.CodeInternal, "adam sqrt")
		}
		epsT, err := tensor.Full(v.Grad.DType(), v.Value.Shape().Dims(), a.Eps)
		if err != nil {
			return errors.Wrap(err, errors.CodeInternal, "adam eps")
		}
		denom, err = ops.Add(denom, epsT)
		if err != nil {
			return errors.Wrap(err, errors.CodeInternal, "adam denom")
		}
		ratio, err := ops.Div(mHat, denom)
		if err != nil {
			return errors.Wrap(err, errors.CodeInternal, "adam ratio")
		}
		delta, err := ops.Scale(ratio, -a.LR)
		if err != nil {
			return errors.Wrap(err, errors.CodeInternal, "adam delta")
		}
		updated, err := ops.Add(v.Value, delta)
		if err != nil {
			return errors.Wrap(err, errors.CodeInternal, "adam update")
		}
		v.Value = updated
	}
	return nil
}

// ZeroGrad implements Optimizer.
func (a *Adam) ZeroGrad(vars []*Variable) {
	for _, v := range vars {
		v.ZeroGrad()
		delete(a.m, v)
		delete(a.v, v)
	}
}

// pow computes base^exp for non-negative integer exp.
func pow(base float64, exp int64) float64 {
	result := 1.0
	for i := int64(0); i < exp; i++ {
		result *= base
	}
	return result
}
