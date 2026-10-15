package reduce

import (
	"math"
	"testing"

	"github.com/astrovox/astrovox/tensor"
)

// First test suite for the reduce package. Every reduction is checked
// against an independently computed reference, and the non-contiguous
// regression cases pin the fix that materializes views before traversal:
// the plan derives strides from the shape, so reading a transposed or
// sliced view in storage order silently reduced the wrong data.

func mkv(vals []float64, dims ...int) *tensor.Tensor {
	t, err := tensor.New(tensor.Float64, dims)
	if err != nil {
		panic(err)
	}
	copy(t.Float64(), vals)
	return t
}

func fv2(t *tensor.Tensor) []float64 { return t.Float64() }

func TestSumAllAndDims(t *testing.T) {
	x := mkv([]float64{1, 2, 3, 4, 5, 6}, 2, 3)

	all, err := Sum(x, nil, false)
	if err != nil {
		t.Fatalf("Sum all: %v", err)
	}
	if got := all.Float64(); len(got) != 1 || got[0] != 21 {
		t.Fatalf("Sum all = %v, want [21]", got)
	}

	// Reduce dim 1: [6, 15].
	r1, err := Sum(x, []int{1}, false)
	if err != nil {
		t.Fatalf("Sum dim1: %v", err)
	}
	got, want := r1.Float64(), []float64{6, 15}
	if len(got) != 2 || math.Abs(got[0]-want[0]) > 1e-9 || math.Abs(got[1]-want[1]) > 1e-9 {
		t.Fatalf("Sum dim1 = %v, want %v", got, want)
	}

	// Reduce dim 0 with keepDims: [[5 7 9]].
	r0k, err := Sum(x, []int{0}, true)
	if err != nil {
		t.Fatalf("Sum dim0 keep: %v", err)
	}
	got = r0k.Float64()
	want = []float64{5, 7, 9}
	if len(got) != 3 {
		t.Fatalf("Sum dim0 keep shape = %v", r0k.Shape().Dims())
	}
	for i := range want {
		if math.Abs(got[i]-want[i]) > 1e-9 {
			t.Fatalf("Sum dim0 keep = %v, want %v", got, want)
		}
	}
}

func TestMeanVarStdMinMaxProd(t *testing.T) {
	x := mkv([]float64{1, 2, 3, 4, 5, 6}, 2, 3)

	mean, err := Mean(x, []int{1}, false)
	if err != nil {
		t.Fatalf("Mean: %v", err)
	}
	got := mean.Float64()
	if math.Abs(got[0]-2) > 1e-9 || math.Abs(got[1]-5) > 1e-9 {
		t.Fatalf("Mean = %v, want [2 5]", got)
	}

	v, err := Var(x, nil, false)
	if err != nil {
		t.Fatalf("Var: %v", err)
	}
	// Population variance of 1..6: mean 3.5, var = 17.5/6.
	if got := v.Float64(); math.Abs(got[0]-17.5/6) > 1e-9 {
		t.Fatalf("Var = %v, want %v", got, 17.5/6)
	}

	s, err := Std(x, nil, false)
	if err != nil {
		t.Fatalf("Std: %v", err)
	}
	if got := s.Float64(); math.Abs(got[0]-math.Sqrt(17.5/6)) > 1e-9 {
		t.Fatalf("Std = %v", got)
	}

	mx, err := Max(x, nil, false)
	if err != nil {
		t.Fatalf("Max: %v", err)
	}
	if got := mx.Float64(); got[0] != 6 {
		t.Fatalf("Max = %v, want 6", got)
	}
	mn, err := Min(x, nil, false)
	if err != nil {
		t.Fatalf("Min: %v", err)
	}
	if got := mn.Float64(); got[0] != 1 {
		t.Fatalf("Min = %v, want 1", got)
	}
	p, err := Prod(x, []int{1}, false)
	if err != nil {
		t.Fatalf("Prod: %v", err)
	}
	got = p.Float64()
	if got[0] != 6 || got[1] != 120 {
		t.Fatalf("Prod = %v, want [6 120]", got)
	}
}

func TestArgMaxArgMin(t *testing.T) {
	x := mkv([]float64{1, 5, 2, 9, 3, 7}, 2, 3)
	am, err := ArgMax(x, 1)
	if err != nil {
		t.Fatalf("ArgMax: %v", err)
	}
	got := am.Int64()
	// Rows [1,5,2] and [9,3,7]: argmax 1 and 0.
	if got[0] != 1 || got[1] != 0 {
		t.Fatalf("ArgMax = %v, want [1 0]", got)
	}
	an, err := ArgMin(x, 1)
	if err != nil {
		t.Fatalf("ArgMin: %v", err)
	}
	got = an.Int64()
	// Rows [1,5,2] and [9,3,7]: argmin 0 and 1.
	if got[0] != 0 || got[1] != 1 {
		t.Fatalf("ArgMin = %v, want [0 1]", got)
	}
}

func TestCumSumAndNorm(t *testing.T) {
	x := mkv([]float64{1, 2, 3, 4, 5, 6}, 2, 3)
	cs, err := CumSum(x, 1)
	if err != nil {
		t.Fatalf("CumSum: %v", err)
	}
	got, want := cs.Float64(), []float64{1, 3, 6, 4, 9, 15}
	for i := range want {
		if got[i] != want[i] {
			t.Fatalf("CumSum = %v, want %v", got, want)
		}
	}

	n, err := Norm(x, 2, nil, false)
	if err != nil {
		t.Fatalf("Norm: %v", err)
	}
	// L2 norm of 1..6 = sqrt(91).
	if got := n.Float64(); math.Abs(got[0]-math.Sqrt(91)) > 1e-9 {
		t.Fatalf("Norm = %v, want %v", got, math.Sqrt(91))
	}
}

// TestReductionsOnNonContiguousViews is the regression test for the
// storage-order traversal bug: a reduction over a transposed tensor must
// equal the reduction over the same values in their original layout.
func TestReductionsOnNonContiguousViews(t *testing.T) {
	x := mkv([]float64{1, 2, 3, 4, 5, 6}, 2, 3)
	tr, err := x.Transpose(0, 1) // [3, 2] view of the same storage
	if err != nil {
		t.Fatalf("Transpose: %v", err)
	}

	// Sum over all elements is layout-independent: 21 either way.
	trSum, err := Sum(tr, nil, false)
	if err != nil {
		t.Fatalf("Sum on transpose: %v", err)
	}
	if got := trSum.Float64(); got[0] != 21 {
		t.Fatalf("Sum over transpose = %v, want 21", got)
	}

	// Row sums of the transpose are the column sums of the original:
	// [1+4, 2+5, 3+6] = [5 7 9].
	trRow, err := Sum(tr, []int{1}, false)
	if err != nil {
		t.Fatalf("Sum dim1 on transpose: %v", err)
	}
	got, want := trRow.Float64(), []float64{5, 7, 9}
	for i := range want {
		if math.Abs(got[i]-want[i]) > 1e-9 {
			t.Fatalf("row sums of transpose = %v, want %v", got, want)
		}
	}

	// Sliced view: rows with a stride.
	base := mkv([]float64{1, 2, 3, 4, 5, 6, 7, 8}, 4, 2)
	sl, err := base.Slice([]int{0, 0}, []int{4, 2})
	if err != nil {
		t.Fatalf("Slice: %v", err)
	}
	if s, err := Sum(sl, nil, false); err != nil {
		t.Fatalf("Sum on slice: %v", err)
	} else if got := s.Float64(); got[0] != 36 {
		t.Fatalf("Sum over slice = %v, want 36", got)
	}

	// CumSum and ArgMax over a transpose.
	cs, err := CumSum(tr, 1)
	if err != nil {
		t.Fatalf("CumSum on transpose: %v", err)
	}
	// Transposed logical data [[1,4],[2,5],[3,6]]: row cumsums [1,5],[2,7],[3,9].
	wantC := []float64{1, 5, 2, 7, 3, 9}
	gotC := cs.Float64()
	for i := range wantC {
		if gotC[i] != wantC[i] {
			t.Fatalf("CumSum over transpose = %v, want %v", gotC, wantC)
		}
	}
	am, err := ArgMax(tr, 1)
	if err != nil {
		t.Fatalf("ArgMax on transpose: %v", err)
	}
	// Rows [1,4],[2,5],[3,6]: argmax is 1, 1, 1.
	gotA := am.Int64()
	for i, v := range gotA {
		if v != 1 {
			t.Fatalf("ArgMax over transpose = %v, want all 1 (index %d = %d)", gotA, i, v)
		}
	}
}

func TestReductionsRejectWrongDtype(t *testing.T) {
	i32, err := tensor.New(tensor.Int32, []int{2, 2})
	if err != nil {
		t.Fatalf("New: %v", err)
	}
	if _, err := Sum(i32, nil, false); err == nil {
		t.Fatal("Sum accepted int32")
	}
	if _, err := Mean(i32, nil, false); err == nil {
		t.Fatal("Mean accepted int32")
	}
	if _, err := CumSum(i32, 0); err == nil {
		t.Fatal("CumSum accepted int32")
	}
	// Out-of-range reduction dim.
	x := mkv([]float64{1, 2, 3, 4}, 2, 2)
	if _, err := Sum(x, []int{2}, false); err == nil {
		t.Fatal("an out-of-range reduction dim was accepted")
	}
}
