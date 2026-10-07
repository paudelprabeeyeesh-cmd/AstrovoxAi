// Package kernels implements the Astrovox kernel
// library: a typed registry of executable kernels,
// CPU implementations over the tensor package,
// GPU backend stubs, and a capability-aware
// dispatcher.
package kernels

import (
	"sync"

	"github.com/astrovox/astrovox/internal/backend"
	"github.com/astrovox/astrovox/internal/errors"
)

// Kernel is an executable operation bound to
// a device class.
type Kernel interface {
	// Name returns the kernel identifier.
	Name() string
	// Device returns the target device class.
	Device() backend.Device
	// Execute runs the kernel over the given
	// input and output tensors.
	Execute(inputs, outputs []TensorView, attrs map[string]any) error
}

// TensorView is the minimal tensor surface the
// kernel API requires: dtype, shape, and the
// raw backing slice for the kernel's dtype.
type TensorView interface {
	DType() string
	Shape() []int
	Data() any
}

// registry is the global kernel registry.
type registry struct {
	mu       sync.RWMutex
	byKey    map[string]Kernel
	byDevice map[backend.Device]map[string]Kernel
}

var globalRegistry = &registry{
	byKey:    map[string]Kernel{},
	byDevice: map[backend.Device]map[string]Kernel{},
}

// Register adds a kernel to the global registry.
// Registering the same name+device twice replaces
// the previous kernel.
func Register(k Kernel) error {
	if k == nil {
		return errors.New(errors.CodeInvalidArgument, "nil kernel")
	}
	key := k.Device().String() + ":" + k.Name()
	globalRegistry.mu.Lock()
	defer globalRegistry.mu.Unlock()
	globalRegistry.byKey[key] = k
	if globalRegistry.byDevice[k.Device()] == nil {
		globalRegistry.byDevice[k.Device()] = map[string]Kernel{}
	}
	globalRegistry.byDevice[k.Device()][k.Name()] = k
	return nil
}

// MustRegister panics on registration failure.
func MustRegister(k Kernel) {
	if err := Register(k); err != nil {
		panic(err)
	}
}

// Lookup returns the kernel registered for the
// given device class and name.
func Lookup(dev backend.Device, name string) (Kernel, error) {
	globalRegistry.mu.RLock()
	defer globalRegistry.mu.RUnlock()
	if m, ok := globalRegistry.byDevice[dev]; ok {
		if k, ok := m[name]; ok {
			return k, nil
		}
	}
	return nil, errors.New(errors.CodeNotFound, "kernel not found").
		WithField("device", dev.String()).WithField("name", name)
}

// LookupAny returns the kernel with the given
// name, preferring the requested device class
// and falling back to any registered device.
func LookupAny(prefer backend.Device, name string) (Kernel, error) {
	if k, err := Lookup(prefer, name); err == nil {
		return k, nil
	}
	globalRegistry.mu.RLock()
	defer globalRegistry.mu.RUnlock()
	for _, m := range globalRegistry.byDevice {
		if k, ok := m[name]; ok {
			return k, nil
		}
	}
	return nil, errors.New(errors.CodeNotFound, "kernel not found").
		WithField("name", name)
}

// List returns all registered kernels.
func List() []Kernel {
	globalRegistry.mu.RLock()
	defer globalRegistry.mu.RUnlock()
	out := make([]Kernel, 0, len(globalRegistry.byKey))
	for _, k := range globalRegistry.byKey {
		out = append(out, k)
	}
	return out
}

// ListForDevice returns all kernels targeting
// the given device class.
func ListForDevice(dev backend.Device) []Kernel {
	globalRegistry.mu.RLock()
	defer globalRegistry.mu.RUnlock()
	m := globalRegistry.byDevice[dev]
	out := make([]Kernel, 0, len(m))
	for _, k := range m {
		out = append(out, k)
	}
	return out
}
