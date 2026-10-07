package kernel

import (
	"fmt"
)

// Dispatcher selects and invokes a kernel.
type Dispatcher struct {
	registry *Registry
	selector *Selector
}

// NewDispatcher creates a new dispatcher.
func NewDispatcher(reg *Registry) *Dispatcher {
	return &Dispatcher{
		registry: reg,
		selector: NewSelector(reg),
	}
}

// Dispatch invokes the best matching kernel.
func (d *Dispatcher) Dispatch(name string, version string, backend string, args ...interface{}) (interface{}, error) {
	entries := d.registry.Lookup(name)
	if len(entries) == 0 {
		return nil, fmt.Errorf("kernel %s not found", name)
	}

	entry := d.selector.Select(entries, version, backend)
	if entry == nil {
		return nil, fmt.Errorf("no suitable kernel found for %s@%s on %s", name, version, backend)
	}

	return entry.Impl, nil
}
