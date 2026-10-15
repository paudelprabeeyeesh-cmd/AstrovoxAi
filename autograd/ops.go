package autograd

import (
	"github.com/astrovox/astrovox/internal/errors"
	"github.com/astrovox/astrovox/tensor"
	"github.com/astrovox/astrovox/tensor/ops"
	"github.com/astrovox/astrovox/tensor/reduce"
)

// Add computes the differentiable sum a + b.
func Add(tape *Tape, a, b *Variable) (*Variable, error) {
	out, err := ops.Add(a.Value, b.Value)
	if err != nil {
		return nil, errors.Wrap(err, errors.CodeInvalidArgument, "add")
	}
	v := &Variable{Value: out, requires: a.requires || b.requires, Creator: true}
	v.backward = func(g *tensor.Tensor) error {
		ga, err := broadcastSum(g, a.Value.Shape())
		if err != nil {
			return errors.Wrap(err, errors.CodeInternal, "add grad a")
		}
		gb, err := broadcastSum(g, b.Value.Shape())
		if err != nil {
			return errors.Wrap(err, errors.CodeInternal, "add grad b")
		}
		if a.requires {
			if err := a.AccumGrad(ga); err != nil {
				return err
			}
		}
		if b.requires {
			if err := b.AccumGrad(gb); err != nil {
				return err
			}
		}
		return nil
	}
	if tape != nil {
		tape.Record(v)
	}
	return v, nil
}

// Mul computes the differentiable product a * b.
func Mul(tape *Tape, a, b *Variable) (*Variable, error) {
	out, err := ops.Mul(a.Value, b.Value)
	if err != nil {
		return nil, errors.Wrap(err, errors.CodeInvalidArgument, "mul")
	}
	v := &Variable{Value: out, requires: a.requires || b.requires, Creator: true}
	v.backward = func(g *tensor.Tensor) error {
		ga, err := ops.Mul(g, b.Value)
		if err != nil {
			return errors.Wrap(err, errors.CodeInternal, "mul grad a")
		}
		gb, err := ops.Mul(a.Value, g)
		if err != nil {
			return errors.Wrap(err, errors.CodeInternal, "mul grad b")
		}
		// The un-broadcast must succeed: swallowing its error would
		// accumulate a gradient of the wrong shape, which surfaces much
		// later as a shape error in the optimizer with no link back to
		// the broadcast that caused it.
		if a.requires {
			ga, err = broadcastSum(ga, a.Value.Shape())
			if err != nil {
				return errors.Wrap(err, errors.CodeInternal, "mul grad a broadcast")
			}
			if err := a.AccumGrad(ga); err != nil {
				return err
			}
		}
		if b.requires {
			gb, err = broadcastSum(gb, b.Value.Shape())
			if err != nil {
				return errors.Wrap(err, errors.CodeInternal, "mul grad b broadcast")
			}
			if err := b.AccumGrad(gb); err != nil {
				return err
			}
		}
		return nil
	}
	if tape != nil {
		tape.Record(v)
	}
	return v, nil
}

// Neg computes the differentiable negation -a.
func Neg(tape *Tape, a *Variable) (*Variable, error) {
	out, err := ops.Neg(a.Value)
	if err != nil {
		return nil, errors.Wrap(err, errors.CodeInvalidArgument, "neg")
	}
	v := &Variable{Value: out, requires: a.requires, Creator: true}
	v.backward = func(g *tensor.Tensor) error {
		if !a.requires {
			return nil
		}
		ng, err := ops.Neg(g)
		if err != nil {
			return errors.Wrap(err, errors.CodeInternal, "neg grad")
		}
		return a.AccumGrad(ng)
	}
	if tape != nil {
		tape.Record(v)
	}
	return v, nil
}

// MatMul computes the differentiable matrix product
// A @ B with the standard adjoint rules:
// dL/dA = dL/dY @ Bᵀ, dL/dB = Aᵀ @ dL/dY.
func MatMul(tape *Tape, a, b *Variable) (*Variable, error) {
	out, err := ops.MatMul(a.Value, b.Value)
	if err != nil {
		return nil, errors.Wrap(err, errors.CodeInvalidArgument, "matmul")
	}
	v := &Variable{Value: out, requires: a.requires || b.requires, Creator: true}
	v.backward = func(g *tensor.Tensor) error {
		if a.requires {
			bt, err := b.Value.Transpose(0, 1)
			if err != nil {
				return errors.Wrap(err, errors.CodeInternal, "matmul grad a transpose")
			}
			ga, err := ops.MatMul(g, bt)
			if err != nil {
				return errors.Wrap(err, errors.CodeInternal, "matmul grad a")
			}
			if err := a.AccumGrad(ga); err != nil {
				return err
			}
		}
		if b.requires {
			at, err := a.Value.Transpose(0, 1)
			if err != nil {
				return errors.Wrap(err, errors.CodeInternal, "matmul grad b transpose")
			}
			gb, err := ops.MatMul(at, g)
			if err != nil {
				return errors.Wrap(err, errors.CodeInternal, "matmul grad b")
			}
			if err := b.AccumGrad(gb); err != nil {
				return err
			}
		}
		return nil
	}
	if tape != nil {
		tape.Record(v)
	}
	return v, nil
}

// Sum computes the differentiable sum reduction over
// the given axes. The adjoint scatters the reduced
// gradient back to the input shape by broadcast.
func Sum(tape *Tape, a *Variable, axes []int, keepDims bool) (*Variable, error) {
	out, err := reduce.Sum(a.Value, axes, keepDims)
	if err != nil {
		return nil, errors.Wrap(err, errors.CodeInvalidArgument, "sum")
	}
	v := &Variable{Value: out, requires: a.requires, Creator: true}
	v.backward = func(g *tensor.Tensor) error {
		if !a.requires {
			return nil
		}
		ga, err := expandReducedGrad(g, a.Value.Shape(), axes, keepDims)
		if err != nil {
			return errors.Wrap(err, errors.CodeInternal, "sum grad")
		}
		return a.AccumGrad(ga)
	}
	if tape != nil {
		tape.Record(v)
	}
	return v, nil
}

// expandReducedGrad scatters a reduced gradient back to inputShape.
//
// broadcastSum alone cannot do this: a gradient of shape [2] against
// input [2,3] is ambiguous from the shapes, because [2] could be the
// retained dim 0 or the retained dim 1. The reduction axes disambiguate:
// reduced axes are reinserted as singletons, then virtually expanded.
// The result is materialized so downstream ops read contiguous data.
func expandReducedGrad(g *tensor.Tensor, inputShape tensor.Shape, axes []int, keepDims bool) (*tensor.Tensor, error) {
	rank := inputShape.Rank()
	reduceSet := make([]bool, rank)
	if len(axes) == 0 {
		for i := range reduceSet {
			reduceSet[i] = true
		}
	} else {
		for _, a := range axes {
			if a < 0 || a >= rank {
				return nil, errors.New(errors.CodeInvalidArgument, "reduction axis out of range").
					WithField("axis", a).WithField("rank", rank)
			}
			reduceSet[a] = true
		}
	}
	if keepDims {
		// g already carries singleton axes at the reduced positions.
		e, err := g.Expand(inputShape.Dims()...)
		if err != nil {
			return nil, err
		}
		return e.Contiguous()
	}
	gDims := g.Shape().Dims()
	dims := make([]int, 0, rank)
	gi := 0
	for i := 0; i < rank; i++ {
		if reduceSet[i] {
			dims = append(dims, 1)
			continue
		}
		if gi >= len(gDims) {
			return nil, errors.New(errors.CodeInternal, "reduced gradient is missing a retained dim").
				WithField("grad_shape", g.Shape().String()).
				WithField("input_shape", inputShape.String())
		}
		dims = append(dims, gDims[gi])
		gi++
	}
	r, err := g.Reshape(dims...)
	if err != nil {
		return nil, err
	}
	e, err := r.Expand(inputShape.Dims()...)
	if err != nil {
		return nil, err
	}
	return e.Contiguous()
}

// Sub computes the differentiable difference a - b.
// The adjoint is +g for a and -g for b, each un-broadcast
// to its own shape.
func Sub(tape *Tape, a, b *Variable) (*Variable, error) {
	out, err := ops.Sub(a.Value, b.Value)
	if err != nil {
		return nil, errors.Wrap(err, errors.CodeInvalidArgument, "sub")
	}
	v := &Variable{Value: out, requires: a.requires || b.requires, Creator: true}
	v.backward = func(g *tensor.Tensor) error {
		if a.requires {
			ga, err := broadcastSum(g, a.Value.Shape())
			if err != nil {
				return errors.Wrap(err, errors.CodeInternal, "sub grad a")
			}
			if err := a.AccumGrad(ga); err != nil {
				return err
			}
		}
		if b.requires {
			gb, err := broadcastSum(g, b.Value.Shape())
			if err != nil {
				return errors.Wrap(err, errors.CodeInternal, "sub grad b")
			}
			neg, err := ops.Neg(gb)
			if err != nil {
				return errors.Wrap(err, errors.CodeInternal, "sub grad b negate")
			}
			if err := b.AccumGrad(neg); err != nil {
				return err
			}
		}
		return nil
	}
	if tape != nil {
		tape.Record(v)
	}
	return v, nil
}

// Div computes the differentiable quotient a / b with the
// quotient rule: d(a/b) = g/b for a and -g*a/b² for b.
func Div(tape *Tape, a, b *Variable) (*Variable, error) {
	out, err := ops.Div(a.Value, b.Value)
	if err != nil {
		return nil, errors.Wrap(err, errors.CodeInvalidArgument, "div")
	}
	v := &Variable{Value: out, requires: a.requires || b.requires, Creator: true}
	v.backward = func(g *tensor.Tensor) error {
		if a.requires {
			ga, err := ops.Div(g, b.Value)
			if err != nil {
				return errors.Wrap(err, errors.CodeInternal, "div grad a")
			}
			ga, err = broadcastSum(ga, a.Value.Shape())
			if err != nil {
				return errors.Wrap(err, errors.CodeInternal, "div grad a broadcast")
			}
			if err := a.AccumGrad(ga); err != nil {
				return err
			}
		}
		if b.requires {
			// -g * a / b^2
			num, err := ops.Mul(g, a.Value)
			if err != nil {
				return errors.Wrap(err, errors.CodeInternal, "div grad b numerator")
			}
			sq, err := ops.Mul(b.Value, b.Value)
			if err != nil {
				return errors.Wrap(err, errors.CodeInternal, "div grad b square")
			}
			gb, err := ops.Div(num, sq)
			if err != nil {
				return errors.Wrap(err, errors.CodeInternal, "div grad b")
			}
			gb, err = ops.Neg(gb)
			if err != nil {
				return errors.Wrap(err, errors.CodeInternal, "div grad b negate")
			}
			gb, err = broadcastSum(gb, b.Value.Shape())
			if err != nil {
				return errors.Wrap(err, errors.CodeInternal, "div grad b broadcast")
			}
			if err := b.AccumGrad(gb); err != nil {
				return err
			}
		}
		return nil
	}
	if tape != nil {
		tape.Record(v)
	}
	return v, nil
}

// Scale computes a * c for a constant c.
// The adjoint is g * c.
func Scale(tape *Tape, a *Variable, c float64) (*Variable, error) {
	out, err := ops.Scale(a.Value, c)
	if err != nil {
		return nil, errors.Wrap(err, errors.CodeInvalidArgument, "scale")
	}
	v := &Variable{Value: out, requires: a.requires, Creator: true}
	v.backward = func(g *tensor.Tensor) error {
		if !a.requires {
			return nil
		}
		ga, err := ops.Scale(g, c)
		if err != nil {
			return errors.Wrap(err, errors.CodeInternal, "scale grad")
		}
		return a.AccumGrad(ga)
	}
	if tape != nil {
		tape.Record(v)
	}
	return v, nil
}

// Relu computes max(0, a). The adjoint gates by the
// output: where the output is positive the input was
// positive, so the gradient passes; elsewhere it is
// zero.
func Relu(tape *Tape, a *Variable) (*Variable, error) {
	out, err := ops.Relu(a.Value)
	if err != nil {
		return nil, errors.Wrap(err, errors.CodeInvalidArgument, "relu")
	}
	v := &Variable{Value: out, requires: a.requires, Creator: true}
	v.backward = func(g *tensor.Tensor) error {
		if !a.requires {
			return nil
		}
		ov := out.Float64()
		mask, err := tensor.New(tensor.Float64, out.Shape().Dims())
		if err != nil {
			return errors.Wrap(err, errors.CodeInternal, "relu mask")
		}
		mv := mask.Float64()
		for i, o := range ov {
			if o > 0 {
				mv[i] = 1
			}
		}
		ga, err := ops.Mul(g, mask)
		if err != nil {
			return errors.Wrap(err, errors.CodeInternal, "relu grad")
		}
		return a.AccumGrad(ga)
	}
	if tape != nil {
		tape.Record(v)
	}
	return v, nil
}

// Sigmoid computes the logistic function. The adjoint
// is g * y * (1 - y), where y is the output.
func Sigmoid(tape *Tape, a *Variable) (*Variable, error) {
	out, err := ops.Sigmoid(a.Value)
	if err != nil {
		return nil, errors.Wrap(err, errors.CodeInvalidArgument, "sigmoid")
	}
	v := &Variable{Value: out, requires: a.requires, Creator: true}
	v.backward = func(g *tensor.Tensor) error {
		if !a.requires {
			return nil
		}
		// d/dy y*(1-y) with y = sigmoid(x): the adjoint is g*y*(1-y).
		// (The tanh rule is 1-y²; sigmoid is 1-y.)
		neg, err := ops.Neg(out)
		if err != nil {
			return errors.Wrap(err, errors.CodeInternal, "sigmoid grad negate")
		}
		oneMinus, err := ops.AddScalar(neg, 1)
		if err != nil {
			return errors.Wrap(err, errors.CodeInternal, "sigmoid grad 1-y")
		}
		dy, err := ops.Mul(out, oneMinus)
		if err != nil {
			return errors.Wrap(err, errors.CodeInternal, "sigmoid grad y(1-y)")
		}
		ga, err := ops.Mul(g, dy)
		if err != nil {
			return errors.Wrap(err, errors.CodeInternal, "sigmoid grad")
		}
		return a.AccumGrad(ga)
	}
	if tape != nil {
		tape.Record(v)
	}
	return v, nil
}

// Tanh computes the hyperbolic tangent. The adjoint is
// g * (1 - y²).
func Tanh(tape *Tape, a *Variable) (*Variable, error) {
	out, err := ops.Tanh(a.Value)
	if err != nil {
		return nil, errors.Wrap(err, errors.CodeInvalidArgument, "tanh")
	}
	v := &Variable{Value: out, requires: a.requires, Creator: true}
	v.backward = func(g *tensor.Tensor) error {
		if !a.requires {
			return nil
		}
		os, err := ops.Mul(out, out)
		if err != nil {
			return errors.Wrap(err, errors.CodeInternal, "tanh grad square")
		}
		// 1-y², sign included: see the sigmoid rule.
		neg, err := ops.Neg(os)
		if err != nil {
			return errors.Wrap(err, errors.CodeInternal, "tanh grad negate")
		}
		oneMinus, err := ops.AddScalar(neg, 1)
		if err != nil {
			return errors.Wrap(err, errors.CodeInternal, "tanh grad 1-y^2")
		}
		ga, err := ops.Mul(g, oneMinus)
		if err != nil {
			return errors.Wrap(err, errors.CodeInternal, "tanh grad")
		}
		return a.AccumGrad(ga)
	}
	if tape != nil {
		tape.Record(v)
	}
	return v, nil
}

// Exp computes e**a. The adjoint is g * y because
// de**a/da = e**a.
func Exp(tape *Tape, a *Variable) (*Variable, error) {
	out, err := ops.Exp(a.Value)
	if err != nil {
		return nil, errors.Wrap(err, errors.CodeInvalidArgument, "exp")
	}
	v := &Variable{Value: out, requires: a.requires, Creator: true}
	v.backward = func(g *tensor.Tensor) error {
		if !a.requires {
			return nil
		}
		ga, err := ops.Mul(g, out)
		if err != nil {
			return errors.Wrap(err, errors.CodeInternal, "exp grad")
		}
		return a.AccumGrad(ga)
	}
	if tape != nil {
		tape.Record(v)
	}
	return v, nil
}

// Mean computes the differentiable mean over the given
// axes. The adjoint scatters the gradient back to the
// input shape and scales by 1/n, where n is the number
// of reduced elements.
func Mean(tape *Tape, a *Variable, axes []int, keepDims bool) (*Variable, error) {
	out, err := reduce.Mean(a.Value, axes, keepDims)
	if err != nil {
		return nil, errors.Wrap(err, errors.CodeInvalidArgument, "mean")
	}
	v := &Variable{Value: out, requires: a.requires, Creator: true}
	v.backward = func(g *tensor.Tensor) error {
		if !a.requires {
			return nil
		}
		ga, err := expandReducedGrad(g, a.Value.Shape(), axes, keepDims)
		if err != nil {
			return errors.Wrap(err, errors.CodeInternal, "mean grad broadcast")
		}
		// The reduction size is a property of the shapes, not of the
		// pass, so it is derived from the recorded output shape.
		n := float64(a.Value.NumElements()) / float64(out.NumElements())
		scaled, err := ops.Scale(ga, 1/n)
		if err != nil {
			return errors.Wrap(err, errors.CodeInternal, "mean grad scale")
		}
		return a.AccumGrad(scaled)
	}
	if tape != nil {
		tape.Record(v)
	}
	return v, nil
}

// broadcastSum reshapes/reduces g to the target
// shape, summing over broadcast dimensions.
func broadcastSum(g *tensor.Tensor, target tensor.Shape) (*tensor.Tensor, error) {
	if g.Shape().Equal(target) {
		return g, nil
	}
	out := g
	// Left-reduce extra leading dimensions.
	for out.Shape().Rank() > target.Rank() {
		s, err := reduce.Sum(out, []int{0}, false)
		if err != nil {
			return nil, err
		}
		out = s
	}
	if out.Shape().Equal(target) {
		return out, nil
	}
	// Reduce remaining mismatched singleton axes.
	os := out.Shape()
	var axes []int
	for i := 0; i < os.Rank(); i++ {
		if os.Dims()[i] != target.Dims()[i] && target.Dims()[i] == 1 {
			axes = append(axes, i)
		}
	}
	if len(axes) > 0 {
		s, err := reduce.Sum(out, axes, true)
		if err != nil {
			return nil, err
		}
		out = s
	}
	if !out.Shape().Equal(target) {
		e, err := out.Expand(target.Dims()...)
		if err != nil {
			return nil, err
		}
		// Expand returns a zero-copy view with
		// broadcast strides; materialize it so
		// downstream consumers see contiguous
		// storage matching the logical shape.
		out, err = e.Contiguous()
		if err != nil {
			return nil, err
		}
	}
	return out, nil
}
