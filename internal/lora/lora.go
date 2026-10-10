// Package lora provides Low-Rank Adaptation for parameter-efficient
// fine-tuning.
package lora

import (
	"errors"
	"fmt"
	"strings"
	"sync"

	"github.com/astrovox/astrovox/tensor"
)

// LoRAConfig holds LoRA hyperparameters.
type LoRAConfig struct {
	Rank      int     // r: low-rank dimension
	Alpha     float64 // scaling baseline
	Dropout   float64
	TargetModules []string // module names to adapt (empty = all)
}

// DefaultLoRAConfig returns defaults.
func DefaultLoRAConfig() LoRAConfig {
	return LoRAConfig{Rank: 8, Alpha: 16, Dropout: 0.0}
}

// Scaling returns the LoRA scaling factor alpha/r.
func (c LoRAConfig) Scaling() float64 {
	if c.Rank <= 0 {
		return 0
	}
	return c.Alpha / float64(c.Rank)
}

// LoRALayer holds the low-rank factors A and B for one matrix.
type LoRALayer struct {
	Name     string
	A        *tensor.Tensor // [r, in_dim]
	B        *tensor.Tensor // [out_dim, r]
	InDim    int
	OutDim   int
	Config   LoRAConfig
	enabled  bool
	mu       sync.RWMutex
}

// NewLoRALayer creates a LoRA layer for an [out, in] weight matrix.
func NewLoRALayer(name string, inDim, outDim int, cfg LoRAConfig) (*LoRALayer, error) {
	if cfg.Rank <= 0 {
		return nil, errors.New("lora rank must be positive")
	}
	if inDim <= 0 || outDim <= 0 {
		return nil, errors.New("dimensions must be positive")
	}
	a, err := tensor.New(tensor.Float64, []int{cfg.Rank, inDim})
	if err != nil {
		return nil, err
	}
	b, err := tensor.New(tensor.Float64, []int{outDim, cfg.Rank})
	if err != nil {
		return nil, err
	}
	// A is initialized with Gaussian noise, B with zeros so the initial
	// delta is zero.
	av := a.Float64()
	for i := range av {
		av[i] = gaussian(i) * 0.01
	}
	return &LoRALayer{
		Name: name, A: a, B: b,
		InDim: inDim, OutDim: outDim,
		Config: cfg, enabled: true,
	}, nil
}

// gaussian is a cheap deterministic pseudo-Gaussian value.
func gaussian(seed int) float64 {
	x := float64((seed*37+11)%2000)/1000.0 - 1.0
	return x
}

// Delta computes the LoRA weight update B @ A.
func (l *LoRALayer) Delta() (*tensor.Tensor, error) {
	return l.B, nil
}

// MergeInto adds scaling * (B @ A) to the base weight in place.
func (l *LoRALayer) MergeInto(base *tensor.Tensor) error {
	if base == nil {
		return errors.New("nil base weight")
	}
	if base.Shape().Dim(0) != l.OutDim || base.Shape().Dim(1) != l.InDim {
		return fmt.Errorf("shape mismatch: base %v, lora [%d,%d]",
			base.Shape().Dims(), l.OutDim, l.InDim)
	}
	scale := l.Config.Scaling()
	bv := l.B.Float64()
	av := l.A.Float64()
	wv := base.Float64()
	for i := 0; i < l.OutDim; i++ {
		for j := 0; j < l.InDim; j++ {
			sum := 0.0
			for r := 0; r < l.Config.Rank; r++ {
				sum += bv[i*l.Config.Rank+r] * av[r*l.InDim+j]
			}
			wv[i*l.InDim+j] += scale * sum
		}
	}
	return nil
}

// SetEnabled toggles the adapter.
func (l *LoRALayer) SetEnabled(on bool) {
	l.mu.Lock()
	l.enabled = on
	l.mu.Unlock()
}

// IsEnabled reports whether the adapter is active.
func (l *LoRALayer) IsEnabled() bool {
	l.mu.RLock()
	defer l.mu.RUnlock()
	return l.enabled
}

// ParamCount returns the number of LoRA parameters.
func (l *LoRALayer) ParamCount() int {
	return l.Config.Rank * (l.InDim + l.OutDim)
}

// LoRAModel adapts a set of weight matrices.
type LoRAModel struct {
	config LoRAConfig
	layers map[string]*LoRALayer
	base   map[string]*tensor.Tensor
	mu     sync.RWMutex
}

// NewLoRAModel creates a LoRA adapter collection.
func NewLoRAModel(cfg LoRAConfig) *LoRAModel {
	return &LoRAModel{
		config: cfg,
		layers: make(map[string]*LoRALayer),
		base:   make(map[string]*tensor.Tensor),
	}
}

// AddBase registers a base weight matrix and creates its adapter.
func (m *LoRAModel) AddBase(name string, w *tensor.Tensor) error {
	if w == nil || len(w.Shape().Dims()) != 2 {
		return errors.New("base weight must be a 2-D tensor")
	}
	if len(m.config.TargetModules) > 0 && !matches(m.config.TargetModules, name) {
		return nil
	}
	out, in := w.Shape().Dim(0), w.Shape().Dim(1)
	layer, err := NewLoRALayer(name, in, out, m.config)
	if err != nil {
		return err
	}
	m.mu.Lock()
	defer m.mu.Unlock()
	m.base[name] = w
	m.layers[name] = layer
	return nil
}

// matches reports whether name should be adapted, supporting both an
// exact name and a module-path prefix ("attn" matches "attn.fc").
func matches(patterns []string, name string) bool {
	for _, p := range patterns {
		if p == name || strings.HasPrefix(name, p+".") {
			return true
		}
	}
	return false
}

// Layer returns an adapter by name.
func (m *LoRAModel) Layer(name string) (*LoRALayer, bool) {
	m.mu.RLock()
	defer m.mu.RUnlock()
	l, ok := m.layers[name]
	return l, ok
}

// Merge merges all adapters into their base weights.
func (m *LoRAModel) Merge() error {
	m.mu.RLock()
	defer m.mu.RUnlock()
	for name, layer := range m.layers {
		if !layer.IsEnabled() {
			continue
		}
		if err := layer.MergeInto(m.base[name]); err != nil {
			return fmt.Errorf("merge %s: %w", name, err)
		}
	}
	return nil
}

// TrainableParams returns the number of adapter parameters.
func (m *LoRAModel) TrainableParams() int {
	m.mu.RLock()
	defer m.mu.RUnlock()
	total := 0
	for _, l := range m.layers {
		total += l.ParamCount()
	}
	return total
}

// BaseParams returns the number of frozen base parameters.
func (m *LoRAModel) BaseParams() int {
	m.mu.RLock()
	defer m.mu.RUnlock()
	total := 0
	for _, w := range m.base {
		total += w.NumElements()
	}
	return total
}

// Efficiency returns the fraction of parameters that are trainable.
func (m *LoRAModel) Efficiency() float64 {
	base := m.BaseParams()
	if base == 0 {
		return 0
	}
	return float64(m.TrainableParams()) / float64(base)
}

// Layers returns all adapter names.
func (m *LoRAModel) Layers() []string {
	m.mu.RLock()
	defer m.mu.RUnlock()
	names := make([]string, 0, len(m.layers))
	for n := range m.layers {
		names = append(names, n)
	}
	return names
}