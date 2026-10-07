package benchmark

import (
	"fmt"
	"os"
	"os/exec"
	"runtime/pprof"
	"strconv"
	"strings"
)

// Collector captures CPU and memory profiles around a workload.
type Collector struct {
	// CPUPath receives a CPU profile when non-empty.
	CPUPath string
	// HeapPath receives a heap profile when non-empty.
	HeapPath string
	// BlockPath receives a block profile when non-empty.
	BlockPath string
	// MutexPath receives a mutex profile when non-empty.
	MutexPath string
}

// Collect runs fn with profiling enabled and writes the
// requested profiles to disk.
func (c *Collector) Collect(fn func()) error {
	if fn == nil {
		return fmt.Errorf("nil workload")
	}
	if c.CPUPath != "" {
		f, err := os.Create(c.CPUPath)
		if err != nil {
			return err
		}
		if err := pprof.StartCPUProfile(f); err != nil {
			f.Close()
			return err
		}
		defer func() {
			pprof.StopCPUProfile()
			f.Close()
		}()
	}
	if c.BlockPath != "" {
		defer writeProfile(c.BlockPath, pprof.Lookup("block"))
	}
	if c.MutexPath != "" {
		defer writeProfile(c.MutexPath, pprof.Lookup("mutex"))
	}
	if c.HeapPath != "" {
		defer writeHeapProfile(c.HeapPath)
	}
	fn()
	return nil
}

func writeProfile(path string, p *pprof.Profile) {
	if p == nil {
		return
	}
	f, err := os.Create(path)
	if err != nil {
		return
	}
	defer f.Close()
	_ = p.WriteTo(f, 0)
}

func writeHeapProfile(path string) {
	f, err := os.Create(path)
	if err != nil {
		return
	}
	defer f.Close()
	_ = pprof.WriteHeapProfile(f)
}

// AllocSite is one allocation site from a heap profile.
type AllocSite struct {
	Function string `json:"function"`
	Bytes    int64  `json:"bytes"`
}

// TopAllocators runs `go tool pprof -top` on a heap profile
// and returns the top n allocation sites by allocated space.
func TopAllocators(profilePath string, n int) ([]AllocSite, error) {
	if n <= 0 {
		n = 10
	}
	cmd := exec.Command("go", "tool", "pprof",
		"-top", "-nodecount="+strconv.Itoa(n),
		"-sample_index=alloc_space", profilePath)
	out, err := cmd.CombinedOutput()
	if err != nil {
		return nil, fmt.Errorf("go tool pprof failed: %w\n%s", err, out)
	}
	return parsePprofTop(string(out))
}

// parsePprofTop parses the table of `go tool pprof -top`.
// Columns: flat flat% sum% cum cum% function...
func parsePprofTop(out string) ([]AllocSite, error) {
	var sites []AllocSite
	inTable := false
	for _, line := range strings.Split(out, "\n") {
		fields := strings.Fields(line)
		if len(fields) == 0 {
			continue
		}
		if !inTable {
			if len(fields) >= 2 && fields[0] == "flat" && fields[1] == "flat%" {
				inTable = true
			}
			continue
		}
		if len(fields) < 6 {
			break
		}
		bytes, err := parseSize(fields[0])
		if err != nil {
			continue
		}
		sites = append(sites, AllocSite{
			Function: strings.Join(fields[5:], " "),
			Bytes:    bytes,
		})
	}
	if len(sites) == 0 {
		return nil, fmt.Errorf("no allocation sites parsed from pprof output")
	}
	return sites, nil
}

// parseSize converts a pprof size string (e.g. "100MB", "1.5GB",
// "2048B", "5635.38kB", "0") to bytes. Suffixes are matched
// case-insensitively.
func parseSize(s string) (int64, error) {
	if s == "" {
		return 0, fmt.Errorf("empty size")
	}
	multiplier := float64(1)
	num := s
	for _, sf := range []struct {
		suffix string
		mult   float64
	}{
		{"tb", 1 << 40},
		{"gb", 1 << 30},
		{"mb", 1 << 20},
		{"kb", 1 << 10},
		{"b", 1},
	} {
		if len(s) >= len(sf.suffix) && strings.EqualFold(s[len(s)-len(sf.suffix):], sf.suffix) {
			multiplier = sf.mult
			num = s[:len(s)-len(sf.suffix)]
			break
		}
	}
	v, err := strconv.ParseFloat(num, 64)
	if err != nil {
		return 0, err
	}
	return int64(v * multiplier), nil
}
