package kernel

import (
	"fmt"
	"sync"
)

// Registry stores kernel implementations.
type Registry struct {
	kernels map[string][]*Entry
	mu      sync.RWMutex
}

// Entry holds a kernel implementation and metadata.
type Entry struct {
	Descriptor *Descriptor
	Impl       interface{}
}

// NewRegistry creates a new kernel registry.
func NewRegistry() *Registry {
	return &Registry{kernels: make(map[string][]*Entry)}
}

// Register adds a kernel.
func (r *Registry) Register(desc *Descriptor, impl interface{}) error {
	if err := desc.Validate(); err != nil {
		return err
	}
	r.mu.Lock()
	defer r.mu.Unlock()
	key := desc.Name
	for _, e := range r.kernels[key] {
		if e.Descriptor.Version == desc.Version {
			return fmt.Errorf("kernel %s@%s already registered", desc.Name, desc.Version)
		}
	}
	r.kernels[key] = append(r.kernels[key], &Entry{Descriptor: desc, Impl: impl})
	return nil
}

// Lookup returns kernels by name.
func (r *Registry) Lookup(name string) []*Entry {
	r.mu.RLock()
	defer r.mu.RUnlock()
	return append([]*Entry(nil), r.kernels[name]...)
}

// List returns all registered kernel names.
func (r *Registry) List() []string {
	r.mu.RLock()
	defer r.mu.RUnlock()
	names := make([]string, 0, len(r.kernels))
	for name := range r.kernels {
		names = append(names, name)
	}
	return names
}
