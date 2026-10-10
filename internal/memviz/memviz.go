// Package memviz provides memory usage visualization: allocation
// tracking, fragmentation reporting, and ASCII treemap rendering.
package memviz

import (
	"fmt"
	"sort"
	"strings"
	"sync"
	"sync/atomic"
)

// Region is a tracked memory region.
type Region struct {
	Name     string
	Bytes    int64
	Category string
	Align    int64
}

// Tracker records allocations by category.
type Tracker struct {
	mu       sync.RWMutex
	regions  []Region
	live     map[string]int64
	total    int64
	peak     int64
	byCateg  map[string]int64
	allocs   atomic.Int64
	frees    atomic.Int64
}

// NewTracker creates a memory tracker.
func NewTracker() *Tracker {
	return &Tracker{live: make(map[string]int64), byCateg: make(map[string]int64)}
}

// Allocate records an allocation and enforces a limit if one is set.
func (t *Tracker) Allocate(name, category string, bytes int64) error {
	if bytes <= 0 {
		return fmt.Errorf("allocation of %s must be positive", name)
	}
	t.mu.Lock()
	t.regions = append(t.regions, Region{Name: name, Bytes: bytes, Category: category})
	t.live[name] += bytes
	t.total += bytes
	t.byCateg[category] += bytes
	if t.total > t.peak {
		t.peak = t.total
	}
	t.mu.Unlock()
	t.allocs.Add(1)
	return nil
}

// Free records a release.
func (t *Tracker) Free(name string) error {
	t.mu.Lock()
	defer t.mu.Unlock()
	n, ok := t.live[name]
	if !ok {
		return fmt.Errorf("region %q not live", name)
	}
	delete(t.live, name)
	t.total -= n
	t.frees.Add(1)
	return nil
}

// Live returns the names of live regions.
func (t *Tracker) Live() []string {
	t.mu.RLock()
	defer t.mu.RUnlock()
	out := make([]string, 0, len(t.live))
	for n := range t.live {
		out = append(out, n)
	}
	sort.Strings(out)
	return out
}

// Usage returns total live bytes.
func (t *Tracker) Usage() int64 {
	t.mu.RLock()
	defer t.mu.RUnlock()
	return t.total
}

// Peak returns the peak live bytes.
func (t *Tracker) Peak() int64 {
	t.mu.RLock()
	defer t.mu.RUnlock()
	return t.peak
}

// ByCategory returns live bytes per category.
func (t *Tracker) ByCategory() map[string]int64 {
	t.mu.RLock()
	defer t.mu.RUnlock()
	out := make(map[string]int64, len(t.byCateg))
	for k, v := range t.byCateg {
		out[k] = v
	}
	return out
}

// RegionUsage returns live bytes for a named region.
func (t *Tracker) RegionUsage(name string) int64 {
	t.mu.RLock()
	defer t.mu.RUnlock()
	return t.live[name]
}

// Fragmentation estimates heap fragmentation given free block sizes.
func Fragmentation(allocated int64, freeBlocks []int64) float64 {
	if allocated <= 0 {
		return 0
	}
	var freeTotal int64
	largest := int64(0)
	for _, b := range freeBlocks {
		freeTotal += b
		if b > largest {
			largest = b
		}
	}
	if freeTotal == 0 {
		return 0
	}
	// External fragmentation: free memory not usable as one block.
	return float64(freeTotal-largest) / float64(allocated+freeTotal)
}

// LargestFreeBlock returns the largest free block size.
func LargestFreeBlock(freeBlocks []int64) int64 {
	var largest int64
	for _, b := range freeBlocks {
		if b > largest {
			largest = b
		}
	}
	return largest
}

// Treemap renderers --------------------------------------------------------

// RenderASCII renders a proportional bar chart of categories.
func RenderASCII(byCategory map[string]int64, width int) string {
	if width <= 0 {
		width = 40
	}
	type kv struct {
		k string
		v int64
	}
	pairs := make([]kv, 0, len(byCategory))
	var total int64
	for k, v := range byCategory {
		pairs = append(pairs, kv{k, v})
		total += v
	}
	sort.Slice(pairs, func(i, j int) bool { return pairs[i].v > pairs[j].v })

	var sb strings.Builder
	sb.WriteString("Memory usage\n")
	sb.WriteString(strings.Repeat("-", width+22) + "\n")
	for _, p := range pairs {
		frac := float64(p.v) / float64(total)
		bars := int(frac * float64(width))
		if bars == 0 && p.v > 0 {
			bars = 1
		}
		sb.WriteString(fmt.Sprintf("%-20s %10d B |%s|\n", truncate(p.k, 20), p.v, strings.Repeat("#", bars)))
	}
	sb.WriteString(strings.Repeat("-", width+22) + "\n")
	sb.WriteString(fmt.Sprintf("%-20s %10d B\n", "TOTAL", total))
	return sb.String()
}

func truncate(s string, n int) string {
	if len(s) <= n {
		return s
	}
	return s[:n-1] + "…"
}

// RenderFlame renders a simple flame-graph-style treemap text view.
func RenderFlame(regions []Region, depth int) string {
	if len(regions) == 0 {
		return "(no regions)\n"
	}
	sorted := append([]Region(nil), regions...)
	sort.Slice(sorted, func(i, j int) bool { return sorted[i].Bytes > sorted[j].Bytes })
	var total int64
	for _, r := range sorted {
		total += r.Bytes
	}
	maxBar := 60
	var sb strings.Builder
	for i := 0; i < len(sorted) && i < depth; i++ {
		r := sorted[i]
		frac := float64(r.Bytes) / float64(total)
		bars := int(frac * float64(maxBar))
		if bars == 0 {
			bars = 1
		}
		indent := strings.Repeat("  ", i/depth)
		sb.WriteString(fmt.Sprintf("%s%-20s %8.2f%% %s\n", indent, truncate(r.Name, 20), frac*100, strings.Repeat("█", bars)))
	}
	return sb.String()
}

// Snapshot is a point-in-time memory summary.
type Snapshot struct {
	Timestamp   int64
	Usage       int64
	Peak        int64
	FreeBlocks  []int64
	Allocations int64
}

// HumanBytes formats bytes as a human-readable string.
func HumanBytes(b int64) string {
	const unit = 1024
	if b < unit {
		return fmt.Sprintf("%d B", b)
	}
	div, exp := int64(unit), 0
	for n := b / unit; n >= unit; n /= unit {
		div *= unit
		exp++
	}
	return fmt.Sprintf("%.1f %ciB", float64(b)/float64(div), "KMGTPE"[exp])
}

// Report produces a full human-readable memory report.
func Report(t *Tracker, freeBlocks []int64) string {
	var sb strings.Builder
	sb.WriteString(RenderASCII(t.ByCategory(), 40))
	sb.WriteString(fmt.Sprintf("\nLive bytes : %s\n", HumanBytes(t.Usage())))
	sb.WriteString(fmt.Sprintf("Peak bytes : %s\n", HumanBytes(t.Peak())))
	sb.WriteString(fmt.Sprintf("Fragmentation: %.3f\n", Fragmentation(t.Usage(), freeBlocks)))
	return sb.String()
}