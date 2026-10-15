package model

import (
	"math"
	"testing"

	"github.com/astrovox/astrovox/autograd"
	"github.com/astrovox/astrovox/tensor"
)

func varOf(vals []float64, dims ...int) *autograd.Variable {
	return autograd.NewVariable(tensorOf(vals, dims...), false)
}

func tensorOf(vals []float64, dims ...int) *tensor.Tensor {
	t, err := tensor.New(tensor.Float64, dims)
	if err != nil {
		panic(err)
	}
	copy(t.Float64(), vals)
	return t
}

func floatVals(v *autograd.Variable) []float64 { return v.Value.Float64() }

func closeTo(t *testing.T, name string, got, want []float64, tol float64) {
	t.Helper()
	if len(got) != len(want) {
		t.Fatalf("%s: length %d, want %d", name, len(got), len(want))
	}
	for i := range got {
		if math.IsNaN(got[i]) || math.Abs(got[i]-want[i]) > tol {
			t.Fatalf("%s[%d] = %v, want %v", name, i, got[i], want[i])
		}
	}
}

// TestLinearForwardMatchesReference checks the layer against a direct
// computation with the same stored weights, not against itself.
func TestLinearForwardMatchesReference(t *testing.T) {
	l, err := NewLinear("fc1", 3, 2, 42)
	if err != nil {
		t.Fatal(err)
	}
	x := varOf([]float64{1, 2, 3, 4, 5, 6}, 2, 3)
	out, err := l.Forward(nil, x)
	if err != nil {
		t.Fatal(err)
	}
	w, b := floatVals(l.W), floatVals(l.B)
	want := make([]float64, 4)
	for i := 0; i < 2; i++ {
		for j := 0; j < 2; j++ {
			var acc float64
			for k := 0; k < 3; k++ {
				acc += floatVals(x)[i*3+k] * w[k*2+j]
			}
			want[i*2+j] = acc + b[j]
		}
	}
	closeTo(t, "linear forward", floatVals(out), want, 1e-12)

	// Shape validation.
	if _, err := l.Forward(nil, varOf([]float64{1, 2}, 2)); err == nil {
		t.Fatal("a 1-D input was accepted")
	}
	if _, err := l.Forward(nil, varOf([]float64{1, 2, 3, 4}, 2, 2)); err == nil {
		t.Fatal("a wrong input width was accepted")
	}
}

// TestLinearDeterministicInit: same seed and shape produce identical
// weights, which is what makes checkpoints and tests reproducible.
func TestLinearDeterministicInit(t *testing.T) {
	a, err := NewLinear("fc", 4, 3, 7)
	if err != nil {
		t.Fatal(err)
	}
	b, err := NewLinear("fc", 4, 3, 7)
	if err != nil {
		t.Fatal(err)
	}
	closeTo(t, "same seed W", floatVals(a.W), floatVals(b.W), 0)
	closeTo(t, "same seed b", floatVals(a.B), floatVals(b.B), 0)
	c, err := NewLinear("fc", 4, 3, 8)
	if err != nil {
		t.Fatal(err)
	}
	if floatVals(a.W)[0] == floatVals(c.W)[0] {
		t.Fatal("different seeds produced identical weights")
	}
	// Bias starts at zero.
	for _, v := range floatVals(a.B) {
		if v != 0 {
			t.Fatalf("bias init = %v, want 0", v)
		}
	}
}

// TestLinearGradientsFlow: after a loss and backward, both parameters
// receive finite-difference-correct gradients.
func TestLinearGradientsFlow(t *testing.T) {
	l, err := NewLinear("fc", 3, 2, 11)
	if err != nil {
		t.Fatal(err)
	}
	xVals := []float64{0.5, -1.0, 2.0, 1.5, 0.25, -0.75}
	tgt := []float64{1.0, 0.0, 0.0, -1.0}

	tape := autograd.NewTape()
	x := autograd.NewVariable(tensorOf(xVals, 2, 3), false)
	pred, err := l.Forward(tape, x)
	if err != nil {
		t.Fatal(err)
	}
	loss, err := MSELoss(tape, pred, varOf(tgt, 2, 2))
	if err != nil {
		t.Fatal(err)
	}
	// Reference loss.
	wv, bv := floatVals(l.W), floatVals(l.B)
	var want float64
	for i := 0; i < 2; i++ {
		for j := 0; j < 2; j++ {
			var acc float64
			for k := 0; k < 3; k++ {
				acc += xVals[i*3+k] * wv[k*2+j]
			}
			d := acc + bv[j] - tgt[i*2+j]
			want += d * d
		}
	}
	want /= 4
	if got := floatVals(loss)[0]; math.Abs(got-want) > 1e-12 {
		t.Fatalf("loss = %v, want %v", got, want)
	}
	if err := tape.Backward(nil); err != nil {
		t.Fatal(err)
	}
	// dL/db_j = sum_i 2*d_ij / n
	wantB := make([]float64, 2)
	for j := 0; j < 2; j++ {
		var s float64
		for i := 0; i < 2; i++ {
			var acc float64
			for k := 0; k < 3; k++ {
				acc += xVals[i*3+k] * wv[k*2+j]
			}
			s += 2 * (acc + bv[j] - tgt[i*2+j])
		}
		wantB[j] = s / 4
	}
	if l.B.Grad == nil {
		t.Fatal("bias received no gradient")
	}
	closeTo(t, "db", l.B.Grad.Float64(), wantB, 1e-12)
}

func TestSequentialAndMLP(t *testing.T) {
	m, err := NewMLP("mlp", []int{4, 5, 3}, ActRelu, 3)
	if err != nil {
		t.Fatal(err)
	}
	x := varOf([]float64{1, 2, 3, 4, 5, 6, 7, 8}, 2, 4)
	out, err := m.Forward(nil, x)
	if err != nil {
		t.Fatal(err)
	}
	if got := out.Value.Shape().Dims(); got[0] != 2 || got[1] != 3 {
		t.Fatalf("MLP output shape = %v, want [2 3]", got)
	}
	// Hidden relu output must be non-negative somewhere, and the output
	// layer is linear, so negatives are permitted.
	if len(m.Parameters()) != 4 {
		t.Fatalf("MLP has %d parameters, want 4 (two layers x W,b)", len(m.Parameters()))
	}

	params, err := Flatten(m)
	if err != nil {
		t.Fatal(err)
	}
	want := []string{"mlp.fc0.W", "mlp.fc0.b", "mlp.fc1.W", "mlp.fc1.b"}
	if len(params) != 4 {
		t.Fatalf("Flatten returned %d parameters, want 4", len(params))
	}
	for i, p := range params {
		if p.Name != want[i] {
			t.Fatalf("parameter %d name = %q, want %q", i, p.Name, want[i])
		}
	}

	// A bad size list is refused.
	if _, err := NewMLP("mlp", []int{4}, ActRelu, 1); err == nil {
		t.Fatal("a single-size MLP was accepted")
	}
	if _, err := NewMLP("mlp", []int{4, 0, 2}, ActRelu, 1); err == nil {
		t.Fatal("a zero-size MLP was accepted")
	}
	// Sequential validation.
	if _, err := NewSequential("s"); err == nil {
		t.Fatal("an empty sequential was accepted")
	}
	if _, err := NewSequential("s", nil); err == nil {
		t.Fatal("a nil module was accepted")
	}
}

// TestSharedParameterIsRejectedByFlatten pins the duplicate-parameter
// check: sharing a module inside one tree would checkpoint its state
// under two names.
func TestSharedParameterIsRejectedByFlatten(t *testing.T) {
	shared, err := NewLinear("shared", 2, 2, 5)
	if err != nil {
		t.Fatal(err)
	}
	seq, err := NewSequential("dupe", shared, shared)
	if err != nil {
		t.Fatal(err)
	}
	if _, err := Flatten(seq); err == nil {
		t.Fatal("a shared module was flattened without an error")
	}
}
