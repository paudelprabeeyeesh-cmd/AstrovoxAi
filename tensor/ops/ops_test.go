package ops

import (
	"math"
	"testing"

	"github.com/astrovox/astrovox/tensor"
)

// First test suite for the ops package. Every op is checked either against
// an independent reference or against an exact hand-computed value.

func mk(vals []float64, dims ...int) *tensor.Tensor {
	t, err := tensor.New(tensor.Float64, dims)
	if err != nil {
		panic(err)
	}
	copy(t.Float64(), vals)
	return t
}

func fv(t *tensor.Tensor) []float64 { return t.Float64() }

func eq(t *testing.T, name string, got, want []float64, tol float64) {
	t.Helper()
	if len(got) != len(want) {
		t.Fatalf("%s: len %d, want %d", name, len(got), len(want))
	}
	for i := range got {
		if math.Abs(got[i]-want[i]) > tol {
			t.Fatalf("%s[%d] = %v, want %v", name, i, got[i], want[i])
		}
	}
}

func TestElementwiseAndBroadcast(t *testing.T) {
	a := mk([]float64{1, 2, 3, 4, 5, 6}, 2, 3)
	b := mk([]float64{10, 20, 30}, 3)

	add, err := Add(a, b)
	if err != nil {
		t.Fatalf("Add: %v", err)
	}
	eq(t, "Add broadcast", fv(add), []float64{11, 22, 33, 14, 25, 36}, 0)

	sub, err := Sub(a, b)
	if err != nil {
		t.Fatalf("Sub: %v", err)
	}
	eq(t, "Sub broadcast", fv(sub), []float64{-9, -18, -27, -6, -15, -24}, 0)

	mul, err := Mul(a, b)
	if err != nil {
		t.Fatalf("Mul: %v", err)
	}
	eq(t, "Mul broadcast", fv(mul), []float64{10, 40, 90, 40, 100, 180}, 0)

	div, err := Div(a, b)
	if err != nil {
		t.Fatalf("Div: %v", err)
	}
	eq(t, "Div broadcast", fv(div), []float64{0.1, 0.1, 0.1, 0.4, 0.25, 0.2}, 1e-12)

	// Same-shape elementwise.
	c := mk([]float64{1, 1, 1, 1, 1, 1}, 2, 3)
	p, err := Pow(a, c)
	if err != nil {
		t.Fatalf("Pow: %v", err)
	}
	eq(t, "Pow", fv(p), fv(a), 1e-12)

	// Incompatible shapes are refused.
	if _, err := Add(mk([]float64{1, 2}, 2), mk([]float64{1, 2, 3}, 3)); err == nil {
		t.Fatal("an un-broadcastable shape pair was accepted")
	}
}

func TestUnaryAndScalarOps(t *testing.T) {
	x := mk([]float64{-2, -1, 0, 1, 2}, 5)
	neg, err := Neg(x)
	if err != nil {
		t.Fatalf("Neg: %v", err)
	}
	eq(t, "Neg", fv(neg), []float64{2, 1, 0, -1, -2}, 0)

	sc, err := Scale(x, 3)
	if err != nil {
		t.Fatalf("Scale: %v", err)
	}
	eq(t, "Scale", fv(sc), []float64{-6, -3, 0, 3, 6}, 0)

	as, err := AddScalar(x, 10)
	if err != nil {
		t.Fatalf("AddScalar: %v", err)
	}
	eq(t, "AddScalar", fv(as), []float64{8, 9, 10, 11, 12}, 0)

	ss, err := SubScalar(x, 1)
	if err != nil {
		t.Fatalf("SubScalar: %v", err)
	}
	eq(t, "SubScalar", fv(ss), []float64{-3, -2, -1, 0, 1}, 0)

	ms, err := MulScalar(x, -0.5)
	if err != nil {
		t.Fatalf("MulScalar: %v", err)
	}
	eq(t, "MulScalar", fv(ms), []float64{1, 0.5, 0, -0.5, -1}, 1e-12)

	ds, err := DivScalar(x, 2)
	if err != nil {
		t.Fatalf("DivScalar: %v", err)
	}
	eq(t, "DivScalar", fv(ds), []float64{-1, -0.5, 0, 0.5, 1}, 1e-12)

	if _, err := DivScalar(x, 0); err == nil {
		t.Fatal("division by zero was accepted")
	}

	r, err := Relu(x)
	if err != nil {
		t.Fatalf("Relu: %v", err)
	}
	eq(t, "Relu", fv(r), []float64{0, 0, 0, 1, 2}, 0)

	sg, err := Sigmoid(x)
	if err != nil {
		t.Fatalf("Sigmoid: %v", err)
	}
	want := make([]float64, 5)
	for i, v := range fv(x) {
		want[i] = 1 / (1 + math.Exp(-v))
	}
	eq(t, "Sigmoid", fv(sg), want, 1e-12)

	ex, err := Exp(x)
	if err != nil {
		t.Fatalf("Exp: %v", err)
	}
	for i, v := range fv(ex) {
		if math.Abs(v-math.Exp(fv(x)[i])) > 1e-12 {
			t.Fatalf("Exp[%d] = %v", i, v)
		}
	}
}

func TestSoftmax(t *testing.T) {
	// Rows sum to 1 and match the manual computation.
	x := mk([]float64{1, 2, 3, 1000, 1001, 1002}, 2, 3)
	out, err := Softmax(x, -1)
	if err != nil {
		t.Fatalf("Softmax: %v", err)
	}
	got := fv(out)
	var total float64
	for _, v := range got {
		if v < 0 || v > 1 {
			t.Fatalf("softmax produced an out-of-range probability %v", v)
		}
		total += v
	}
	if math.Abs(total-2) > 1e-12 {
		t.Fatalf("softmax rows sum to %v, want 2", total)
	}
	// The large row must not overflow to NaN: stability check.
	for _, v := range got[3:] {
		if math.IsNaN(v) || math.IsInf(v, 0) {
			t.Fatalf("softmax overflowed on large inputs: %v", got[3:])
		}
	}
	// Reference for the first row.
	denom := math.Exp(1-3) + math.Exp(2-3) + math.Exp(3-3)
	eq(t, "Softmax row0", got[:3], []float64{math.Exp(1-3) / denom, math.Exp(2-3) / denom, 1 / denom}, 1e-12)

	// Softmax along dim 0 of a column vector.
	col := mk([]float64{0, 0, 0}, 3, 1)
	oc, err := Softmax(col, 0)
	if err != nil {
		t.Fatalf("Softmax dim0: %v", err)
	}
	eq(t, "Softmax uniform", fv(oc), []float64{1.0 / 3, 1.0 / 3, 1.0 / 3}, 1e-12)

	// Out-of-range dim is refused.
	if _, err := Softmax(x, 2); err == nil {
		t.Fatal("an out-of-range softmax dim was accepted")
	}
	if _, err := Softmax(mk([]float64{1, 2}, 2), 0); err != nil {
		t.Fatalf("Softmax dim0 rank1: %v", err)
	}
}

func TestConcat(t *testing.T) {
	a := mk([]float64{1, 2, 3, 4}, 2, 2)
	b := mk([]float64{5, 6, 7, 8}, 2, 2)
	c := mk([]float64{9, 10, 11, 12}, 2, 2)

	// Dim 1: side by side.
	out, err := Concat([]*tensor.Tensor{a, b}, 1)
	if err != nil {
		t.Fatalf("Concat dim1: %v", err)
	}
	eq(t, "Concat dim1", fv(out), []float64{1, 2, 5, 6, 3, 4, 7, 8}, 0)

	// Dim 0: stacked.
	out0, err := Concat([]*tensor.Tensor{a, b, c}, 0)
	if err != nil {
		t.Fatalf("Concat dim0: %v", err)
	}
	eq(t, "Concat dim0", fv(out0), []float64{1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12}, 0)

	// Negative dim indexes from the end.
	outNeg, err := Concat([]*tensor.Tensor{a, b}, -1)
	if err != nil {
		t.Fatalf("Concat -1: %v", err)
	}
	eq(t, "Concat -1", fv(outNeg), fv(out), 0)

	// Rank mismatch and non-concat-dim mismatch are refused.
	if _, err := Concat([]*tensor.Tensor{a, mk([]float64{1, 2}, 2)}, 0); err == nil {
		t.Fatal("a rank mismatch was accepted")
	}
	if _, err := Concat([]*tensor.Tensor{a, mk([]float64{1, 2, 3, 4, 5, 6}, 2, 3)}, 0); err == nil {
		t.Fatal("a non-concat dim mismatch was accepted")
	}
	if _, err := Concat(nil, 0); err == nil {
		t.Fatal("an empty list was accepted")
	}
}

func TestDotAndMatMul(t *testing.T) {
	a := mk([]float64{1, 2, 3}, 3)
	b := mk([]float64{4, 5, 6}, 3)
	d, err := Dot(a, b)
	if err != nil {
		t.Fatalf("Dot: %v", err)
	}
	if d != 32 {
		t.Fatalf("Dot = %v, want 32", d)
	}

	am := mk([]float64{1, 2, 3, 4, 5, 6}, 2, 3)
	bm := mk([]float64{1, 4, 2, 5, 3, 6}, 3, 2)
	m, err := MatMul(am, bm)
	if err != nil {
		t.Fatalf("MatMul: %v", err)
	}
	// [[1*1+2*2+3*3, 1*4+2*5+3*6], [4*1+5*2+6*3, 4*4+5*5+6*6]]
	eq(t, "MatMul", fv(m), []float64{14, 32, 32, 77}, 0)

	// A transposed input is materialized, not read through the wrong view.
	tr, err := am.Transpose(0, 1)
	if err != nil {
		t.Fatalf("Transpose: %v", err)
	}
	mt, err := MatMul(tr, mk([]float64{1, 2}, 2, 1))
	if err != nil {
		t.Fatalf("MatMul transposed: %v", err)
	}
	eq(t, "MatMul transposed", fv(mt), []float64{1*1 + 4*2, 2*1 + 5*2, 3*1 + 6*2}, 0)

	if _, err := MatMul(am, mk([]float64{1, 2}, 2)); err == nil {
		t.Fatal("a contracting-dim mismatch was accepted")
	}
	if _, err := Dot(mk([]float64{1, 2}, 2), b); err == nil {
		t.Fatal("a dot length mismatch was accepted")
	}
}

func TestOpsRejectWrongDtype(t *testing.T) {
	i32, err := tensor.New(tensor.Int32, []int{2})
	if err != nil {
		t.Fatalf("New: %v", err)
	}
	if _, err := Add(i32, i32); err == nil {
		t.Fatal("a binary op accepted int32")
	}
	if _, err := Relu(i32); err == nil {
		t.Fatal("a unary op accepted int32")
	}
	if _, err := Softmax(i32, 0); err == nil {
		t.Fatal("softmax accepted int32")
	}
}
