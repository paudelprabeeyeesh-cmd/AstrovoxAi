package autograd

import (
	"math"
	"testing"

	"github.com/astrovox/astrovox/tensor"
	"github.com/astrovox/astrovox/tensor/ops"
)

// scalar creates a 1-element tracked variable.
func scalar(t *testing.T, v float64) *Variable {
	t.Helper()
	buf, err := tensor.Full(tensor.Float64, []int{1}, v)
	if err != nil {
		t.Fatal(err)
	}
	return NewVariable(buf, true)
}

// vec creates a tracked vector variable.
func vec(t *testing.T, vals []float64) *Variable {
	t.Helper()
	buf, err := tensor.New(tensor.Float64, []int{len(vals)})
	if err != nil {
		t.Fatal(err)
	}
	for i, v := range vals {
		if err := buf.Set(v, i); err != nil {
			t.Fatal(err)
		}
	}
	return NewVariable(buf, true)
}

func grad(v *Variable) float64 {
	if v.Grad == nil {
		return 0
	}
	return v.Grad.Float64()[0]
}

func TestAddGrad(t *testing.T) {
	tape := NewTape()
	a := scalar(t, 3)
	b := scalar(t, 4)
	y, err := Add(tape, a, b)
	if err != nil {
		t.Fatal(err)
	}
	if got := y.Value.Float64()[0]; got != 7 {
		t.Fatalf("y = %v, want 7", got)
	}
	if err := tape.Backward(nil); err != nil {
		t.Fatal(err)
	}
	if grad(a) != 1 || grad(b) != 1 {
		t.Fatalf("grads = a:%v b:%v, want 1 1", grad(a), grad(b))
	}
}

func TestMulGrad(t *testing.T) {
	tape := NewTape()
	a := scalar(t, 3)
	b := scalar(t, 4)
	y, err := Mul(tape, a, b)
	if err != nil {
		t.Fatal(err)
	}
	if got := y.Value.Float64()[0]; got != 12 {
		t.Fatalf("y = %v, want 12", got)
	}
	if err := tape.Backward(nil); err != nil {
		t.Fatal(err)
	}
	// d(a*b)/da = b = 4, d(a*b)/db = a = 3
	if grad(a) != 4 || grad(b) != 3 {
		t.Fatalf("grads = a:%v b:%v, want 4 3", grad(a), grad(b))
	}
}

func TestCompositeGrad(t *testing.T) {
	// y = a*b + a; dy/da = b+1 = 5, dy/db = a = 3
	tape := NewTape()
	a := scalar(t, 3)
	b := scalar(t, 4)
	ab, err := Mul(tape, a, b)
	if err != nil {
		t.Fatal(err)
	}
	y, err := Add(tape, ab, a)
	if err != nil {
		t.Fatal(err)
	}
	if got := y.Value.Float64()[0]; got != 15 {
		t.Fatalf("y = %v, want 15", got)
	}
	if err := tape.Backward(nil); err != nil {
		t.Fatal(err)
	}
	if grad(a) != 5 || grad(b) != 3 {
		t.Fatalf("grads = a:%v b:%v, want 5 3", grad(a), grad(b))
	}
}

func TestMatMulGrad(t *testing.T) {
	// A = [[1,2],[3,4]], B = [[5,6],[7,8]]
	// Y = A@B, L = sum(Y)
	// dL/dA = ones @ B^T -> every row = row sums of B = [11, 15]
	// dL/dB = A^T @ ones -> every col = col sums of A = [4, 6]
	mk := func(vals []float64) *tensor.Tensor {
		buf, err := tensor.New(tensor.Float64, []int{2, 2})
		if err != nil {
			t.Fatal(err)
		}
		for i, v := range vals {
			if err := buf.Set(v, i/2, i%2); err != nil {
				t.Fatal(err)
			}
		}
		return buf
	}
	tape := NewTape()
	a := NewVariable(mk([]float64{1, 2, 3, 4}), true)
	b := NewVariable(mk([]float64{5, 6, 7, 8}), true)
	y, err := MatMul(tape, a, b)
	if err != nil {
		t.Fatal(err)
	}
	// Y = [[19, 22], [43, 50]]
	ys := y.Value.Float64()
	if ys[0] != 19 || ys[1] != 22 || ys[2] != 43 || ys[3] != 50 {
		t.Fatalf("Y = %v, want [19 22 43 50]", ys)
	}
	if err := tape.Backward(nil); err != nil {
		t.Fatal(err)
	}
	ga := a.Grad.Float64()
	gb := b.Grad.Float64()
	for i := range ga {
		wantA := []float64{11, 15, 11, 15}
		if ga[i] != wantA[i] {
			t.Fatalf("dL/dA = %v, want %v", ga, wantA)
		}
	}
	for i := range gb {
		wantB := []float64{4, 4, 6, 6}
		if gb[i] != wantB[i] {
			t.Fatalf("dL/dB = %v, want %v", gb, wantB)
		}
	}
}

func TestSumGrad(t *testing.T) {
	// L = sum(x); dL/dx = ones
	tape := NewTape()
	x := vec(t, []float64{1, 2, 3})
	y, err := Sum(tape, x, []int{0}, false)
	if err != nil {
		t.Fatal(err)
	}
	if got := y.Value.Float64()[0]; got != 6 {
		t.Fatalf("sum = %v, want 6", got)
	}
	if err := tape.Backward(nil); err != nil {
		t.Fatal(err)
	}
	gx := x.Grad.Float64()
	for i, g := range gx {
		if g != 1 {
			t.Fatalf("dL/dx[%d] = %v, want 1", i, g)
		}
	}
}

// TestNumericalGradients verifies analytical
// gradients against central finite differences.
func TestNumericalGradients(t *testing.T) {
	f := func(a, b float64) float64 {
		// f = a*b + sin-less composition: a^2*b + b
		tape := NewTape()
		va := scalar(t, a)
		vb := scalar(t, b)
		a2, err := Mul(tape, va, va)
		if err != nil {
			t.Fatal(err)
		}
		a2b, err := Mul(tape, a2, vb)
		if err != nil {
			t.Fatal(err)
		}
		y, err := Add(tape, a2b, vb)
		if err != nil {
			t.Fatal(err)
		}
		if err := tape.Backward(nil); err != nil {
			t.Fatal(err)
		}
		_ = y
		return a*a*b + b
	}
	a, b := 2.0, 3.0
	tape := NewTape()
	va := scalar(t, a)
	vb := scalar(t, b)
	a2, _ := Mul(tape, va, va)
	a2b, _ := Mul(tape, a2, vb)
	y, _ := Add(tape, a2b, vb)
	if got := y.Value.Float64()[0]; got != f(a, b) {
		t.Fatalf("y = %v, want %v", got, f(a, b))
	}
	if err := tape.Backward(nil); err != nil {
		t.Fatal(err)
	}
	// df/da = 2ab = 12, df/db = a^2+1 = 5
	h := 1e-6
	numDA := (f(a+h, b) - f(a-h, b)) / (2 * h)
	numDB := (f(a, b+h) - f(a, b-h)) / (2 * h)
	if math.Abs(grad(va)-numDA) > 1e-4 {
		t.Fatalf("df/da = %v, numerical %v", grad(va), numDA)
	}
	if math.Abs(grad(vb)-numDB) > 1e-4 {
		t.Fatalf("df/db = %v, numerical %v", grad(vb), numDB)
	}
}

func TestSGDStep(t *testing.T) {
	// Minimize f(x) = (x-3)^2; grad = 2(x-3)
	tape := NewTape()
	x := scalar(t, 0)
	three := scalar(t, 3)
	three.requires = false
	diff, err := Sub(tape, x, three)
	if err != nil {
		t.Fatal(err)
	}
	_ = diff
	// Manually set gradient: df/dx = 2(x-3) = -6 at x=0
	g, err := tensor.Full(tensor.Float64, []int{1}, -6)
	if err != nil {
		t.Fatal(err)
	}
	x.Grad = g
	sgd, err := NewSGD(0.1, 0)
	if err != nil {
		t.Fatal(err)
	}
	if err := sgd.Step([]*Variable{x}); err != nil {
		t.Fatal(err)
	}
	// x' = 0 - 0.1*(-6) = 0.6
	got := x.Value.Float64()[0]
	if math.Abs(got-0.6) > 1e-9 {
		t.Fatalf("x = %v, want 0.6", got)
	}
}

func TestAdamStep(t *testing.T) {
	// One Adam step on a quadratic: verify the
	// update moves x toward the minimum and the
	// moment buffers initialize correctly.
	x := scalar(t, 0)
	g, _ := tensor.Full(tensor.Float64, []int{1}, -2)
	x.Grad = g
	adam, err := NewAdam(0.1, 0.9, 0.999, 1e-8)
	if err != nil {
		t.Fatal(err)
	}
	if err := adam.Step([]*Variable{x}); err != nil {
		t.Fatal(err)
	}
	// m = 0.1*(-2) = -0.2; v = 0.001*4 = 0.004
	// mhat = -0.2/0.1 = -2; vhat = 0.004/0.001 = 4
	// update = -0.1 * (-2)/(2+1e-8) ≈ 0.1
	got := x.Value.Float64()[0]
	if math.Abs(got-0.1) > 1e-6 {
		t.Fatalf("x = %v, want ≈0.1", got)
	}
}

func TestAdamBadBetas(t *testing.T) {
	if _, err := NewAdam(0.1, 1.0, 0.9, 1e-8); err == nil {
		t.Fatal("expected beta1 error")
	}
	if _, err := NewAdam(0.1, 0.9, 0.0, 1e-8); err == nil {
		t.Fatal("expected beta2 error")
	}
	if _, err := NewAdam(-1, 0.9, 0.9, 1e-8); err == nil {
		t.Fatal("expected lr error")
	}
}

// Sub lives in the library now; this helper was the test-only stand-in.

func TestNegGrad(t *testing.T) {
	tape := NewTape()
	a := scalar(t, 5)
	y, err := Neg(tape, a)
	if err != nil {
		t.Fatal(err)
	}
	if got := y.Value.Float64()[0]; got != -5 {
		t.Fatalf("y = %v, want -5", got)
	}
	if err := tape.Backward(nil); err != nil {
		t.Fatal(err)
	}
	if grad(a) != -1 {
		t.Fatalf("grad = %v, want -1", grad(a))
	}
}

func TestZeroGrad(t *testing.T) {
	tape := NewTape()
	a := scalar(t, 1)
	b := scalar(t, 2)
	y, _ := Mul(tape, a, b)
	_ = y
	_ = tape.Backward(nil)
	if a.Grad == nil {
		t.Fatal("gradient not accumulated")
	}
	a.ZeroGrad()
	if a.Grad != nil {
		t.Fatal("ZeroGrad did not clear")
	}
}

func TestUntrackedLeaf(t *testing.T) {
	// Constants (requires=false) receive no gradient.
	tape := NewTape()
	a := scalar(t, 3)
	c := scalar(t, 4)
	c.requires = false
	y, err := Add(tape, a, c)
	if err != nil {
		t.Fatal(err)
	}
	_ = y
	if err := tape.Backward(nil); err != nil {
		t.Fatal(err)
	}
	if grad(a) != 1 {
		t.Fatalf("grad(a) = %v, want 1", grad(a))
	}
	if c.Grad != nil {
		t.Fatal("constant received gradient")
	}
}

func TestOpsPackageIntegration(t *testing.T) {
	// Verify the underlying ops package contract
	// used by autograd: elementwise scale and add.
	a, _ := tensor.Full(tensor.Float64, []int{2}, 2)
	b, _ := tensor.Full(tensor.Float64, []int{2}, 3)
	sum, err := ops.Add(a, b)
	if err != nil {
		t.Fatal(err)
	}
	if got := sum.Float64()[0]; got != 5 {
		t.Fatalf("add = %v, want 5", got)
	}
	scaled, err := ops.Scale(a, 1.5)
	if err != nil {
		t.Fatal(err)
	}
	if got := scaled.Float64()[0]; got != 3 {
		t.Fatalf("scale = %v, want 3", got)
	}
}
