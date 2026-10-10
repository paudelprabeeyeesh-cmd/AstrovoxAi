package backend

import (
	"errors"
	"fmt"
	"math"
	"runtime"
	"sync"
	"sync/atomic"
)

// CUDA backend error definitions.
var (
	ErrCUDANotAvailable = errors.New("cuda not available")
	ErrCUDADevice       = errors.New("cuda device error")
	ErrCUDAMemory       = errors.New("cuda out of memory")
	ErrCUDAStream       = errors.New("cuda stream error")
)

// CUDAMemoryPool manages simulated CUDA memory allocation.
type CUDAMemoryPool struct {
	mu     sync.Mutex
	total  int64
	used   atomic.Int64
	peak   atomic.Int64
	allocs map[uintptr]int64
	nextID atomic.Uintptr
}

// NewCUDAMemoryPool creates a new CUDA memory pool.
func NewCUDAMemoryPool(total int64) *CUDAMemoryPool {
	return &CUDAMemoryPool{
		total:  total,
		allocs: make(map[uintptr]int64),
	}
}

// Allocate allocates memory from the pool.
func (p *CUDAMemoryPool) Allocate(size int64) (uintptr, error) {
	p.mu.Lock()
	defer p.mu.Unlock()

	used := p.used.Load()
	if used+size > p.total {
		return 0, ErrCUDAMemory
	}

	id := p.nextID.Add(1)
	p.allocs[id] = size
	p.used.Add(size)

	// Track peak memory
	for {
		peak := p.peak.Load()
		if p.used.Load() <= peak {
			break
		}
		if p.peak.CompareAndSwap(peak, p.used.Load()) {
			break
		}
	}

	return id, nil
}

// Free frees allocated memory.
func (p *CUDAMemoryPool) Free(id uintptr) {
	p.mu.Lock()
	defer p.mu.Unlock()

	if size, ok := p.allocs[id]; ok {
		p.used.Add(-size)
		delete(p.allocs, id)
	}
}

// Stats returns memory pool statistics.
func (p *CUDAMemoryPool) Stats() (used, peak, total int64) {
	return p.used.Load(), p.peak.Load(), p.total
}

// CUDAStream represents a simulated CUDA stream.
type CUDAStream struct {
	id       int
	deviceID int
	mu       sync.Mutex
	events   []*CUDAEvent
	busy     atomic.Bool
	stats    StreamStats
}

// StreamStats tracks stream statistics.
type StreamStats struct {
	OpsSubmitted atomic.Int64
	OpsCompleted atomic.Int64
	BytesCopied  atomic.Int64
}

// ID returns the stream ID.
func (s *CUDAStream) ID() int {
	return s.id
}

// Device returns the device.
func (s *CUDAStream) Device() Device {
	return DeviceCUDA
}

// Synchronize waits for all operations to complete.
func (s *CUDAStream) Synchronize() error {
	if !s.busy.Load() {
		return nil
	}
	s.mu.Lock()
	defer s.mu.Unlock()
	s.busy.Store(false)
	return nil
}

// IsBusy returns whether the stream is busy.
func (s *CUDAStream) IsBusy() bool {
	return s.busy.Load()
}

// CUDAEvent represents a simulated CUDA event.
type CUDAEvent struct {
	id       int
	recorded atomic.Bool
	mu       sync.Mutex
}

// Record records the event on a stream.
func (e *CUDAEvent) Record(stream Stream) error {
	if s, ok := stream.(*CUDAStream); ok {
		s.mu.Lock()
		s.events = append(s.events, e)
		s.mu.Unlock()
	}
	e.recorded.Store(true)
	return nil
}

// Wait makes a stream wait for this event.
func (e *CUDAEvent) Wait(stream Stream) error {
	return nil
}

// Synchronize waits for the event to complete.
func (e *CUDAEvent) Synchronize() error {
	return nil
}

// IsComplete returns whether the event has completed.
func (e *CUDAEvent) IsComplete() bool {
	return e.recorded.Load()
}

// CUDAKernel represents a simulated CUDA kernel configuration.
type CUDAKernel struct {
	Name          string
	GridDimX      int
	GridDimY      int
	GridDimZ      int
	BlockDimX     int
	BlockDimY     int
	BlockDimZ     int
	SharedMem     int64
	RegsPerThread int
	Fn            func(args ...interface{}) error
}

// LaunchConfig returns a string describing the launch configuration.
func (k *CUDAKernel) LaunchConfig() string {
	return fmt.Sprintf("grid(%d,%d,%d) block(%d,%d,%d) shared=%d regs=%d",
		k.GridDimX, k.GridDimY, k.GridDimZ,
		k.BlockDimX, k.BlockDimY, k.BlockDimZ,
		k.SharedMem, k.RegsPerThread)
}

// CUDA implements a CUDA backend with CPU fallback.
type CUDA struct {
	deviceID      int
	deviceName    string
	computeCap    string // e.g. "8.6" for SM 8.6
	pool          *CUDAMemoryPool
	streams       []*CUDAStream
	currentStream int
	mu            sync.RWMutex
	available     bool
	stats         CUDAStats
	tensorCores   bool
}

// CUDAStats tracks CUDA backend statistics.
type CUDAStats struct {
	MatMulOps      atomic.Int64
	AddOps         atomic.Int64
	ReluOps        atomic.Int64
	SoftmaxOps     atomic.Int64
	MemCopies      atomic.Int64
	KernelLaunches atomic.Int64
}

// NewCUDA creates a new CUDA backend.
func NewCUDA(deviceID int, memoryMB int64) (*CUDA, error) {
	// Check for CUDA availability (simulated)
	// In production, would use cgo to bind to CUDA runtime
	c := &CUDA{
		deviceID:    deviceID,
		deviceName:  fmt.Sprintf("NVIDIA GeForce (Simulated) %d", deviceID),
		computeCap:  "8.6",
		pool:        NewCUDAMemoryPool(memoryMB * 1024 * 1024),
		available:   false, // Simulated - no real GPU
		tensorCores: true,
	}

	// Create default streams
	c.streams = make([]*CUDAStream, 4)
	for i := range c.streams {
		c.streams[i] = &CUDAStream{id: i, deviceID: deviceID}
	}

	return c, nil
}

// Name returns the backend name.
func (c *CUDA) Name() string {
	return "cuda"
}

// SupportedDtypes returns supported dtypes.
func (c *CUDA) SupportedDtypes() []string {
	return []string{"float64", "float32", "float16", "bfloat16", "int64", "int32", "int8"}
}

// Available returns whether CUDA is actually available.
func (c *CUDA) Available() bool {
	return c.available
}

// DeviceName returns the device name.
func (c *CUDA) DeviceName() string {
	return c.deviceName
}

// ComputeCapability returns the compute capability.
func (c *CUDA) ComputeCapability() string {
	return c.computeCap
}

// HasTensorCores returns whether tensor cores are available.
func (c *CUDA) HasTensorCores() bool {
	return c.tensorCores
}

// GetStream returns a CUDA stream by index.
func (c *CUDA) GetStream(idx int) *CUDAStream {
	c.mu.RLock()
	defer c.mu.RUnlock()
	if idx < 0 || idx >= len(c.streams) {
		return c.streams[0]
	}
	return c.streams[idx]
}

// CurrentStream returns the current stream.
func (c *CUDA) CurrentStream() *CUDAStream {
	c.mu.RLock()
	defer c.mu.RUnlock()
	return c.streams[c.currentStream]
}

// SetCurrentStream sets the current stream.
func (c *CUDA) SetCurrentStream(idx int) error {
	c.mu.Lock()
	defer c.mu.Unlock()
	if idx < 0 || idx >= len(c.streams) {
		return ErrCUDAStream
	}
	c.currentStream = idx
	return nil
}

// SynchronizeDevice synchronizes all streams.
func (c *CUDA) SynchronizeDevice() error {
	c.mu.RLock()
	streams := make([]*CUDAStream, len(c.streams))
	copy(streams, c.streams)
	c.mu.RUnlock()

	for _, s := range streams {
		if err := s.Synchronize(); err != nil {
			return err
		}
	}
	return nil
}

// MemoryStats returns memory statistics.
func (c *CUDA) MemoryStats() (used, peak, total int64) {
	return c.pool.Stats()
}

// Allocate allocates CUDA memory.
func (c *CUDA) Allocate(sizeBytes int64) (uintptr, error) {
	id, err := c.pool.Allocate(sizeBytes)
	if err != nil {
		return 0, err
	}
	c.stats.MemCopies.Add(1)
	return id, nil
}

// Free frees CUDA memory.
func (c *CUDA) Free(id uintptr) {
	c.pool.Free(id)
}

// MatMul performs matrix multiplication (simulated with CPU fallback).
// a: [m, k], b: [k, n] (column-major), output: [m, n]
func (c *CUDA) MatMul(a, b []float64, m, n, k int) ([]float64, error) {
	if len(a) != m*k {
		return nil, errors.New("invalid a dimensions")
	}
	if len(b) != k*n {
		return nil, errors.New("invalid b dimensions")
	}

	// Simulate tensor core usage for supported sizes
	useTensorCores := c.tensorCores && m%8 == 0 && k%8 == 0 && n%8 == 0

	out := make([]float64, m*n)
	c.stats.MatMulOps.Add(1)
	c.stats.KernelLaunches.Add(1)

	// Tiled matmul (simulating GPU tiling)
	const tileSize = 16

	if useTensorCores && m >= tileSize && n >= tileSize {
		// Simulate tensor core path with 16x16 tiles
		for i0 := 0; i0 < m; i0 += tileSize {
			for j0 := 0; j0 < n; j0 += tileSize {
				for l0 := 0; l0 < k; l0 += tileSize {
					iEnd := minInt(i0+tileSize, m)
					jEnd := minInt(j0+tileSize, n)
					lEnd := minInt(l0+tileSize, k)

					for i := i0; i < iEnd; i++ {
						for j := j0; j < jEnd; j++ {
							sum := out[i*n+j]
							for l := l0; l < lEnd; l++ {
								sum += a[i*k+l] * b[l*n+j]
							}
							out[i*n+j] = sum
						}
					}
				}
			}
		}
	} else {
		// Standard path
		for i := 0; i < m; i++ {
			for j := 0; j < n; j++ {
				sum := 0.0
				for l := 0; l < k; l++ {
					sum += a[i*k+l] * b[l*n+j]
				}
				out[i*n+j] = sum
			}
		}
	}

	return out, nil
}

// Add performs element-wise addition.
func (c *CUDA) Add(a, b []float64) ([]float64, error) {
	if len(a) != len(b) {
		return nil, errors.New("shape mismatch")
	}

	out := make([]float64, len(a))
	c.stats.AddOps.Add(1)
	c.stats.KernelLaunches.Add(1)

	for i := range a {
		out[i] = a[i] + b[i]
	}

	return out, nil
}

// Relu applies the ReLU activation.
func (c *CUDA) Relu(x []float64) []float64 {
	c.stats.ReluOps.Add(1)
	c.stats.KernelLaunches.Add(1)

	for i := range x {
		if x[i] < 0 {
			x[i] = 0
		}
	}
	return x
}

// Softmax applies the softmax function.
func (c *CUDA) Softmax(x []float64, dim int) ([]float64, error) {
	c.stats.SoftmaxOps.Add(1)
	c.stats.KernelLaunches.Add(1)
	return softmaxValues(x, dim)
}

// Stats returns CUDA statistics.
func (c *CUDA) Stats() *CUDAStats {
	return &c.stats
}

// Capabilities returns CUDA capabilities.
func (c *CUDA) Capabilities() Capabilities {
	_, _, total := c.pool.Stats()
	return Capabilities{
		Devices:      []Device{DeviceCUDA},
		Dtypes:       c.SupportedDtypes(),
		MaxMemory:    total,
		ThreadCount:  runtime.NumCPU(),
		HasVectorize: true,
		HasStreams:   true,
	}
}

// CUDAKernelLauncher simulates launching a CUDA kernel.
type CUDAKernelLauncher struct {
	cuda *CUDA
}

// NewCUDAKernelLauncher creates a kernel launcher.
func NewCUDAKernelLauncher(c *CUDA) *CUDAKernelLauncher {
	return &CUDAKernelLauncher{cuda: c}
}

// Launch launches a kernel on the current stream.
func (kl *CUDAKernelLauncher) Launch(kernel *CUDAKernel, args ...interface{}) error {
	if kernel.Fn == nil {
		return errors.New("kernel has no function")
	}

	stream := kl.cuda.CurrentStream()
	stream.mu.Lock()
	stream.busy.Store(true)
	stream.stats.OpsSubmitted.Add(1)
	stream.mu.Unlock()

	err := kernel.Fn(args...)

	stream.mu.Lock()
	stream.busy.Store(false)
	stream.stats.OpsCompleted.Add(1)
	stream.mu.Unlock()

	kl.cuda.stats.KernelLaunches.Add(1)
	return err
}

// LaunchAsync launches a kernel asynchronously.
func (kl *CUDAKernelLauncher) LaunchAsync(kernel *CUDAKernel, args ...interface{}) chan error {
	errCh := make(chan error, 1)
	go func() {
		errCh <- kl.Launch(kernel, args...)
	}()
	return errCh
}

// CUDAGraph captures a graph of operations for replay.
type CUDAGraph struct {
	ops            []*CUDAKernel
	captured       atomic.Bool
	mu             sync.Mutex
	instantiations atomic.Int64
}

// NewCUDAGraph creates a new CUDA graph.
func NewCUDAGraph() *CUDAGraph {
	return &CUDAGraph{}
}

// BeginCapture begins graph capture.
func (g *CUDAGraph) BeginCapture() {
	g.mu.Lock()
	defer g.mu.Unlock()
	g.ops = nil
	g.captured.Store(false)
}

// AddOp adds an operation to the graph.
func (g *CUDAGraph) AddOp(kernel *CUDAKernel) {
	g.mu.Lock()
	defer g.mu.Unlock()
	g.ops = append(g.ops, kernel)
}

// EndCapture ends graph capture.
func (g *CUDAGraph) EndCapture() {
	g.mu.Lock()
	defer g.mu.Unlock()
	g.captured.Store(true)
}

// Replay replays the captured graph.
func (g *CUDAGraph) Replay(launcher *CUDAKernelLauncher) error {
	g.mu.Lock()
	ops := make([]*CUDAKernel, len(g.ops))
	copy(ops, g.ops)
	g.mu.Unlock()

	for _, op := range ops {
		if err := launcher.Launch(op); err != nil {
			return err
		}
	}
	g.instantiations.Add(1)
	return nil
}

// CUDAMixedPrecisionConfig holds mixed precision configuration.
type CUDAMixedPrecisionConfig struct {
	Enabled        bool
	LossScale      float64
	DynamicScale   bool
	GrowthFactor   float64
	BackoffFactor  float64
	GrowthInterval int
}

// NewCUDAMixedPrecisionConfig creates a default mixed precision config.
func NewCUDAMixedPrecisionConfig() *CUDAMixedPrecisionConfig {
	return &CUDAMixedPrecisionConfig{
		Enabled:        true,
		LossScale:      65536.0,
		DynamicScale:   true,
		GrowthFactor:   2.0,
		BackoffFactor:  0.5,
		GrowthInterval: 2000,
	}
}

// minInt returns the minimum of two integers.
func minInt(a, b int) int {
	if a < b {
		return a
	}
	return b
}

// mathExp computes e^x, saturating to the representable range so callers
// that subtract a maximum before exponentiating never see NaN or ±Inf.
func mathExp(x float64) float64 {
	if x > 88 {
		return math.MaxFloat64
	}
	if x < -745 {
		return 0
	}
	return math.Exp(x)
}
