package backend

import (
	"errors"
	"sync"
)

// Backend defines the interface for execution backends.
type Backend interface {
	// Name returns the backend identifier.
	Name() string
	// SupportedDtypes returns the data types this backend supports.
	SupportedDtypes() []string
	// MatMul performs matrix multiplication.
	MatMul(a, b []float64, m, n, k int) ([]float64, error)
	// Add performs element-wise addition.
	Add(a, b []float64) ([]float64, error)
	// Relu applies the ReLU activation.
	Relu(x []float64) []float64
	// Softmax applies the softmax function.
	Softmax(x []float64, dim int) ([]float64, error)
}

// Device represents an execution device.
type Device int

const (
	DeviceCPU Device = iota
	DeviceCUDA
	DeviceROCm
	DeviceMetal
	DeviceOpenCL
)

func (d Device) String() string {
	switch d {
	case DeviceCPU:
		return "cpu"
	case DeviceCUDA:
		return "cuda"
	case DeviceROCm:
		return "rocm"
	case DeviceMetal:
		return "metal"
	case DeviceOpenCL:
		return "opencl"
	default:
		return "unknown"
	}
}

// Capabilities describes backend capabilities.
type Capabilities struct {
	Devices      []Device
	Dtypes       []string
	MaxMemory    int64
	ThreadCount  int
	HasVectorize bool
	HasStreams   bool
}

// Stream represents an execution stream on a backend.
type Stream interface {
	ID() int
	Device() Device
	Synchronize() error
}

// Event represents a backend event for synchronization.
type Event interface {
	Record(stream Stream) error
	Wait(stream Stream) error
	Synchronize() error
}

// BackendRegistry manages available backends.
type BackendRegistry struct {
	mu       sync.RWMutex
	backends map[string]Backend
	default_ string
}

var globalRegistry = &BackendRegistry{
	backends: make(map[string]Backend),
}

// RegisterBackend adds a backend to the global registry.
func RegisterBackend(name string, b Backend) {
	globalRegistry.mu.Lock()
	defer globalRegistry.mu.Unlock()
	globalRegistry.backends[name] = b
	if globalRegistry.default_ == "" {
		globalRegistry.default_ = name
	}
}

// GetBackend returns a backend by name.
func GetBackend(name string) (Backend, bool) {
	globalRegistry.mu.RLock()
	defer globalRegistry.mu.RUnlock()
	b, ok := globalRegistry.backends[name]
	return b, ok
}

// DefaultBackend returns the default backend.
func DefaultBackend() Backend {
	globalRegistry.mu.RLock()
	defer globalRegistry.mu.RUnlock()
	return globalRegistry.backends[globalRegistry.default_]
}

// ListBackends returns all registered backend names.
func ListBackends() []string {
	globalRegistry.mu.RLock()
	defer globalRegistry.mu.RUnlock()
	names := make([]string, 0, len(globalRegistry.backends))
	for name := range globalRegistry.backends {
		names = append(names, name)
	}
	return names
}

// CPUThreadPool manages a pool of CPU worker threads.
type CPUThreadPool struct {
	workers int
	tasks   chan func()
	wg      sync.WaitGroup
	once    sync.Once
}

// NewCPUThreadPool creates a new thread pool.
func NewCPUThreadPool(workers int) *CPUThreadPool {
	if workers <= 0 {
		workers = 1
	}
	p := &CPUThreadPool{
		workers: workers,
		tasks:   make(chan func(), workers*4),
	}
	p.wg.Add(workers)
	for i := 0; i < workers; i++ {
		go p.worker()
	}
	return p
}

// Submit submits a task to the pool.
func (p *CPUThreadPool) Submit(task func()) {
	p.tasks <- task
}

// Wait waits for all submitted tasks to complete.
func (p *CPUThreadPool) Wait() {
	p.wg.Wait()
}

func (p *CPUThreadPool) worker() {
	defer p.wg.Done()
	for task := range p.tasks {
		task()
	}
}

// Shutdown stops the thread pool.
func (p *CPUThreadPool) Shutdown() {
	p.once.Do(func() {
		close(p.tasks)
	})
}

// VecAdd performs vectorized addition using the thread pool.
func VecAdd(a, b []float64, pool *CPUThreadPool) ([]float64, error) {
	if len(a) != len(b) {
		return nil, errors.New("shape mismatch")
	}
	out := make([]float64, len(a))
	workers := 1
	if pool != nil {
		workers = pool.workers
	}
	chunk := len(a) / workers
	if chunk == 0 {
		chunk = len(a)
	}
	var wg sync.WaitGroup
	for w := 0; w < workers; w++ {
		start := w * chunk
		end := start + chunk
		if w == workers-1 {
			end = len(a)
		}
		if start >= end {
			continue
		}
		wg.Add(1)
		go func(s, e int) {
			defer wg.Done()
			for i := s; i < e; i++ {
				out[i] = a[i] + b[i]
			}
		}(start, end)
	}
	wg.Wait()
	return out, nil
}

// VecMatMul performs vectorized matrix multiplication using the thread pool.
func VecMatMul(a, b []float64, m, n, k int, pool *CPUThreadPool) ([]float64, error) {
	if len(a) != m*k || len(b) != n*k {
		return nil, errors.New("invalid matrix dimensions")
	}
	out := make([]float64, m*n)
	workers := 1
	if pool != nil {
		workers = pool.workers
	}
	chunk := m / workers
	if chunk == 0 {
		chunk = m
	}
	var wg sync.WaitGroup
	for w := 0; w < workers; w++ {
		start := w * chunk
		end := start + chunk
		if w == workers-1 {
			end = m
		}
		if start >= end {
			continue
		}
		wg.Add(1)
		go func(rowStart, rowEnd int) {
			defer wg.Done()
			for i := rowStart; i < rowEnd; i++ {
				for j := 0; j < n; j++ {
					sum := 0.0
					for l := 0; l < k; l++ {
						sum += a[i*k+l] * b[l*n+j]
					}
					out[i*n+j] = sum
				}
			}
		}(start, end)
	}
	wg.Wait()
	return out, nil
}

// RowMajorLayout represents row-major memory layout.
const RowMajorLayout = "row_major"

// ColumnMajorLayout represents column-major memory layout.
const ColumnMajorLayout = "column_major"

// MemoryLayout describes tensor memory layout.
type MemoryLayout struct {
	Layout string
	Strides []int
	Offset  int
}

// NewRowMajor creates a row-major layout.
func NewRowMajor(shape []int) MemoryLayout {
	strides := make([]int, len(shape))
	if len(shape) > 0 {
		strides[len(shape)-1] = 1
		for i := len(shape) - 2; i >= 0; i-- {
			strides[i] = strides[i+1] * shape[i+1]
		}
	}
	return MemoryLayout{Layout: RowMajorLayout, Strides: strides, Offset: 0}
}

// NewColumnMajor creates a column-major layout.
func NewColumnMajor(shape []int) MemoryLayout {
	strides := make([]int, len(shape))
	if len(shape) > 0 {
		strides[0] = 1
		for i := 1; i < len(shape); i++ {
			strides[i] = strides[i-1] * shape[i-1]
		}
	}
	return MemoryLayout{Layout: ColumnMajorLayout, Strides: strides, Offset: 0}
}

// SchedulerBackend bridges Backend and runtime.Scheduler.
type SchedulerBackend struct {
	backend Backend
	pool    *CPUThreadPool
}

// NewSchedulerBackend creates a backend with scheduler integration.
func NewSchedulerBackend(b Backend, workers int) *SchedulerBackend {
	return &SchedulerBackend{
		backend: b,
		pool:    NewCPUThreadPool(workers),
	}
}

// MatMulAsync performs async matrix multiplication.
func (s *SchedulerBackend) MatMulAsync(a, b []float64, m, n, k int) ([]float64, error) {
	return VecMatMul(a, b, m, n, k, s.pool)
}

// AddAsync performs async addition.
func (s *SchedulerBackend) AddAsync(a, b []float64) ([]float64, error) {
	return VecAdd(a, b, s.pool)
}

// Close shuts down the thread pool.
func (s *SchedulerBackend) Close() {
	s.pool.Shutdown()
}
