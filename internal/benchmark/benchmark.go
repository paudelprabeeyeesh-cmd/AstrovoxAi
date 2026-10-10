// Package benchmark provides a statistical benchmark harness: warmup, timed
// iterations, outlier handling, percentiles, coefficient of variation, and
// baseline regression gating.
package benchmark

import (
	"fmt"
	"math"
	"runtime"
	"sort"
	"time"

	"github.com/astrovox/astrovox/internal/errors"
)

// Env captures the execution environment of a benchmark run.
type Env struct {
	GOOS       string `json:"goos"`
	GOARCH     string `json:"goarch"`
	GOMAXPROCS int    `json:"gomaxprocs"`
	CPU        string `json:"cpu,omitempty"`
}

// Result holds the statistics of one benchmark.
type Result struct {
	Name      string    `json:"name"`
	Env       Env       `json:"env"`
	Runs      int       `json:"runs"`
	Warmup    int       `json:"warmup"`
	NanosMean float64   `json:"nanos_mean"`
	NanosP50  float64   `json:"nanos_p50"`
	NanosP95  float64   `json:"nanos_p95"`
	NanosP99  float64   `json:"nanos_p99"`
	CoV       float64   `json:"cov"`
	OpsPerSec float64   `json:"ops_per_sec"`
	RawNanos  []float64 `json:"raw_nanos,omitempty"`
	// ClockFloor is true when at least one sample was faster than the
	// platform clock could resolve, so the numbers are a lower bound.
	ClockFloor bool `json:"clock_floor,omitempty"`
}

// Harness executes timed workloads with fixed warmup and run counts.
type Harness struct {
	WarmupRuns  int
	Runs        int
	DropOutlier bool
}

// DefaultHarness is the standard configuration: 3 warmup runs, 10 measured
// runs, outlier dropping enabled.
var DefaultHarness = Harness{WarmupRuns: 3, Runs: 10, DropOutlier: true}

// EnvOf captures the current runtime environment.
func EnvOf() Env {
	return Env{
		GOOS:       runtime.GOOS,
		GOARCH:     runtime.GOARCH,
		GOMAXPROCS: runtime.GOMAXPROCS(0),
	}
}

// Run executes fn warmup times, then runs measured iterations, returning
// aggregate statistics. fn receives the iteration index.
func (h Harness) Run(name string, fn func(int)) (*Result, error) {
	if fn == nil {
		return nil, errors.New(errors.CodeInvalidArgument, "benchmark function is nil").WithField("name", name)
	}
	for i := 0; i < h.WarmupRuns; i++ {
		fn(i)
	}
	samples := make([]float64, 0, h.Runs)
	clockFloor := false
	for i := 0; i < h.Runs; i++ {
		runtime.GC()
		start := time.Now()
		fn(i)
		elapsed := float64(time.Since(start).Nanoseconds())
		// A zero reading means the platform clock is coarser than the
		// measured work, not that the work was instantaneous. Record the
		// floor and keep the sample so statistics stay meaningful.
		if elapsed <= 0 {
			elapsed = 1
			clockFloor = true
		}
		samples = append(samples, elapsed)
	}
	if h.DropOutlier && len(samples) >= 4 {
		samples = dropOutliers(samples)
	}
	sort.Float64s(samples)
	mean := meanOf(samples)
	std := stdOf(samples, mean)
	cov := 0.0
	if mean > 0 {
		cov = std / mean
	}
	return &Result{
		Name:      name,
		Env:       EnvOf(),
		Runs:      len(samples),
		Warmup:    h.WarmupRuns,
		NanosMean: mean,
		NanosP50:  percentile(samples, 0.50),
		NanosP95:  percentile(samples, 0.95),
		NanosP99:  percentile(samples, 0.99),
		CoV:       cov,
		OpsPerSec: 1e9 / mean,
		RawNanos:  samples,
		ClockFloor: clockFloor,
	}, nil
}

// RunBytes is like Run but tracks bytes allocated per operation.
func (h Harness) RunBytes(name string, fn func(int)) (*Result, int64, error) {
	var bytesPerOp int64
	wrapped := func(i int) {
		before := runtimeStats()
		fn(i)
		after := runtimeStats()
		if i == 0 {
			bytesPerOp = int64(after.total - before.total)
		}
	}
	res, err := h.Run(name, wrapped)
	if err != nil {
		return nil, 0, err
	}
	return res, bytesPerOp, nil
}

type rtStats struct {
	total   uint64
	mallocs uint64
}

func runtimeStats() rtStats {
	var ms runtime.MemStats
	runtime.ReadMemStats(&ms)
	return rtStats{total: ms.TotalAlloc, mallocs: ms.Mallocs}
}

func dropOutliers(xs []float64) []float64 {
	sorted := append([]float64(nil), xs...)
	sort.Float64s(sorted)
	q1 := percentile(sorted, 0.25)
	q3 := percentile(sorted, 0.75)
	iqr := q3 - q1
	lo := q1 - 1.5*iqr
	hi := q3 + 1.5*iqr
	out := make([]float64, 0, len(xs))
	for _, x := range xs {
		if x >= lo && x <= hi {
			out = append(out, x)
		}
	}
	if len(out) == 0 {
		return xs
	}
	return out
}

func percentile(sorted []float64, p float64) float64 {
	if len(sorted) == 0 {
		return 0
	}
	if len(sorted) == 1 {
		return sorted[0]
	}
	idx := p * float64(len(sorted)-1)
	lo := int(math.Floor(idx))
	hi := int(math.Ceil(idx))
	if lo == hi {
		return sorted[lo]
	}
	frac := idx - float64(lo)
	return sorted[lo]*(1-frac) + sorted[hi]*frac
}

func meanOf(xs []float64) float64 {
	if len(xs) == 0 {
		return 0
	}
	sum := 0.0
	for _, x := range xs {
		sum += x
	}
	return sum / float64(len(xs))
}

func stdOf(xs []float64, mean float64) float64 {
	if len(xs) < 2 {
		return 0
	}
	sum := 0.0
	for _, x := range xs {
		d := x - mean
		sum += d * d
	}
	return math.Sqrt(sum / float64(len(xs)-1))
}

// Regressed reports whether candidate is a statistically meaningful regression
// against baseline (threshold is a fraction, e.g. 0.05 = 5%).
func Regressed(baseline, candidate *Result, threshold float64) bool {
	if baseline == nil || candidate == nil {
		return false
	}
	return candidate.NanosP95 > baseline.NanosP95*(1+threshold)
}

// String renders a human-readable single-line summary.
func (r *Result) String() string {
	return fmt.Sprintf("%-40s mean=%9.0fns p50=%9.0fns p95=%9.0fns p99=%9.0fns cov=%.3f ops/s=%9.0f",
		r.Name, r.NanosMean, r.NanosP50, r.NanosP95, r.NanosP99, r.CoV, r.OpsPerSec)
}
