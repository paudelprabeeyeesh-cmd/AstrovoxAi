package memviz

import (
	"strings"
	"testing"
)

func TestTrackerAllocateFree(t *testing.T) {
	tr := NewTracker()
	if err := tr.Allocate("w", "weights", 1024); err != nil {
		t.Fatal(err)
	}
	if tr.Usage() != 1024 {
		t.Errorf("usage: %d", tr.Usage())
	}
	if tr.Peak() != 1024 {
		t.Error("peak")
	}
	if err := tr.Free("w"); err != nil {
		t.Fatal(err)
	}
	if tr.Usage() != 0 {
		t.Errorf("expected 0 after free, got %d", tr.Usage())
	}
}

func TestTrackerMultipleRegions(t *testing.T) {
	tr := NewTracker()
	tr.Allocate("a", "weights", 1000)
	tr.Allocate("b", "activations", 500)
	tr.Allocate("c", "weights", 250)
	byC := tr.ByCategory()
	if byC["weights"] != 1250 || byC["activations"] != 500 {
		t.Errorf("categories: %v", byC)
	}
	if tr.Usage() != 1750 {
		t.Errorf("total: %d", tr.Usage())
	}
	if tr.RegionUsage("b") != 500 {
		t.Error("region usage")
	}
}

func TestTrackerInvalidAlloc(t *testing.T) {
	tr := NewTracker()
	if tr.Allocate("x", "c", 0) == nil {
		t.Error("expected zero-size error")
	}
	if tr.Allocate("x", "c", -1) == nil {
		t.Error("expected negative error")
	}
}

func TestTrackerFreeUnknown(t *testing.T) {
	tr := NewTracker()
	if tr.Free("nope") == nil {
		t.Error("expected unknown region error")
	}
}

func TestTrackerLive(t *testing.T) {
	tr := NewTracker()
	tr.Allocate("b", "x", 1)
	tr.Allocate("a", "x", 1)
	live := tr.Live()
	if len(live) != 2 || live[0] != "a" {
		t.Errorf("expected sorted live regions, got %v", live)
	}
	tr.Free("a")
	if len(tr.Live()) != 1 {
		t.Error("expected 1 live region")
	}
}

func TestFragmentation(t *testing.T) {
	// One contiguous free block => no external fragmentation.
	if f := Fragmentation(1000, []int64{500}); f != 0 {
		t.Errorf("expected 0, got %f", f)
	}
	// Split free blocks => fragmentation proportional to unusable slack.
	if f := Fragmentation(1000, []int64{100, 100}); f <= 0 {
		t.Errorf("expected positive fragmentation, got %f", f)
	}
	if Fragmentation(0, nil) != 0 {
		t.Error("zero allocated must be zero")
	}
}

func TestLargestFreeBlock(t *testing.T) {
	if LargestFreeBlock(nil) != 0 {
		t.Error("nil blocks")
	}
	if LargestFreeBlock([]int64{10, 50, 30}) != 50 {
		t.Error("largest block")
	}
}

func TestHumanBytes(t *testing.T) {
	cases := map[int64]string{
		512:         "512 B",
		2048:        "2.0 KiB",
		5 * 1 << 20: "5.0 MiB",
	}
	for in, want := range cases {
		if got := HumanBytes(in); got != want {
			t.Errorf("HumanBytes(%d) = %q, want %q", in, got, want)
		}
	}
}

func TestRenderASCII(t *testing.T) {
	out := RenderASCII(map[string]int64{"weights": 700, "activations": 300}, 20)
	if !strings.Contains(out, "weights") || !strings.Contains(out, "TOTAL") {
		t.Errorf("unexpected render:\n%s", out)
	}
	if !strings.Contains(out, "1000 B") {
		t.Error("expected total bytes")
	}
}

func TestRenderASCIIEmpty(t *testing.T) {
	out := RenderASCII(nil, 10)
	if !strings.Contains(out, "TOTAL") {
		t.Error("expected a header even when empty")
	}
}

func TestRenderFlame(t *testing.T) {
	regions := []Region{
		{Name: "big", Bytes: 900},
		{Name: "small", Bytes: 100},
	}
	out := RenderFlame(regions, 2)
	if !strings.Contains(out, "big") {
		t.Errorf("unexpected flame:\n%s", out)
	}
	if RenderFlame(nil, 4) != "(no regions)\n" {
		t.Error("empty flame")
	}
}

func TestReport(t *testing.T) {
	tr := NewTracker()
	tr.Allocate("w", "weights", 4096)
	out := Report(tr, []int64{1024})
	for _, want := range []string{"Memory usage", "Live bytes", "Peak bytes", "Fragmentation"} {
		if !strings.Contains(out, want) {
			t.Errorf("report missing %q:\n%s", want, out)
		}
	}
}