package autograd_test

import (
	"testing"

	"github.com/astrovox/astrovox/autograd"
	"github.com/astrovox/astrovox/tensor"
)

func benchVars(b *testing.B, n int) []*autograd.Variable {
	vars := make([]*autograd.Variable, n)
	for i := range vars {
		t, err := tensor.Ones(tensor.Float64, []int{64, 64})
		if err != nil {
			b.Fatal(err)
		}
		vars[i] = autograd.NewVariable(t, true)
	}
	return vars
}

func BenchmarkAutogradAdd(b *testing.B) {
	tape := autograd.NewTape()
	vars := benchVars(b, 2)
	a, c := vars[0], vars[1]
	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		if _, err := autograd.Add(tape, a, c); err != nil {
			b.Fatal(err)
		}
	}
}

func BenchmarkAutogradMul(b *testing.B) {
	tape := autograd.NewTape()
	vars := benchVars(b, 2)
	a, c := vars[0], vars[1]
	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		if _, err := autograd.Mul(tape, a, c); err != nil {
			b.Fatal(err)
		}
	}
}

func BenchmarkAutogradBackward(b *testing.B) {
	vars := benchVars(b, 2)
	a, c := vars[0], vars[1]
	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		tape := autograd.NewTape()
		out, err := autograd.Add(tape, a, c)
		if err != nil {
			b.Fatal(err)
		}
		seed, err := tensor.Ones(out.Value.DType(), out.Value.Shape().Dims())
		if err != nil {
			b.Fatal(err)
		}
		if err := tape.Backward(seed); err != nil {
			b.Fatal(err)
		}
	}
}

func BenchmarkSGDStep(b *testing.B) {
	vars := benchVars(b, 10)
	opt, err := autograd.NewSGD(0.01, 0.9)
	if err != nil {
		b.Fatal(err)
	}
	for _, v := range vars {
		g, err := tensor.Ones(v.Value.DType(), v.Value.Shape().Dims())
		if err != nil {
			b.Fatal(err)
		}
		v.Grad = g
	}
	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		if err := opt.Step(vars); err != nil {
			b.Fatal(err)
		}
	}
}
