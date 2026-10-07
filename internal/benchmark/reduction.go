package benchmark

import (
	"fmt"
	"os"
	"path/filepath"
	"sort"
)

// ReductionPass identifies allocation hotspots in a workload by
// capturing a heap profile and ranking allocation sites.
type ReductionPass struct {
	// TopN limits the number of reported sites.
	TopN int
	// TempDir receives the captured heap profile; defaults to os.TempDir.
	TempDir string
}

// ReductionReport ranks allocation sites and totals.
type ReductionReport struct {
	// Sites are sorted by bytes, largest first.
	Sites []AllocSite `json:"sites"`
	// TotalBytes is the sum of reported site bytes.
	TotalBytes int64 `json:"total_bytes"`
	// ProfilePath is the captured heap profile.
	ProfilePath string `json:"profile_path"`
}

// Analyze runs fn with heap profiling and ranks allocation sites.
func (p *ReductionPass) Analyze(fn func()) (*ReductionReport, error) {
	if fn == nil {
		return nil, fmt.Errorf("nil workload")
	}
	topN := p.TopN
	if topN <= 0 {
		topN = 10
	}
	dir := p.TempDir
	if dir == "" {
		dir = os.TempDir()
	}
	profilePath := filepath.Join(dir, "astrovox-heap-*.pprof")
	tmp, err := os.CreateTemp(dir, "astrovox-heap-*.pprof")
	if err != nil {
		return nil, err
	}
	profilePath = tmp.Name()
	tmp.Close()
	defer func() {
		_ = os.Remove(profilePath)
	}()

	collector := Collector{HeapPath: profilePath}
	if err := collector.Collect(fn); err != nil {
		return nil, err
	}
	sites, err := TopAllocators(profilePath, topN)
	if err != nil {
		return nil, err
	}
	sort.Slice(sites, func(i, j int) bool { return sites[i].Bytes > sites[j].Bytes })

	var total int64
	for _, s := range sites {
		total += s.Bytes
	}
	return &ReductionReport{
		Sites:       sites,
		TotalBytes:  total,
		ProfilePath: profilePath,
	}, nil
}

// Hotspots returns the sites whose share of total reported
// allocations exceeds threshold (a fraction, e.g. 0.1 = 10%).
func (r *ReductionReport) Hotspots(threshold float64) []AllocSite {
	if r == nil || r.TotalBytes <= 0 {
		return nil
	}
	var hotspots []AllocSite
	for _, s := range r.Sites {
		if float64(s.Bytes)/float64(r.TotalBytes) > threshold {
			hotspots = append(hotspots, s)
		}
	}
	return hotspots
}

// SuggestReduction reports whether the workload allocates more
// than maxBytesPerOp per invocation of fn.
func SuggestReduction(report *ReductionReport, calls int, maxBytesPerOp int64) string {
	if report == nil || calls <= 0 {
		return ""
	}
	perOp := report.TotalBytes / int64(calls)
	if perOp <= maxBytesPerOp {
		return ""
	}
	return fmt.Sprintf("allocates %d B/op (limit %d B/op); reduce allocations in top sites", perOp, maxBytesPerOp)
}
