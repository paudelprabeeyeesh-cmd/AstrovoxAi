package planner

import "testing"

func TestAnalyzeLifetimes(t *testing.T) {
	ops := []OpInfo{
		{"mul", []string{"a", "b"}, []string{"c"}},
		{"add", []string{"c", "d"}, []string{"e"}},
		{"relu", []string{"e"}, []string{"f"}},
	}

	lts := AnalyzeLifetimes(ops)

	expected := map[string]bool{
		"a": true, "b": true, "c": true,
		"d": true, "e": true, "f": true,
	}
	if len(lts) != len(expected) {
		t.Fatalf("got %d lifetimes, want %d", len(lts), len(expected))
	}
	for _, lt := range lts {
		if !expected[lt.TensorID] {
			t.Errorf("unexpected lifetime for %s", lt.TensorID)
		}
	}
}

func TestAnalyzeLifetimesEmpty(t *testing.T) {
	if got := AnalyzeLifetimes(nil); got != nil {
		t.Error("nil input should return nil")
	}
}

func TestByStartSort(t *testing.T) {
	lts := []Lifetime{
		{"b", Interval{2, 5}},
		{"a", Interval{0, 3}},
		{"c", Interval{0, 10}},
	}
	sort.Sort(ByStart(lts))
	if lts[0].TensorID != "a" || lts[1].TensorID != "c" || lts[2].TensorID != "b" {
		t.Errorf("sort order wrong: %v", lts)
	}
}
