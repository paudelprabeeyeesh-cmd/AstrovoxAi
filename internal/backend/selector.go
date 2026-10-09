package backend

import (
	"sync"
)

// BackendType identifies a backend implementation.
type BackendType int

const (
	BackendTypeCPU BackendType = iota
	BackendTypeCUDA
	BackendTypeVulkan
	BackendTypeMetal
	BackendTypeDirectML
	BackendTypeROCm
)

func (bt BackendType) String() string {
	switch bt {
	case BackendTypeCPU:
		return "cpu"
	case BackendTypeCUDA:
		return "cuda"
	case BackendTypeVulkan:
		return "vulkan"
	case BackendTypeMetal:
		return "metal"
	case BackendTypeDirectML:
		return "directml"
	case BackendTypeROCm:
		return "rocm"
	default:
		return "unknown"
	}
}

// BackendSelector selects the best available backend.
type BackendSelector struct {
	mu       sync.RWMutex
	preferred BackendType
	fallback  Backend
	candidates []Backend
}

// NewBackendSelector creates a backend selector.
func NewBackendSelector(preferred BackendType, fallback Backend) *BackendSelector {
	return &BackendSelector{
		preferred: preferred,
		fallback:  fallback,
	}
}

// Register registers a candidate backend.
func (bs *BackendSelector) Register(b Backend) {
	bs.mu.Lock()
	defer bs.mu.Unlock()
	bs.candidates = append(bs.candidates, b)
}

// Select selects the best available backend.
// Falls back to CPU if preferred backend is unavailable.
func (bs *BackendSelector) Select() Backend {
	bs.mu.RLock()
	defer bs.mu.RUnlock()
	
	// Try preferred backend first
	for _, b := range bs.candidates {
		if b.Name() == bs.preferred.String() {
			if avail, ok := b.(interface{ Available() bool }); ok {
				if avail.Available() {
					return b
				}
			} else {
				return b
			}
		}
	}
	
	// Try any GPU backend
	for _, b := range bs.candidates {
		if b.Name() != "cpu" {
			if avail, ok := b.(interface{ Available() bool }); ok {
				if avail.Available() {
					return b
				}
			}
		}
	}
	
	// Fallback to CPU
	if bs.fallback != nil {
		return bs.fallback
	}
	
	return nil
}

// AvailableBackends returns names of all registered backends.
func (bs *BackendSelector) AvailableBackends() []string {
	bs.mu.RLock()
	defer bs.mu.RUnlock()
	names := make([]string, len(bs.candidates))
	for i, b := range bs.candidates {
		names[i] = b.Name()
	}
	return names
}

// InitDefaultBackends initializes all available backends and registers them.
func InitDefaultBackends() (*BackendSelector, error) {
	// Create CPU fallback
	cpu := NewCPUBackend()
	selector := NewBackendSelector(BackendTypeCUDA, cpu)
	
	// Register CPU
	selector.Register(cpu)
	
	// Try to create GPU backends (will be simulated)
	if cuda, err := NewCUDA(0, 4096); err == nil {
		selector.Register(cuda)
	}
	if vulkan, err := NewVulkan(VulkanDeviceTypeDiscreteGPU, 4096); err == nil {
		selector.Register(vulkan)
	}
	if metal, err := NewMetal(8192); err == nil {
		selector.Register(metal)
	}
	if dml, err := NewDirectML(0); err == nil {
		selector.Register(dml)
	}
	
	return selector, nil
}