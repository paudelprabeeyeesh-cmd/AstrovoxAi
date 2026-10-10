package backend

import (
	"errors"
	"fmt"
	"sync"
	"sync/atomic"
)

// ROCm and OpenCL backend errors.
var (
	ErrROCmNoDevice     = errors.New("rocm device not available")
	ErrOpenCLNoPlatform = errors.New("opencl platform not available")
	ErrOpenCLContext    = errors.New("opencl context error")
)

// ROCmBackend implements a simulated AMD ROCm/HIP backend.
type ROCmBackend struct {
	deviceID   int
	deviceName string
	gcnArch    string // e.g. "gfx90a"
	available  bool
	mu         sync.RWMutex
	stats      ROCmStats
}

// ROCmStats tracks ROCm statistics.
type ROCmStats struct {
	MatMulOps      atomic.Int64
	AddOps         atomic.Int64
	ReluOps        atomic.Int64
	SoftmaxOps     atomic.Int64
	KernelLaunches atomic.Int64
}

// NewROCmBackend creates a ROCm backend.
func NewROCmBackend(deviceID int) (*ROCmBackend, error) {
	if deviceID < 0 {
		return nil, ErrROCmNoDevice
	}
	return &ROCmBackend{
		deviceID:   deviceID,
		deviceName: fmt.Sprintf("AMD Instinct MI250 (Simulated) %d", deviceID),
		gcnArch:    "gfx90a",
		available:  false,
	}, nil
}

// Name returns the backend name.
func (r *ROCmBackend) Name() string { return "rocm" }

// SupportedDtypes returns supported dtypes.
func (r *ROCmBackend) SupportedDtypes() []string {
	return []string{"float64", "float32", "float16", "int64", "int32", "int8"}
}

// Available reports whether a device is present.
func (r *ROCmBackend) Available() bool { return r.available }

// GCNArch returns the device architecture.
func (r *ROCmBackend) GCNArch() string { return r.gcnArch }

// MatMul performs matrix multiplication (simulated).
func (r *ROCmBackend) MatMul(a, b []float64, m, n, k int) ([]float64, error) {
	if len(a) != m*k || len(b) != k*n {
		return nil, errors.New("invalid dimensions")
	}
	r.stats.MatMulOps.Add(1)
	r.stats.KernelLaunches.Add(1)
	out := make([]float64, m*n)
	for i := 0; i < m; i++ {
		for j := 0; j < n; j++ {
			sum := 0.0
			for l := 0; l < k; l++ {
				sum += a[i*k+l] * b[l*n+j]
			}
			out[i*n+j] = sum
		}
	}
	return out, nil
}

// Add performs element-wise addition.
func (r *ROCmBackend) Add(a, b []float64) ([]float64, error) {
	if len(a) != len(b) {
		return nil, errors.New("shape mismatch")
	}
	r.stats.AddOps.Add(1)
	out := make([]float64, len(a))
	for i := range a {
		out[i] = a[i] + b[i]
	}
	return out, nil
}

// Relu applies ReLU.
func (r *ROCmBackend) Relu(x []float64) []float64 {
	r.stats.ReluOps.Add(1)
	for i := range x {
		if x[i] < 0 {
			x[i] = 0
		}
	}
	return x
}

// Softmax applies the softmax function.
func (r *ROCmBackend) Softmax(x []float64, dim int) ([]float64, error) {
	r.stats.SoftmaxOps.Add(1)
	return softmaxValues(x, dim)
}

// Stats returns ROCm statistics.
func (r *ROCmBackend) Stats() *ROCmStats { return &r.stats }

// Capabilities returns ROCm capabilities.
func (r *ROCmBackend) Capabilities() Capabilities {
	return Capabilities{
		Devices:      []Device{DeviceROCm},
		Dtypes:       r.SupportedDtypes(),
		MaxMemory:    64 * 1024 * 1024 * 1024,
		ThreadCount:  110,
		HasVectorize: true,
		HasStreams:   true,
	}
}

// OpenCLDeviceType identifies an OpenCL device kind.
type OpenCLDeviceType uint32

// OpenCL device types.
const (
	OpenCLDeviceTypeDefault     OpenCLDeviceType = 1 << 0
	OpenCLDeviceTypeCPU         OpenCLDeviceType = 1 << 1
	OpenCLDeviceTypeGPU         OpenCLDeviceType = 1 << 2
	OpenCLDeviceTypeAccelerator OpenCLDeviceType = 1 << 3
)

func (t OpenCLDeviceType) String() string {
	switch {
	case t&OpenCLDeviceTypeCPU != 0:
		return "cpu"
	case t&OpenCLDeviceTypeGPU != 0:
		return "gpu"
	case t&OpenCLDeviceTypeAccelerator != 0:
		return "accelerator"
	default:
		return "default"
	}
}

// OpenCLDevice describes an OpenCL device.
type OpenCLDevice struct {
	id         uint64
	Name       string
	Type       OpenCLDeviceType
	VendorID   uint32
	MaxUnits   uint32
	MaxFreqMHz uint32
	// OpenCL 2.x+ SVM capabilities (subset).
	SVMCoarseGrain bool
	SVMFineGrain   bool
}

// Score is a simple device-selection heuristic (more units * freq is better).
func (d OpenCLDevice) Score() uint64 {
	return uint64(d.MaxUnits) * uint64(d.MaxFreqMHz)
}

// OpenCLPlatform groups devices.
type OpenCLPlatform struct {
	id      uint64
	Name    string
	Vendor  string
	Version string
	Devices []OpenCLDevice
}

// OpenCLBackend implements a simulated OpenCL backend.
type OpenCLBackend struct {
	platform  OpenCLPlatform
	deviceIdx int
	available bool
	mu        sync.RWMutex
	stats     OpenCLStats
}

// OpenCLStats tracks OpenCL statistics.
type OpenCLStats struct {
	MatMulOps    atomic.Int64
	AddOps       atomic.Int64
	ReluOps      atomic.Int64
	SoftmaxOps   atomic.Int64
	KernelBuilds atomic.Int64
}

// NewOpenCLBackend creates an OpenCL backend.
func NewOpenCLBackend(platform OpenCLPlatform, deviceIdx int) (*OpenCLBackend, error) {
	if len(platform.Devices) == 0 {
		return nil, ErrOpenCLNoPlatform
	}
	if deviceIdx < 0 || deviceIdx >= len(platform.Devices) {
		return nil, ErrOpenCLContext
	}
	return &OpenCLBackend{
		platform:  platform,
		deviceIdx: deviceIdx,
		available: false,
	}, nil
}

// DefaultOpenCLPlatform returns a representative platform.
func DefaultOpenCLPlatform() OpenCLPlatform {
	return OpenCLPlatform{
		Name:    "OpenCL 3.0 (Simulated)",
		Vendor:  "astrovox",
		Version: "OpenCL 3.0 Unified",
		Devices: []OpenCLDevice{
			{id: 1, Name: "Sim GPU", Type: OpenCLDeviceTypeGPU, VendorID: 0x10DE, MaxUnits: 80, MaxFreqMHz: 1800, SVMCoarseGrain: true},
			{id: 2, Name: "Sim CPU", Type: OpenCLDeviceTypeCPU, VendorID: 0x8086, MaxUnits: 16, MaxFreqMHz: 3200},
		},
	}
}

// Name returns the backend name.
func (b *OpenCLBackend) Name() string { return "opencl" }

// SupportedDtypes returns supported dtypes.
func (b *OpenCLBackend) SupportedDtypes() []string {
	return []string{"float64", "float32", "int64", "int32", "int16", "int8", "uint8"}
}

// Available reports whether a device is present.
func (b *OpenCLBackend) Available() bool { return b.available }

// Device returns the selected device.
func (b *OpenCLBackend) Device() OpenCLDevice {
	b.mu.RLock()
	defer b.mu.RUnlock()
	return b.platform.Devices[b.deviceIdx]
}

// BestDevice returns the highest-scoring device on the platform.
func (b *OpenCLBackend) BestDevice() OpenCLDevice {
	b.mu.RLock()
	defer b.mu.RUnlock()
	best := b.platform.Devices[0]
	for _, d := range b.platform.Devices[1:] {
		if d.Score() > best.Score() {
			best = d
		}
	}
	return best
}

// MatMul performs matrix multiplication (simulated).
func (b *OpenCLBackend) MatMul(a, c []float64, m, n, k int) ([]float64, error) {
	if len(a) != m*k || len(c) != k*n {
		return nil, errors.New("invalid dimensions")
	}
	b.stats.MatMulOps.Add(1)
	b.stats.KernelBuilds.Add(1)
	out := make([]float64, m*n)
	for i := 0; i < m; i++ {
		for j := 0; j < n; j++ {
			sum := 0.0
			for l := 0; l < k; l++ {
				sum += a[i*k+l] * c[l*n+j]
			}
			out[i*n+j] = sum
		}
	}
	return out, nil
}

// Add performs element-wise addition.
func (b *OpenCLBackend) Add(a, c []float64) ([]float64, error) {
	if len(a) != len(c) {
		return nil, errors.New("shape mismatch")
	}
	b.stats.AddOps.Add(1)
	out := make([]float64, len(a))
	for i := range a {
		out[i] = a[i] + c[i]
	}
	return out, nil
}

// Relu applies ReLU.
func (b *OpenCLBackend) Relu(x []float64) []float64 {
	b.stats.ReluOps.Add(1)
	for i := range x {
		if x[i] < 0 {
			x[i] = 0
		}
	}
	return x
}

// Softmax applies the softmax function.
func (b *OpenCLBackend) Softmax(x []float64, dim int) ([]float64, error) {
	b.stats.SoftmaxOps.Add(1)
	return softmaxValues(x, dim)
}

// Stats returns OpenCL statistics.
func (b *OpenCLBackend) Stats() *OpenCLStats { return &b.stats }

// Capabilities returns OpenCL capabilities.
func (b *OpenCLBackend) Capabilities() Capabilities {
	return Capabilities{
		Devices:      []Device{DeviceOpenCL},
		Dtypes:       b.SupportedDtypes(),
		MaxMemory:    4 * 1024 * 1024 * 1024,
		ThreadCount:  int(b.Device().MaxUnits),
		HasVectorize: true,
		HasStreams:   true,
	}
}
