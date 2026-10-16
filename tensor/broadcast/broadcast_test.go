package broadcast

import (
	"reflect"
	"strconv"
	"strings"
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

// FuzzBroadcastShapes feeds arbitrary shape pairs to BroadcastShapes.
// The function must never panic: invalid inputs are rejected with an
// error, valid inputs produce a shape whose rank equals max(len(a),len(b))
// and whose dims equal the right-aligned broadcast rule.
func FuzzBroadcastShapes(f *testing.F) {
	f.Add("2,3", "3")
	f.Add("2,3", "2,3")
	f.Add("5", "5")
	f.Add("", "3")
	f.Add("3", "")
	f.Fuzz(func(t *testing.T, aStr, bStr string) {
		a := parseDims(aStr)
		b := parseDims(bStr)
		got, err := BroadcastShapes(a, b)
		if err != nil {
			return
		}
		if len(got) != max(len(a), len(b)) {
			t.Fatalf("BroadcastShapes(%v,%v) rank = %d, want %d", a, b, len(got), max(len(a), len(b)))
		}
		// Verify right-aligned broadcast: for each output dim from the
		// right, sizes must be equal or one of them must be 1 (absent dims
		// count as 1).
		ra, rb := len(a)-1, len(b)-1
		for ro := len(got) - 1; ro >= 0; ro-- {
			sa, sb := 1, 1
			if ra >= 0 {
				sa = a[ra]
				ra--
			}
			if rb >= 0 {
				sb = b[rb]
				rb--
			}
			outDim := got[ro]
			if sa != 1 && sb != 1 && sa != sb {
				t.Fatalf("BroadcastShapes(%v,%v) = %v: dim %d (%d vs %d) not broadcastable", a, b, got, ro, sa, sb)
			}
			if outDim != sa && outDim != sb {
				t.Fatalf("BroadcastShapes(%v,%v) = %v: output dim %d = %d, expected %d or %d", a, b, got, ro, outDim, sa, sb)
			}
		}
	})
}

func parseDims(s string) []int {
	if s == "" {
		return nil
	}
	parts := strings.Split(s, ",")
	dims := make([]int, 0, len(parts))
	for _, p := range parts {
		if p == "" {
			continue
		}
		d, err := strconv.Atoi(p)
		if err != nil || d < 0 {
			continue
		}
		dims = append(dims, d)
	}
	return dims
}

func max(a, b int) int {
	if a > b {
		return a
	}
	return b
}
