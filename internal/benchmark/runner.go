package benchmark

import (
	"encoding/json"
	"fmt"
	"os"
	"os/exec"
	"regexp"
	"sort"
	"strconv"
	"strings"
)

// BenchResult is one parsed benchmark observation from
// a `go test -bench` run.
type BenchResult struct {
	Name        string  `json:"name"`
	Iterations  int     `json:"iterations"`
	NanosPerOp  float64 `json:"nanos_per_op"`
	BytesPerOp  int64   `json:"bytes_per_op,omitempty"`
	AllocsPerOp int64   `json:"allocs_per_op,omitempty"`
}

var benchLine = regexp.MustCompile(`^(Benchmark\S+?)(?:-\d+)?\s+(\d+)\s+([\d.]+) ns/op(.*)$`)

// parseBenchLine parses one `go test -bench` output line.
func parseBenchLine(line string) *BenchResult {
	m := benchLine.FindStringSubmatch(strings.TrimSpace(line))
	if m == nil {
		return nil
	}
	iters, err := strconv.Atoi(m[2])
	if err != nil {
		return nil
	}
	nanos, err := strconv.ParseFloat(m[3], 64)
	if err != nil {
		return nil
	}
	res := &BenchResult{
		Name:       m[1],
		Iterations: iters,
		NanosPerOp: nanos,
	}
	// Optional trailing columns: "  123 B/op   4 allocs/op".
	fields := strings.Fields(m[4])
	for i := 0; i+1 < len(fields); i++ {
		switch fields[i+1] {
		case "B/op":
			if v, err := strconv.ParseInt(fields[i], 10, 64); err == nil {
				res.BytesPerOp = v
			}
		case "allocs/op":
			if v, err := strconv.ParseInt(fields[i], 10, 64); err == nil {
				res.AllocsPerOp = v
			}
		}
	}
	return res
}

// Runner executes benchmark suites in CI.
type Runner struct {
	// Packages selects the packages to benchmark.
	Packages []string
	// BenchRegex filters benchmarks (go test -bench value).
	BenchRegex string
	// BenchTime sets the per-benchmark time budget.
	BenchTime string
	// Count repeats each benchmark.
	Count int
}

// DefaultRunner benchmarks all packages with a short time budget.
var DefaultRunner = Runner{
	Packages:   []string{"./..."},
	BenchRegex: ".",
	BenchTime:  "100ms",
	Count:      1,
}

// Run executes `go test -bench` and returns parsed results.
func (r *Runner) Run() ([]BenchResult, error) {
	args := []string{"test", "-count=1"}
	if r.BenchTime != "" {
		args = append(args, "-benchtime="+r.BenchTime)
	}
	if r.Count > 0 {
		args = append(args, fmt.Sprintf("-count=%d", r.Count))
	}
	args = append(args, "-bench="+r.BenchRegex)
	args = append(args, r.Packages...)

	cmd := exec.Command("go", args...)
	cmd.Env = os.Environ()
	out, err := cmd.CombinedOutput()
	if err != nil {
		return nil, fmt.Errorf("go test failed: %w\n%s", err, out)
	}

	var results []BenchResult
	for _, line := range strings.Split(string(out), "\n") {
		if res := parseBenchLine(line); res != nil {
			results = append(results, *res)
		}
	}
	if len(results) == 0 {
		return nil, fmt.Errorf("no benchmark results parsed from output:\n%s", out)
	}
	return results, nil
}

// Regression compares a current result against its baseline.
type Regression struct {
	Name       string  `json:"name"`
	BaselineNs float64 `json:"baseline_ns"`
	CurrentNs  float64 `json:"current_ns"`
	Change     float64 `json:"change"` // fraction, e.g. 0.1 = 10% slower
}

// Compare reports regressions of current against baseline.
// A result is flagged when its p-op time exceeds the baseline
// by more than threshold (a fraction, e.g. 0.05 = 5%).
func Compare(baseline, current []BenchResult, threshold float64) []Regression {
	base := make(map[string]BenchResult, len(baseline))
	for _, r := range baseline {
		base[r.Name] = r
	}
	var regressions []Regression
	for _, r := range current {
		b, ok := base[r.Name]
		if !ok || b.NanosPerOp <= 0 {
			continue
		}
		change := (r.NanosPerOp - b.NanosPerOp) / b.NanosPerOp
		if change > threshold {
			regressions = append(regressions, Regression{
				Name:       r.Name,
				BaselineNs: b.NanosPerOp,
				CurrentNs:  r.NanosPerOp,
				Change:     change,
			})
		}
	}
	sort.Slice(regressions, func(i, j int) bool {
		return regressions[i].Change > regressions[j].Change
	})
	return regressions
}

// SaveBaseline writes results to a JSON baseline file.
func SaveBaseline(path string, results []BenchResult) error {
	data, err := json.MarshalIndent(results, "", "  ")
	if err != nil {
		return err
	}
	return os.WriteFile(path, data, 0644)
}

// LoadBaseline reads results from a JSON baseline file.
func LoadBaseline(path string) ([]BenchResult, error) {
	data, err := os.ReadFile(path)
	if err != nil {
		return nil, err
	}
	var results []BenchResult
	if err := json.Unmarshal(data, &results); err != nil {
		return nil, err
	}
	return results, nil
}
