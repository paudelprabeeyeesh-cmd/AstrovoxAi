package backend

import (
	"errors"
	"fmt"
	"sync"
	"sync/atomic"
)

// WebGPU backend errors.
var (
	ErrWebGPUNoDevice    = errors.New("webgpu device not available")
	ErrWebGPUBufferSize  = errors.New("webgpu buffer size mismatch")
	ErrWebGPUPipeline    = errors.New("webgpu pipeline error")
)

// limits mirrors a subset of GPUSupportedLimits.
type webGPULimits struct {
	maxTextureDim1D       uint32
	maxTextureDim2D       uint32
	maxBindGroups         uint32
	maxBufferSize         uint64
	maxStorageBufferBindingSize uint64
	maxComputeWorkgroupSizeX  uint32
	maxComputeWorkgroupSizeY  uint32
	maxComputeWorkgroupSizeZ  uint32
	maxComputeInvocationsPerWorkgroup uint32
}

func defaultWebGPULimits() webGPULimits {
	return webGPULimits{
		maxTextureDim1D:                 8192,
		maxTextureDim2D:                 8192,
		maxBindGroups:                   4,
		maxBufferSize:                   268435456,
		maxStorageBufferBindingSize:     134217728,
		maxComputeWorkgroupSizeX:       256,
		maxComputeWorkgroupSizeY:       256,
		maxComputeWorkgroupSizeZ:        64,
		maxComputeInvocationsPerWorkgroup: 256,
	}
}

// WebGPUAdapter describes a physical adapter.
type WebGPUAdapter struct {
	Name       string
	Vendor     string
	Architecture string
	IsIntegrated bool
	Limits     webGPULimits
	Features   []string
}

// String renders the adapter summary.
func (a WebGPUAdapter) String() string {
	kind := "discrete"
	if a.IsIntegrated {
		kind = "integrated"
	}
	return fmt.Sprintf("%s (%s, %s)", a.Name, a.Vendor, kind)
}

// WebGPUBuffer is a device buffer.
type WebGPUBuffer struct {
	id     uint64
	size   uint64
	usage  uint32 // GPUBufferUsage flags
	label  string
}

// Buffer usage flags (subset of the WebGPU spec).
const (
	WebGPUBufferUsageMapRead     uint32 = 1 << 0
	WebGPUBufferUsageMapWrite    uint32 = 1 << 1
	WebGPUBufferUsageCopySrc     uint32 = 1 << 2
	WebGPUBufferUsageCopyDst     uint32 = 1 << 3
	WebGPUBufferUsageIndex       uint32 = 1 << 4
	WebGPUBufferUsageVertex      uint32 = 1 << 5
	WebGPUBufferUsageUniform     uint32 = 1 << 6
	WebGPUBufferUsageStorage     uint32 = 1 << 7
)

// UsageString renders the usage flags.
func (b WebGPUBuffer) UsageString() string {
	parts := []string{}
	if b.usage&WebGPUBufferUsageStorage != 0 {
		parts = append(parts, "STORAGE")
	}
	if b.usage&WebGPUBufferUsageUniform != 0 {
		parts = append(parts, "UNIFORM")
	}
	if b.usage&WebGPUBufferUsageCopySrc != 0 {
		parts = append(parts, "COPY_SRC")
	}
	if b.usage&WebGPUBufferUsageCopyDst != 0 {
		parts = append(parts, "COPY_DST")
	}
	if len(parts) == 0 {
		return "NONE"
	}
	out := parts[0]
	for _, p := range parts[1:] {
		out += "|" + p
	}
	return out
}

// WebGPUComputePipeline is a compute pipeline.
type WebGPUComputePipeline struct {
	entryPoint string
	workgroupX  uint32
	workgroupY  uint32
	workgroupZ  uint32
	compiled    atomic.Bool
	execCount   atomic.Int64
}

// Compile marks the pipeline ready.
func (p *WebGPUComputePipeline) Compile() error {
	if p.entryPoint == "" {
		return ErrWebGPUPipeline
	}
	p.compiled.Store(true)
	return nil
}

// WebGPU implements the Backend interface over a simulated WebGPU device.
type WebGPU struct {
	adapter   WebGPUAdapter
	available bool
	mu        sync.RWMutex
	buffers   map[uint64]*WebGPUBuffer
	nextID    atomic.Uint64
	pipelines map[string]*WebGPUComputePipeline
	stats     WebGPUStats
}

// WebGPUStats tracks WebGPU statistics.
type WebGPUStats struct {
	MatMulOps  atomic.Int64
	AddOps     atomic.Int64
	ReluOps    atomic.Int64
	SoftmaxOps atomic.Int64
	Allocations atomic.Int64
	Dispatches atomic.Int64
}

// NewWebGPU creates a WebGPU backend bound to an adapter.
func NewWebGPU(adapter WebGPUAdapter) (*WebGPU, error) {
	if adapter.Name == "" {
		return nil, ErrWebGPUNoDevice
	}
	w := &WebGPU{
		adapter:   adapter,
		available: false, // simulated: no real GPU adapter in CI
		buffers:   make(map[uint64]*WebGPUBuffer),
		pipelines: make(map[string]*WebGPUComputePipeline),
	}
	return w, nil
}

// DefaultWebGPUAdapter returns a representative adapter.
func DefaultWebGPUAdapter() WebGPUAdapter {
	return WebGPUAdapter{
		Name:         "WebGPU Device (Simulated)",
		Vendor:       "astrovox",
		Architecture: "webgpu-1",
		IsIntegrated: true,
		Limits:       defaultWebGPULimits(),
		Features:     []string{"compute-shaders", "timestamp-query"},
	}
}

// Name returns the backend name.
func (w *WebGPU) Name() string { return "webgpu" }

// SupportedDtypes returns supported dtypes.
func (w *WebGPU) SupportedDtypes() []string {
	return []string{"float32", "float16", "int32", "uint32"}
}

// Available reports whether a real adapter is present.
func (w *WebGPU) Available() bool { return w.available }

// Adapter returns the bound adapter.
func (w *WebGPU) Adapter() WebGPUAdapter { return w.adapter }

// CreateBuffer allocates a device buffer.
func (w *WebGPU) CreateBuffer(label string, size uint64, usage uint32) (*WebGPUBuffer, error) {
	if size == 0 {
		return nil, errors.New("buffer size must be positive")
	}
	if size > w.adapter.Limits.maxBufferSize {
		return nil, ErrWebGPUBufferSize
	}
	b := &WebGPUBuffer{
		id:    w.nextID.Add(1),
		size:  size,
		usage: usage,
		label: label,
	}
	w.mu.Lock()
	w.buffers[b.id] = b
	w.mu.Unlock()
	w.stats.Allocations.Add(1)
	return b, nil
}

// DestroyBuffer releases a buffer.
func (w *WebGPU) DestroyBuffer(b *WebGPUBuffer) {
	if b == nil {
		return
	}
	w.mu.Lock()
	delete(w.buffers, b.id)
	w.mu.Unlock()
}

// BufferCount returns the number of live buffers.
func (w *WebGPU) BufferCount() int {
	w.mu.RLock()
	defer w.mu.RUnlock()
	return len(w.buffers)
}

// CreatePipeline registers a compute pipeline.
func (w *WebGPU) CreatePipeline(label, entryPoint string, wgX, wgY, wgZ uint32) (*WebGPUComputePipeline, error) {
	l := w.adapter.Limits
	if wgX > l.maxComputeWorkgroupSizeX || wgY > l.maxComputeWorkgroupSizeY || wgZ > l.maxComputeWorkgroupSizeZ {
		return nil, ErrWebGPUPipeline
	}
	if wgX*wgY*wgZ > l.maxComputeInvocationsPerWorkgroup {
		return nil, ErrWebGPUPipeline
	}
	p := &WebGPUComputePipeline{
		entryPoint: entryPoint,
		workgroupX: wgX, workgroupY: wgY, workgroupZ: wgZ,
	}
	if err := p.Compile(); err != nil {
		return nil, err
	}
	w.mu.Lock()
	w.pipelines[label] = p
	w.mu.Unlock()
	return p, nil
}

// Dispatch records a compute dispatch.
func (w *WebGPU) Dispatch(p *WebGPUComputePipeline, groupsX, groupsY, groupsZ uint32) error {
	if p == nil || !p.compiled.Load() {
		return ErrWebGPUPipeline
	}
	p.execCount.Add(1)
	w.stats.Dispatches.Add(1)
	return nil
}

// MatMul performs matrix multiplication (simulated).
func (w *WebGPU) MatMul(a, b []float64, m, n, k int) ([]float64, error) {
	if len(a) != m*k || len(b) != k*n {
		return nil, errors.New("invalid dimensions")
	}
	w.stats.MatMulOps.Add(1)
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
func (w *WebGPU) Add(a, b []float64) ([]float64, error) {
	if len(a) != len(b) {
		return nil, errors.New("shape mismatch")
	}
	w.stats.AddOps.Add(1)
	out := make([]float64, len(a))
	for i := range a {
		out[i] = a[i] + b[i]
	}
	return out, nil
}

// Relu applies ReLU.
func (w *WebGPU) Relu(x []float64) []float64 {
	w.stats.ReluOps.Add(1)
	for i := range x {
		if x[i] < 0 {
			x[i] = 0
		}
	}
	return x
}

// Softmax applies softmax.
func (w *WebGPU) Softmax(x []float64, dim int) ([]float64, error) {
	if len(x) == 0 {
		return nil, errors.New("empty input")
	}
	w.stats.SoftmaxOps.Add(1)
	maxV := x[0]
	for _, v := range x {
		if v > maxV {
			maxV = v
		}
	}
	sum := 0.0
	out := make([]float64, len(x))
	for i, v := range x {
		out[i] = mathExp(v - maxV)
		sum += out[i]
	}
	for i := range out {
		out[i] /= sum
	}
	return out, nil
}

// Stats returns WebGPU statistics.
func (w *WebGPU) Stats() *WebGPUStats { return &w.stats }

// Capabilities returns WebGPU capabilities.
func (w *WebGPU) Capabilities() Capabilities {
	return Capabilities{
		Devices:      []Device{DeviceOpenCL},
		Dtypes:       w.SupportedDtypes(),
		MaxMemory:    int64(w.adapter.Limits.maxBufferSize),
		ThreadCount:  int(w.adapter.Limits.maxComputeInvocationsPerWorkgroup),
		HasVectorize: true,
		HasStreams:   true,
	}
}
