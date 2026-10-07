package benchmark

import (
	"os"
	"path/filepath"
	"testing"
)

func TestHarnessRun(t *testing.T) {
	h := Harness{WarmupRuns: 1, Runs: 5, DropOutlier: true}
	res, err := h.Run("test_op", func(int) {
		for i := 0; i < 100000; i++ {
			benchWorkload(i)
		}
	})
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if res.Name != "test_op" {
		t.Fatalf("name = %q, want test_op", res.Name)
	}
	if res.Runs < 1 || res.Runs > 5 {
		t.Fatalf("runs = %d, want 1..5 (outliers may be dropped)", res.Runs)
	}
	if res.NanosMean <= 0 {
		t.Fatalf("mean = %v, want > 0", res.NanosMean)
	}
	if res.NanosP50 > res.NanosP95 || res.NanosP95 > res.NanosP99 {
		t.Fatalf("percentiles not ordered: p50=%v p95=%v p99=%v",
			res.NanosP50, res.NanosP95, res.NanosP99)
	}
	if res.OpsPerSec <= 0 {
		t.Fatalf("ops/s = %v, want > 0", res.OpsPerSec)
	}
	if res.CoV < 0 {
		t.Fatalf("cov = %v, want >= 0", res.CoV)
	}
}

func TestHarnessRunNil(t *testing.T) {
	if _, err := (Harness{}).Run("x", nil); err == nil {
		t.Fatal("expected error for nil function")
	}
}

func TestHarnessRunBytes(t *testing.T) {
	h := Harness{WarmupRuns: 1, Runs: 3}
	res, bytes, err := h.RunBytes("alloc_op", func(int) {
		bytesSink = make([]byte, 1024)
	})
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if res == nil {
		t.Fatal("expected result")
	}
	if bytes < 1024 {
		t.Fatalf("bytesPerOp = %d, want >= 1024", bytes)
	}
}

func TestRegressed(t *testing.T) {
	base := &Result{Name: "op", NanosP95: 100}
	tests := []struct {
		name      string
		candidate *Result
		threshold float64
		want      bool
	}{
		{"same", &Result{NanosP95: 100}, 0.05, false},
		{"slightly faster", &Result{NanosP95: 95}, 0.05, false},
		{"within threshold", &Result{NanosP95: 104}, 0.05, false},
		{"regressed", &Result{NanosP95: 110}, 0.05, true},
		{"nil baseline", nil, 0.05, false},
		{"nil candidate", &Result{NanosP95: 1}, 0.05, false},
	}
	for _, tt := range tests {
		if got := Regressed(base, tt.candidate, tt.threshold); got != tt.want {
			t.Errorf("%s: Regressed = %v, want %v", tt.name, got, tt.want)
		}
	}
}

func TestParseBenchLine(t *testing.T) {
	res := parseBenchLine("BenchmarkTensorAdd-8   \t   1000\t   25000 ns/op\t   512 B/op\t   2 allocs/op")
	if res == nil {
		t.Fatal("expected parsed result")
	}
	if res.Name != "BenchmarkTensorAdd" {
		t.Fatalf("name = %q", res.Name)
	}
	if res.Iterations != 1000 {
		t.Fatalf("iterations = %d", res.Iterations)
	}
	if res.NanosPerOp != 25000 {
		t.Fatalf("nanos = %v", res.NanosPerOp)
	}
	if res.BytesPerOp != 512 || res.AllocsPerOp != 2 {
		t.Fatalf("bytes=%d allocs=%d", res.BytesPerOp, res.AllocsPerOp)
	}
}

func TestParseBenchLineNoMatch(t *testing.T) {
	for _, line := range []string{
		"ok  \tgithub.com/astrovox/astrovox\t0.5s",
		"goos: windows",
		"",
		"PASS",
	} {
		if res := parseBenchLine(line); res != nil {
			t.Errorf("expected no parse for %q, got %+v", line, res)
		}
	}
}

func TestRunnerRun(t *testing.T) {
	r := Runner{
		Packages:   []string{"github.com/astrovox/astrovox/internal/arch"},
		BenchRegex: "BenchmarkBuildDependencyGraph",
		BenchTime:  "10x",
		Count:      1,
	}
	results, err := r.Run()
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if len(results) == 0 {
		t.Fatal("expected results")
	}
	if results[0].Name != "BenchmarkBuildDependencyGraph" {
		t.Fatalf("name = %q", results[0].Name)
	}
	if results[0].NanosPerOp <= 0 {
		t.Fatalf("nanos = %v", results[0].NanosPerOp)
	}
}

func TestCompare(t *testing.T) {
	baseline := []BenchResult{
		{Name: "A", NanosPerOp: 100},
		{Name: "B", NanosPerOp: 200},
	}
	current := []BenchResult{
		{Name: "A", NanosPerOp: 101},
		{Name: "B", NanosPerOp: 300},
		{Name: "C", NanosPerOp: 50},
	}
	regs := Compare(baseline, current, 0.05)
	if len(regs) != 1 {
		t.Fatalf("expected 1 regression, got %v", regs)
	}
	if regs[0].Name != "B" {
		t.Fatalf("regression = %q, want B", regs[0].Name)
	}
	if regs[0].BaselineNs != 200 || regs[0].CurrentNs != 300 {
		t.Fatalf("unexpected regression: %+v", regs[0])
	}
	wantChange := (300 - 200) / 200.0
	if regs[0].Change != wantChange {
		t.Fatalf("change = %v, want %v", regs[0].Change, wantChange)
	}
}

func TestBaselineRoundTrip(t *testing.T) {
	path := filepath.Join(t.TempDir(), "baseline.json")
	results := []BenchResult{
		{Name: "A", Iterations: 100, NanosPerOp: 1234.5, BytesPerOp: 64, AllocsPerOp: 1},
		{Name: "B", Iterations: 200, NanosPerOp: 999},
	}
	if err := SaveBaseline(path, results); err != nil {
		t.Fatalf("save: %v", err)
	}
	loaded, err := LoadBaseline(path)
	if err != nil {
		t.Fatalf("load: %v", err)
	}
	if len(loaded) != 2 {
		t.Fatalf("loaded %d results", len(loaded))
	}
	if loaded[0].Name != "A" || loaded[0].NanosPerOp != 1234.5 ||
		loaded[0].BytesPerOp != 64 || loaded[0].AllocsPerOp != 1 {
		t.Fatalf("unexpected result: %+v", loaded[0])
	}
	if loaded[1].Name != "B" || loaded[1].Iterations != 200 {
		t.Fatalf("unexpected result: %+v", loaded[1])
	}
}

func TestLoadBaselineMissing(t *testing.T) {
	if _, err := LoadBaseline(filepath.Join(t.TempDir(), "missing.json")); err == nil {
		t.Fatal("expected error for missing file")
	}
}

func TestCollectorProfiles(t *testing.T) {
	dir := t.TempDir()
	c := Collector{
		CPUPath:  filepath.Join(dir, "cpu.pprof"),
		HeapPath: filepath.Join(dir, "heap.pprof"),
	}
	err := c.Collect(func() {
		_ = make([]byte, 1<<20)
	})
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	for _, p := range []string{c.CPUPath, c.HeapPath} {
		info, err := os.Stat(p)
		if err != nil {
			t.Fatalf("profile %s: %v", p, err)
		}
		if info.Size() == 0 {
			t.Fatalf("profile %s is empty", p)
		}
	}
}

func TestCollectorNilWorkload(t *testing.T) {
	if err := (&Collector{}).Collect(nil); err == nil {
		t.Fatal("expected error for nil workload")
	}
}

func TestTopAllocators(t *testing.T) {
	dir := t.TempDir()
	heapPath := filepath.Join(dir, "heap.pprof")
	c := Collector{HeapPath: heapPath}
	err := c.Collect(func() {
		sink = make([]byte, 4<<20)
	})
	if err != nil {
		t.Fatalf("collect: %v", err)
	}
	sites, err := TopAllocators(heapPath, 5)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if len(sites) == 0 {
		t.Fatal("expected allocation sites")
	}
	found := false
	for _, s := range sites {
		if s.Bytes > 0 && s.Function != "" {
			found = true
		}
	}
	if !found {
		t.Fatalf("no meaningful sites: %v", sites)
	}
}

var sink []byte

var bytesSink []byte

var intSink int

// benchWorkload is a compiler barrier: noinline keeps the loop
// side effects observable to the timer.
//
//go:noinline
func benchWorkload(i int) {
	intSink += i % 7
}

func TestParseSize(t *testing.T) {
	tests := []struct {
		in   string
		want int64
	}{
		{"0", 0},
		{"1024B", 1024},
		{"2KB", 2048},
		{"2kB", 2048},
		{"4MB", 4 << 20},
		{"1GB", 1 << 30},
		{"1.5MB", 3 << 19},
		{"4097.37kB", 4195706},
	}
	for _, tt := range tests {
		got, err := parseSize(tt.in)
		if err != nil {
			t.Errorf("parseSize(%q): %v", tt.in, err)
			continue
		}
		if got != tt.want {
			t.Errorf("parseSize(%q) = %d, want %d", tt.in, got, tt.want)
		}
	}
}

func TestReductionPassAnalyze(t *testing.T) {
	pass := ReductionPass{TopN: 5, TempDir: t.TempDir()}
	report, err := pass.Analyze(func() {
		for i := 0; i < 100; i++ {
			_ = make([]byte, 4096)
		}
	})
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if len(report.Sites) == 0 {
		t.Fatal("expected sites")
	}
	if report.TotalBytes <= 0 {
		t.Fatalf("total bytes = %d", report.TotalBytes)
	}
	for i := 1; i < len(report.Sites); i++ {
		if report.Sites[i-1].Bytes < report.Sites[i].Bytes {
			t.Fatalf("sites not sorted: %v", report.Sites)
		}
	}
	hot := report.Hotspots(0.0)
	if len(hot) == 0 {
		t.Fatal("expected hotspots at zero threshold")
	}
}

func TestReductionPassNilWorkload(t *testing.T) {
	if _, err := (&ReductionPass{}).Analyze(nil); err == nil {
		t.Fatal("expected error for nil workload")
	}
}

func TestSuggestReduction(t *testing.T) {
	report := &ReductionReport{Sites: []AllocSite{{Bytes: 1000}}, TotalBytes: 1000}
	if msg := SuggestReduction(report, 10, 200); msg != "" {
		t.Fatalf("expected no suggestion, got %q", msg)
	}
	msg := SuggestReduction(report, 10, 50)
	if msg == "" {
		t.Fatal("expected suggestion")
	}
	if SuggestReduction(nil, 10, 50) != "" {
		t.Fatal("expected no suggestion for nil report")
	}
}
