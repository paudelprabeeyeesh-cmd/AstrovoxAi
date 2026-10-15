package autograd

import (
	"math"
	"testing"

	"github.com/astrovox/astrovox/tensor"
)

// Gradient and semantics tests for the differentiable op set and the
// tape's failure behavior. Every gradient is checked either against a
// hand-computed value or against central finite differences of the
// forward function.

func tensorOf(vals []float64, dims ...int) *tensor.Tensor {
	t, err := tensor.New(tensor.Float64, dims)
	if err != nil {
		panic(err)
	}
	copy(t.Float64(), vals)
	return t
}

func gradOf(v *Variable) []float64 {
	if v.Grad == nil {
		return nil
	}
	return v.Grad.Float64()
}

func scalarVar(t *testing.T, x float64) *Variable {
	t.Helper()
	return NewVariable(tensorOf([]float64{x}, 1), true)
}

func numGrad(f func(x *tensor.Tensor) float64, x *tensor.Tensor) []float64 {
	xv := x.Float64()
	g := make([]float64, len(xv))
	const h = 1e-6
	for i := range xv {
		orig := xv[i]
		xv[i] = orig + h
		fp := f(x)
		xv[i] = orig - h
		fm := f(x)
		xv[i] = orig
		g[i] = (fp - fm) / (2 * h)
	}
	return g
}

func TestSubDivScaleGradients(t *testing.T) {
	// f = (a/c - b) * (1/c) with a=6, b=2, c=3 -> f = 0.7778-2 = -1.2222
	tape := NewTape()
	a := NewVariable(tensorOf([]float64{6, 8}, 2), true)
	b := NewVariable(tensorOf([]float64{2, 1}, 2), true)
	c := NewVariable(tensorOf([]float64{3, 4}, 2), true)

	q, err := Div(tape, a, c)
	if err != nil {
		t.Fatal(err)
	}
	d, err := Sub(tape, q, b)
	if err != nil {
		t.Fatal(err)
	}
	s, err := Scale(tape, d, 2)
	if err != nil {
		t.Fatal(err)
	}
	_ = s
	if err := tape.Backward(nil); err != nil {
		t.Fatal(err)
	}
	// Seed is ones: dL/dout = 1 everywhere. f_i = 2*((a_i/c_i) - b_i).
	// df/da = 2/c, df/db = -2, df/dc = -2*a/c^2.
	wantA := []float64{2.0 / 3, 2.0 / 4}
	wantB := []float64{-2, -2}
	// Float literals on every operand: untyped-integer division truncates
	// (-12/9 == -1), which silently changes the expected value.
	wantC := []float64{-2.0 * 6 / 9, -2.0 * 8 / 16}
	checkClose(t, "div/da", gradOf(a), wantA, 1e-9)
	checkClose(t, "div/db", gradOf(b), wantB, 1e-9)
	checkClose(t, "div/dc", gradOf(c), wantC, 1e-9)
}

func TestActivationGradients(t *testing.T) {
	// Finite differences for each activation at several points.
	xs := []float64{-2, -0.5, 0.25, 1.5}
	cases := []struct {
		name string
		fn   func(tape *Tape, a *Variable) (*Variable, error)
		ref  func(x float64) float64
	}{
		{"relu", Relu, func(x float64) float64 {
			if x < 0 {
				return 0
			}
			return x
		}},
		{"sigmoid", Sigmoid, func(x float64) float64 { return 1 / (1 + math.Exp(-x)) }},
		{"tanh", Tanh, math.Tanh},
		{"exp", Exp, math.Exp},
	}
	for _, c := range cases {
		tape := NewTape()
		a := NewVariable(tensorOf(xs, len(xs)), true)
		out, err := c.fn(tape, a)
		if err != nil {
			t.Fatalf("%s: %v", c.name, err)
		}
		if err := tape.Backward(nil); err != nil {
			t.Fatalf("%s backward: %v", c.name, err)
		}
		want := numGrad(func(x *tensor.Tensor) float64 {
			var s float64
			for _, v := range x.Float64() {
				s += c.ref(v)
			}
			return s
		}, tensorOf(xs, len(xs)))
		checkClose(t, c.name, gradOf(a), want, 1e-5)
		if out == nil {
			t.Fatalf("%s: nil output", c.name)
		}
	}
}

func TestMeanGradient(t *testing.T) {
	// d/dx sum(mean(x)) = 1/n per element.
	x := tensorOf([]float64{1, 2, 3, 4, 5, 6}, 2, 3)
	a := NewVariable(x, true)
	tape := NewTape()
	m, err := Mean(tape, a, []int{1}, false)
	if err != nil {
		t.Fatal(err)
	}
	if err := tape.Backward(nil); err != nil {
		t.Fatal(err)
	}
	checkClose(t, "mean grad", gradOf(a), []float64{1.0 / 3, 1.0 / 3, 1.0 / 3, 1.0 / 3, 1.0 / 3, 1.0 / 3}, 1e-12)
	if got := m.Value.Float64(); math.Abs(got[0]-2) > 1e-9 || math.Abs(got[1]-5) > 1e-9 {
		t.Fatalf("mean value = %v, want [2 5]", got)
	}
}

func TestBroadcastGradients(t *testing.T) {
	// a is [2,3], b is [3]: broadcasting means b's gradient is the sum
	// over the broadcast axis.
	tape := NewTape()
	a := NewVariable(tensorOf([]float64{1, 2, 3, 4, 5, 6}, 2, 3), true)
	b := NewVariable(tensorOf([]float64{10, 20, 30}, 3), true)
	m, err := Mul(tape, a, b)
	if err != nil {
		t.Fatal(err)
	}
	if got := m.Value.Shape().Dims(); got[0] != 2 || got[1] != 3 {
		t.Fatalf("broadcast output shape = %v, want [2 3]", got)
	}
	if err := tape.Backward(nil); err != nil {
		t.Fatal(err)
	}
	checkClose(t, "broadcast da", gradOf(a), []float64{10, 20, 30, 10, 20, 30}, 1e-9)
	checkClose(t, "broadcast db", gradOf(b), []float64{5, 7, 9}, 1e-9)
}

func TestDiamondGraphAccumulatesOncePerPath(t *testing.T) {
	// f = x*x + x*x: x reaches the output through two paths, so its
	// gradient is 4x, not 2x. A tape that zeroes accumulated gradients
	// between paths would silently halve it.
	x := scalarVar(t, 3)
	tape := NewTape()
	l, err := Mul(tape, x, x)
	if err != nil {
		t.Fatal(err)
	}
	r, err := Mul(tape, x, x)
	if err != nil {
		t.Fatal(err)
	}
	f, err := Add(tape, l, r)
	if err != nil {
		t.Fatal(err)
	}
	if err := tape.Backward(nil); err != nil {
		t.Fatal(err)
	}
	if got := gradOf(x); len(got) != 1 || math.Abs(got[0]-12) > 1e-9 {
		t.Fatalf("diamond gradient = %v, want [12]", got)
	}
	_ = f
}

func TestTapeIsSingleUse(t *testing.T) {
	// Replaying a tape double-accumulates gradients; it is refused
	// rather than silently wrong.
	tape := NewTape()
	a := scalarVar(t, 2)
	if _, err := Mul(tape, a, a); err != nil {
		t.Fatal(err)
	}
	if err := tape.Backward(nil); err != nil {
		t.Fatal(err)
	}
	if err := tape.Backward(nil); err == nil {
		t.Fatal("a second Backward on the same tape was accepted")
	}
	// A fresh pass works after a zero and a reset.
	totalFirst := gradOf(a)[0]
	a.ZeroGrad()
	tape.Reset()
	if _, err := Mul(tape, a, a); err != nil {
		t.Fatal(err)
	}
	if err := tape.Backward(nil); err != nil {
		t.Fatal(err)
	}
	if got := gradOf(a); math.Abs(got[0]-totalFirst) > 1e-9 {
		t.Fatalf("fresh tape gradient = %v, want %v", got, totalFirst)
	}
}

func TestBackwardRejectsUnknownRule(t *testing.T) {
	// A recorded creator node with no gradient rule is an error, not a
	// silently skipped node that leaves a zero gradient.
	tape := NewTape()
	a := scalarVar(t, 1)
	_, err := Mul(tape, a, a)
	if err != nil {
		t.Fatal(err)
	}
	unbacked := &Variable{Value: tensorOf([]float64{1}, 1), requires: true, Creator: true}
	tape.Record(unbacked)
	if err := tape.Backward(nil); err == nil {
		t.Fatal("a node without a gradient rule was silently skipped")
	}
}

// TestDetachStopsGradientFlow: a detached path cuts the tape. The branch
// behind the detach still receives its (zero) gradient, which is the
// correct contribution of an unreachable node, while the path through the
// detached leaf still trains.
func TestDetachStopsGradientFlow(t *testing.T) {
	tape := NewTape()
	a := scalarVar(t, 5)
	b := scalarVar(t, 0.5)
	p, err := Mul(tape, a, b)
	if err != nil {
		t.Fatal(err)
	}
	frozen := p.Detach()
	if frozen.RequiresGrad() {
		t.Fatal("a detached variable still requires grad")
	}
	if frozen.Value != p.Value {
		t.Fatal("detach must share the value, not copy it")
	}
	c, err := Mul(tape, frozen, a)
	if err != nil {
		t.Fatal(err)
	}
	if !c.RequiresGrad() {
		t.Fatal("the second operand still requires grad")
	}
	if err := tape.Backward(nil); err != nil {
		t.Fatal(err)
	}
	// a receives the gradient only through the second factor: c = p*a,
	// so da = p = 2.5. The a*b branch contributes zero because p was
	// detached.
	if got := gradOf(a); len(got) != 1 || math.Abs(got[0]-2.5) > 1e-9 {
		t.Fatalf("a gradient = %v, want [2.5]", got)
	}
	// b's gradient exists but is exactly zero: the only path to b ran
	// through the detached node, and an unreachable branch contributes
	// nothing rather than being silently dropped.
	if gradOf(b) == nil {
		t.Fatal("b has no gradient tensor")
	}
	for i, v := range gradOf(b) {
		if v != 0 {
			t.Fatalf("b gradient[%d] = %v, want 0", i, v)
		}
	}
	// The detached node recorded nothing: 2 real ops on the tape.
	if tape.Len() != 2 {
		t.Fatalf("tape length = %d, want 2", tape.Len())
	}
}

func TestCompositeFiniteDifferences(t *testing.T) {
	// A small MLP-like composition: sigmoid(x @ W + b), checked against
	// finite differences of the forward computation.
	xVals := []float64{0.5, -1.0, 2.0}
	wVals := []float64{0.2, -0.4, 0.6, 1.0, 0.1, -0.3}
	bVals := []float64{0.05, -0.05}

	forward := func(x, w, b *tensor.Tensor) float64 {
		// matmul by hand: [1,3] @ [3,2]
		var out [2]float64
		for j := 0; j < 2; j++ {
			var acc float64
			for k := 0; k < 3; k++ {
				acc += x.Float64()[k] * w.Float64()[k*2+j]
			}
			out[j] = 1 / (1 + math.Exp(-(acc + b.Float64()[j])))
		}
		return out[0] + out[1]
	}

	tape := NewTape()
	x := NewVariable(tensorOf(xVals, 1, 3), true)
	w := NewVariable(tensorOf(wVals, 3, 2), true)
	b := NewVariable(tensorOf(bVals, 1, 2), true)
	xw, err := MatMul(tape, x, w)
	if err != nil {
		t.Fatal(err)
	}
	xwb, err := Add(tape, xw, b)
	if err != nil {
		t.Fatal(err)
	}
	if _, err := Sigmoid(tape, xwb); err != nil {
		t.Fatal(err)
	}
	if err := tape.Backward(nil); err != nil {
		t.Fatal(err)
	}
	checkClose(t, "mlp dx", gradOf(x), numGrad(func(t *tensor.Tensor) float64 {
		return forward(t, tensorOf(wVals, 3, 2), tensorOf(bVals, 1, 2))
	}, tensorOf(xVals, 1, 3)), 1e-5)
	checkClose(t, "mlp dW", gradOf(w), numGrad(func(t *tensor.Tensor) float64 {
		return forward(tensorOf(xVals, 1, 3), t, tensorOf(bVals, 1, 2))
	}, tensorOf(wVals, 3, 2)), 1e-5)
	checkClose(t, "mlp db", gradOf(b), numGrad(func(t *tensor.Tensor) float64 {
		return forward(tensorOf(xVals, 1, 3), tensorOf(wVals, 3, 2), t)
	}, tensorOf(bVals, 1, 2)), 1e-5)
}

func TestOptimizerSeesFreshTapeEachStep(t *testing.T) {
	// The training-loop pattern: forward, backward, step, zero, repeat
	// on a NEW tape. Each step must use fresh gradients, not leftovers.
	w := NewVariable(tensorOf([]float64{1}, 1), true)
	opt, err := NewSGD(0.1, 0)
	if err != nil {
		t.Fatal(err)
	}
	var losses []float64
	for step := 0; step < 3; step++ {
		tape := NewTape()
		loss, err := Mul(tape, w, w) // loss = w^2, grad = 2w
		if err != nil {
			t.Fatal(err)
		}
		losses = append(losses, loss.Value.Float64()[0])
		if err := tape.Backward(nil); err != nil {
			t.Fatal(err)
		}
		if err := opt.Step([]*Variable{w}); err != nil {
			t.Fatal(err)
		}
		opt.ZeroGrad([]*Variable{w})
	}
	// w: 1 -> 0.8 -> 0.64 -> 0.512; losses shrink monotonically.
	if !(losses[0] > losses[1] && losses[1] > losses[2]) {
		t.Fatalf("losses not decreasing: %v", losses)
	}
	if got := w.Value.Float64()[0]; math.Abs(got-0.512) > 1e-9 {
		t.Fatalf("w = %v, want 0.512", got)
	}
}

func checkClose(t *testing.T, name string, got, want []float64, tol float64) {
	t.Helper()
	if len(got) != len(want) {
		t.Fatalf("%s: length %d, want %d", name, len(got), len(want))
	}
	for i := range got {
		if math.IsNaN(got[i]) || math.Abs(got[i]-want[i]) > tol {
			t.Fatalf("%s[%d] = %v, want %v (tol %g)", name, i, got[i], want[i], tol)
		}
	}
}
