package kernel

import (
	"fmt"
	"strconv"
	"strings"
	"sync"
)

// AutoTuner adjusts kernel parameters based on performance data.
type AutoTuner struct {
	configs   map[string]map[string]map[string]int
	latencies map[string]map[string]int
	best      map[string]string
	mu        sync.RWMutex
}

// NewAutoTuner creates a new auto-tuner.
func NewAutoTuner() *AutoTuner {
	return &AutoTuner{
		configs:   make(map[string]map[string]map[string]int),
		latencies: make(map[string]map[string]int),
		best:      make(map[string]string),
	}
}

// Record records a kernel execution result.
func (a *AutoTuner) Record(kernel string, config map[string]int, latencyMs int) {
	a.mu.Lock()
	defer a.mu.Unlock()
	if a.configs[kernel] == nil {
		a.configs[kernel] = make(map[string]map[string]int)
	}
	if a.latencies[kernel] == nil {
		a.latencies[kernel] = make(map[string]int)
	}
	key := encodeConfig(config)
	a.configs[kernel][key] = config
	a.latencies[kernel][key] = latencyMs
	if cur, ok := a.best[kernel]; !ok || latencyMs < a.latencies[kernel][cur] {
		a.best[kernel] = key
	}
}

// BestConfig returns the best known configuration for a kernel.
func (a *AutoTuner) BestConfig(kernel string) (map[string]int, bool) {
	a.mu.RLock()
	defer a.mu.RUnlock()
	key, ok := a.best[kernel]
	if !ok {
		return nil, false
	}
	return a.configs[kernel][key], true
}

// Suggest returns a suggested configuration for a kernel.
func (a *AutoTuner) Suggest(kernel string) map[string]int {
	a.mu.RLock()
	defer a.mu.RUnlock()
	if key, ok := a.best[kernel]; ok {
		if cfg, ok := a.configs[kernel][key]; ok {
			return cfg
		}
	}
	return map[string]int{"tile": 32}
}

func encodeConfig(m map[string]int) string {
	var parts []string
	for k, v := range m {
		parts = append(parts, fmt.Sprintf("%s=%d", k, v))
	}
	return strings.Join(parts, ",")
}
