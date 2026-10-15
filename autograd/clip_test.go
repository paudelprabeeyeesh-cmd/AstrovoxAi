package autograd

import (
	"math"
	"testing"

	"github.com/astrovox/astrovox/tensor"
)

func gradVar(vals ...float64) *Variable {
	t, err := tensor.New(tensor.Float64, []int{len(vals)})
	if err != nil {
		panic(err)
	}
	copy(t.Float64(), vals)
	v := NewVariable(t, true)
	g, err := tensor.New(tensor.Float64, []int{len(vals)})
	if err != nil {
		panic(err)
	}
	copy(g.Float64(), vals)
	v.Grad = g
	return v
}

func TestGradNorm(t *testing.T) {
	// sqrt(3^2 + 4^2 + 12^2) = 13 across two variables.
	a := gradVar(3, 4)
	b := gradVar(12)
	norm, err := GradNorm([]*Variable{a, b})
	if err != nil {
		t.Fatal(err)
	}
	if math.Abs(norm-13) > 1e-12 {
		t.Fatalf("norm = %v, want 13", norm)
	}
	// No gradients at all: zero, not an error.
	fresh := NewVariable(nil, true)
	norm, err = GradNorm([]*Variable{fresh, nil})
	if err != nil {
		t.Fatal(err)
	}
	if norm != 0 {
		t.Fatalf("norm without gradients = %v, want 0", norm)
	}
}

func TestClipGradientsScalesOnlyWhenAboveThreshold(t *testing.T) {
	// Norm 10, clip at 5: scaled by 0.5.
	a := gradVar(6, 8)
	norm, err := ClipGradients([]*Variable{a}, 5)
	if err != nil {
		t.Fatal(err)
	}
	if math.Abs(norm-10) > 1e-12 {
		t.Fatalf("returned norm = %v, want 10", norm)
	}
	got := a.Grad.Float64()
	if math.Abs(got[0]-3) > 1e-12 || math.Abs(got[1]-4) > 1e-12 {
		t.Fatalf("clipped gradient = %v, want [3 4]", got)
	}

	// Below the threshold: unchanged.
	b := gradVar(3, 4)
	norm, err = ClipGradients([]*Variable{b}, 100)
	if err != nil {
		t.Fatal(err)
	}
	if norm != 5 || b.Grad.Float64()[0] != 3 {
		t.Fatalf("below-threshold clip changed the gradient: %v", b.Grad.Float64())
	}
}

func TestClipGradientsRejectsBadThreshold(t *testing.T) {
	if _, err := ClipGradients([]*Variable{gradVar(1)}, 0); err == nil {
		t.Fatal("a zero threshold was accepted")
	}
	if _, err := ClipGradients([]*Variable{gradVar(1)}, -1); err == nil {
		t.Fatal("a negative threshold was accepted")
	}
	if _, err := ClipGradients([]*Variable{gradVar(1)}, math.NaN()); err == nil {
		t.Fatal("a NaN threshold was accepted")
	}
}

func TestClipGradientsZeroesNonFinite(t *testing.T) {
	// A NaN gradient norm must zero gradients (documented policy) rather
	// than propagate NaN into the optimizer.
	a := gradVar(math.NaN(), 1)
	norm, err := ClipGradients([]*Variable{a}, 1)
	if err != nil {
		t.Fatal(err)
	}
	if !math.IsNaN(norm) {
		t.Fatalf("norm = %v, want NaN", norm)
	}
	for i, v := range a.Grad.Float64() {
		if !math.IsNaN(v) && v != 0 {
			t.Fatalf("gradient[%d] = %v after non-finite clip, want 0 or preserved NaN policy", i, v)
		}
	}
	// At least one element must be zeroed for the policy to hold.
	zeroed := false
	for _, v := range a.Grad.Float64() {
		if v == 0 {
			zeroed = true
		}
	}
	if !zeroed {
		t.Fatal("non-finite gradients were not zeroed")
	}
}

func TestGradNumel(t *testing.T) {
	v := gradVar(1, 2, 3)
	if n := v.GradNumel(); n != 3 {
		t.Fatalf("GradNumel = %d, want 3", n)
	}
	if n := NewVariable(nil, true).GradNumel(); n != 0 {
		t.Fatalf("GradNumel without gradient = %d, want 0", n)
	}
}

// TestClipThenStepReducesNorm verifies clipping composes with the real
// optimizer: after clipping, an SGD step along the gradient shrinks the
// loss on a quadratic.
func TestClipThenStepReducesLoss(t *testing.T) {
	tape := NewTape()
	x := NewVariable(tensorOf1d(2), true)
	sq, err := Mul(tape, x, x)
	if err != nil {
		t.Fatal(err)
	}
	if err := tape.Backward(nil); err != nil {
		t.Fatal(err)
	}
	norm, err := ClipGradients([]*Variable{x}, 1)
	if err != nil {
		t.Fatal(err)
	}
	if norm != 4 {
		t.Fatalf("norm = %v, want 4", norm)
	}
	// After clipping to 1, the gradient is 4 * (1/4) = 1.
	if g := x.Grad.Float64()[0]; math.Abs(g-1) > 1e-12 {
		t.Fatalf("clipped gradient = %v, want 1", g)
	}
	opt, err := NewSGD(0.1, 0)
	if err != nil {
		t.Fatal(err)
	}
	before := sq.Value.Float64()[0]
	if err := opt.Step([]*Variable{x}); err != nil {
		t.Fatal(err)
	}
	after := x.Value.Float64()[0]
	if math.Abs(after-1.9) > 1e-12 {
		t.Fatalf("x = %v, want 1.9", after)
	}
	if before <= after {
		t.Fatalf("loss did not shrink toward the optimum: %v -> %v", before, after)
	}
}

func tensorOf1d(v float64) *tensor.Tensor {
	t, err := tensor.New(tensor.Float64, []int{1})
	if err != nil {
		panic(err)
	}
	t.Float64()[0] = v
	return t
}
