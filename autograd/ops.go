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
		if a.requires {
			if s, err := broadcastSum(ga, a.Value.Shape()); err == nil {
				ga = s
			}
			if err := a.AccumGrad(ga); err != nil {
				return err
			}
		}
		if b.requires {
			if s, err := broadcastSum(gb, b.Value.Shape()); err == nil {
				gb = s
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
		ga, err := broadcastSum(g, a.Value.Shape())
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
