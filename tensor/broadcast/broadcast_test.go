package broadcast

import (
	"reflect"
	"testing"
)

// Regression test: BroadcastShapes compared dimensions right-aligned but
// wrote the output left-aligned, so any rank-mismatched broadcast (the
// only case broadcasting exists for when ranks differ) produced a reversed
// shape. Equal-rank shapes accidentally worked, which is why it survived.
func TestBroadcastShapesRankMismatch(t *testing.T) {
	cases := []struct {
		a, b, want []int
	}{
		{[]int{2, 3}, []int{3}, []int{2, 3}},
		{[]int{2, 3}, []int{1}, []int{2, 3}},
		{[]int{2, 1}, []int{1, 4}, []int{2, 4}},
		{[]int{3}, []int{2, 3}, []int{2, 3}},
		{[]int{2, 3, 4}, []int{4}, []int{2, 3, 4}},
		{[]int{2, 3, 4}, []int{3, 1}, []int{2, 3, 4}},
		{[]int{2, 3}, []int{2, 3}, []int{2, 3}},
		{[]int{5}, []int{5}, []int{5}},
	}
	for _, c := range cases {
		got, err := BroadcastShapes(c.a, c.b)
		if err != nil {
			t.Fatalf("BroadcastShapes(%v,%v): %v", c.a, c.b, err)
		}
		if !reflect.DeepEqual(got, c.want) {
			t.Fatalf("BroadcastShapes(%v,%v) = %v, want %v", c.a, c.b, got, c.want)
		}
	}
}

func TestBroadcastShapesRejects(t *testing.T) {
	if _, err := BroadcastShapes([]int{2, 3}, []int{4}); err == nil {
		t.Fatal("an un-broadcastable pair was accepted")
	}
	if _, err := BroadcastShapes([]int{2}, []int{3}); err == nil {
		t.Fatal("an un-broadcastable pair was accepted")
	}
}

func TestExpandStridesAndRowMajor(t *testing.T) {
	got, err := ExpandStrides([]int{3}, []int{2, 3})
	if err != nil {
		t.Fatalf("ExpandStrides: %v", err)
	}
	if !reflect.DeepEqual(got, []int{0, 1}) {
		t.Fatalf("ExpandStrides = %v, want [0 1]", got)
	}
	got2, err := ExpandStrides([]int{2, 1}, []int{2, 3})
	if err != nil {
		t.Fatalf("ExpandStrides: %v", err)
	}
	// Row-major strides of [2,1] are [1,1]; the expanded dim gets stride 0.
	if !reflect.DeepEqual(got2, []int{1, 0}) {
		t.Fatalf("ExpandStrides = %v, want [1 0]", got2)
	}
}
