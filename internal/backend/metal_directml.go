package backend

import (
	"errors"
	"fmt"
	"sync"
	"sync/atomic"
)

// Metal backend error definitions.
var (
	ErrMetalNotAvailable = errors.New("metal not available")
	ErrMetalDevice       = errors.New("metal device error")
	ErrMetalBuffer       = errors.New("metal buffer error")
	ErrMetalLibrary      = errors.New("metal library error")
	ErrMetalCommandQueue = errors.New("metal command queue error")
)

// MetalDevice represents a simulated Metal device.
type MetalDevice struct {
	name           string
	registryID     uint64
	isLowPower     bool
	isHeadless     bool
	hasUnifiedMemory bool
	maxThreadsPerThreadgroup MetalSize
	maxBufferLength uint64
	recommendedMaxWorkingSetSize uint64
	streams        []*MetalCommandQueue
}

// MetalSize represents a 3D size.
type MetalSize struct {
	Width  uint64
	Height uint64
	Depth  uint64
}

// MetalCommandQueue represents a Metal command queue.
type MetalCommandQueue struct {
	id       int
	device   *MetalDevice
	buffers  []*MetalCommandBuffer
	busy     atomic.Bool
	stats    StreamStats
}

// ID returns the queue ID.
func (q *MetalCommandQueue) ID() int {
	return q.id
}

// Device returns the device.
func (q *MetalCommandQueue) Device() Device {
	return DeviceMetal
}

// Synchronize waits for all commands to complete.
func (q *MetalCommandQueue) Synchronize() error {
	q.busy.Store(false)
	return nil
}

// MetalCommandBuffer records Metal commands.
type MetalCommandBuffer struct {
	queue    *MetalCommandQueue
	state    MetalCommandBufferState
	encoders []MetalCommandEncoder
	committed atomic.Bool
	mu       sync.Mutex
}

// MetalCommandBufferState represents command buffer state.
type MetalCommandBufferState int

const (
	MetalCommandBufferStateInitial MetalCommandBufferState = iota
	MetalCommandBufferStateEncoding
	MetalCommandBufferStateCommitted
	MetalCommandBufferStateScheduled
	MetalCommandBufferStateCompleted
)

// MetalCommandEncoder is the interface for Metal command encoders.
type MetalCommandEncoder interface {
	EncoderType() string
}

// MetalComputeCommandEncoder encodes compute commands.
type MetalComputeCommandEncoder struct {
	pipeline     *MetalComputePipeline
	threadgroups int
	threadsPerTG int
	buffers      map[int]*MetalBuffer
	committed    atomic.Bool
}

// EncoderType returns the encoder type.
func (e *MetalComputeCommandEncoder) EncoderType() string {
	return "compute"
}

// MetalBuffer represents a Metal buffer.
type MetalBuffer struct {
	device   *MetalDevice
	length   uint64
	data     []byte
	deviceID uint64
	shared   bool
}

// MetalComputePipeline represents a Metal compute pipeline.
type MetalComputePipeline struct {
	name         string
	functionName string
	source       string
	maxThreads   MetalSize
	compiled     atomic.Bool
	mu           sync.Mutex
	execCount    atomic.Int64
}

// Compile compiles the pipeline (simulated).
func (p *MetalComputePipeline) Compile() error {
	p.mu.Lock()
	defer p.mu.Unlock()
	if p.compiled.Load() {
		return nil
	}
	if p.source == "" {
		return ErrMetalLibrary
	}
	p.compiled.Store(true)
	return nil
}

// IsCompiled returns whether the pipeline is compiled.
func (p *MetalComputePipeline) IsCompiled() bool {
	return p.compiled.Load()
}

// Metal implements a Metal backend with CPU fallback.
type Metal struct {
	device       *MetalDevice
	available    bool
	queues       []*MetalCommandQueue
	pipelines    map[string]*MetalComputePipeline
	buffers      map[uint64]*MetalBuffer
	nextBufferID atomic.Uint64
	mu           sync.RWMutex
	stats        MetalStats
}

// MetalStats tracks Metal statistics.
type MetalStats struct {
	MatMulOps      atomic.Int64
	AddOps         atomic.Int64
	ReluOps        atomic.Int64
	SoftmaxOps     atomic.Int64
	BufferAllocs   atomic.Int64
	BytesAllocated atomic.Int64
	PipelineCompiles atomic.Int64
	CommandBuffers atomic.Int64
}

// NewMetal creates a new Metal backend.
func NewMetal(memoryMB uint64) (*Metal, error) {
	device := &MetalDevice{
		name:                  "Apple M-series (Simulated)",
		registryID:            1,
		isLowPower:            false,
		isHeadless:            true,
		hasUnifiedMemory:      true,
		maxThreadsPerThreadgroup: MetalSize{Width: 1024, Height: 1024, Depth: 64},
		maxBufferLength:       memoryMB * 1024 * 1024,
		recommendedMaxWorkingSetSize: memoryMB * 1024 * 1024,
	}
	
	m := &Metal{
		device:    device,
		available: false, // Simulated
		pipelines: make(map[string]*MetalComputePipeline),
		buffers:   make(map[uint64]*MetalBuffer),
	}
	
	// Create command queues
	m.queues = make([]*MetalCommandQueue, 4)
	for i := range m.queues {
		m.queues[i] = &MetalCommandQueue{id: i, device: device}
	}
	
	return m, nil
}

// Name returns the backend name.
func (m *Metal) Name() string {
	return "metal"
}

// SupportedDtypes returns supported dtypes.
func (m *Metal) SupportedDtypes() []string {
	return []string{"float64", "float32", "float16", "int64", "int32", "int16", "int8", "uint8", "bool"}
}

// Available returns whether Metal is available.
func (m *Metal) Available() bool {
	return m.available
}

// Device returns the Metal device.
func (m *Metal) Device() *MetalDevice {
	return m.device
}

// GetQueue returns a command queue by index.
func (m *Metal) GetQueue(idx int) *MetalCommandQueue {
	m.mu.RLock()
	defer m.mu.RUnlock()
	if idx < 0 || idx >= len(m.queues) {
		return m.queues[0]
	}
	return m.queues[idx]
}

// CreateBuffer allocates a Metal buffer.
func (m *Metal) CreateBuffer(length uint64) (*MetalBuffer, error) {
	if length > m.device.maxBufferLength {
		return nil, ErrMetalBuffer
	}
	
	buf := &MetalBuffer{
		device: m.device,
		length: length,
		data:   make([]byte, length),
		deviceID: m.nextBufferID.Add(1),
		shared: m.device.hasUnifiedMemory,
	}
	
	m.mu.Lock()
	m.buffers[buf.deviceID] = buf
	m.mu.Unlock()
	
	m.stats.BufferAllocs.Add(1)
	m.stats.BytesAllocated.Add(int64(length))
	
	return buf, nil
}

// ReleaseBuffer releases a Metal buffer.
func (m *Metal) ReleaseBuffer(buf *MetalBuffer) {
	m.mu.Lock()
	delete(m.buffers, buf.deviceID)
	m.mu.Unlock()
}

// WriteBuffer writes data to a Metal buffer.
func (m *Metal) WriteBuffer(buf *MetalBuffer, data []byte) error {
	if uint64(len(data)) > buf.length {
		return ErrMetalBuffer
	}
	copy(buf.data, data)
	return nil
}

// ReadBuffer reads data from a Metal buffer.
func (m *Metal) ReadBuffer(buf *MetalBuffer) ([]byte, error) {
	out := make([]byte, buf.length)
	copy(out, buf.data)
	return out, nil
}

// CreatePipeline creates and compiles a Metal compute pipeline.
func (m *Metal) CreatePipeline(name, functionName, source string) (*MetalComputePipeline, error) {
	m.mu.Lock()
	defer m.mu.Unlock()
	
	if p, ok := m.pipelines[name]; ok {
		return p, nil
	}
	
	p := &MetalComputePipeline{
		name:         name,
		functionName: functionName,
		source:       source,
		maxThreads:   m.device.maxThreadsPerThreadgroup,
	}
	if err := p.Compile(); err != nil {
		return nil, err
	}
	m.pipelines[name] = p
	m.stats.PipelineCompiles.Add(1)
	return p, nil
}

// GetPipeline retrieves a pipeline by name.
func (m *Metal) GetPipeline(name string) (*MetalComputePipeline, bool) {
	m.mu.RLock()
	defer m.mu.RUnlock()
	p, ok := m.pipelines[name]
	return p, ok
}

// CreateCommandBuffer creates a new command buffer.
func (m *Metal) CreateCommandBuffer(queue *MetalCommandQueue) *MetalCommandBuffer {
	cb := &MetalCommandBuffer{queue: queue}
	m.stats.CommandBuffers.Add(1)
	return cb
}

// CreateComputeEncoder creates a compute command encoder.
func (m *Metal) CreateComputeEncoder(cb *MetalCommandBuffer, pipeline *MetalComputePipeline) (*MetalComputeCommandEncoder, error) {
	if !pipeline.IsCompiled() {
		return nil, ErrMetalLibrary
	}
	
	enc := &MetalComputeCommandEncoder{
		pipeline: pipeline,
		buffers:  make(map[int]*MetalBuffer),
	}
	
	cb.mu.Lock()
	cb.state = MetalCommandBufferStateEncoding
	cb.encoders = append(cb.encoders, enc)
	cb.mu.Unlock()
	
	return enc, nil
}

// SetBuffer binds a buffer to the encoder.
func (e *MetalComputeCommandEncoder) SetBuffer(buf *MetalBuffer, offset, index int) {
	e.buffers[index] = buf
}

// DispatchThreadgroups dispatches compute work.
func (e *MetalComputeCommandEncoder) DispatchThreadgroups(threadgroups, threadsPerTG int) error {
	if e.pipeline == nil {
		return ErrMetalLibrary
	}
	e.threadgroups = threadgroups
	e.threadsPerTG = threadsPerTG
	return nil
}

// EndEncoding ends the encoder.
func (e *MetalComputeCommandEncoder) EndEncoding() {
	e.committed.Store(true)
	e.pipeline.execCount.Add(1)
}

// Commit commits the command buffer.
func (cb *MetalCommandBuffer) Commit() {
	cb.mu.Lock()
	cb.state = MetalCommandBufferStateCommitted
	cb.mu.Unlock()
	cb.committed.Store(true)
}

// WaitUntilCompleted waits for the command buffer to complete.
func (cb *MetalCommandBuffer) WaitUntilCompleted() {
	cb.mu.Lock()
	cb.state = MetalCommandBufferStateCompleted
	cb.mu.Unlock()
}

// SynchronizeDevice synchronizes all queues.
func (m *Metal) SynchronizeDevice() error {
	m.mu.RLock()
	queues := make([]*MetalCommandQueue, len(m.queues))
	copy(queues, m.queues)
	m.mu.RUnlock()
	
	for _, q := range queues {
		if err := q.Synchronize(); err != nil {
			return err
		}
	}
	return nil
}

// MatMul performs matrix multiplication (simulated with CPU fallback).
func (m *Metal) MatMul(a, b []float64, mm, n, k int) ([]float64, error) {
	if len(a) != mm*k {
		return nil, errors.New("invalid a dimensions")
	}
	if len(b) != k*n {
		return nil, errors.New("invalid b dimensions")
	}
	
	m.stats.MatMulOps.Add(1)
	out := make([]float64, mm*n)
	
	for i := 0; i < mm; i++ {
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
func (m *Metal) Add(a, b []float64) ([]float64, error) {
	if len(a) != len(b) {
		return nil, errors.New("shape mismatch")
	}
	
	m.stats.AddOps.Add(1)
	out := make([]float64, len(a))
	for i := range a {
		out[i] = a[i] + b[i]
	}
	return out, nil
}

// Relu applies the ReLU activation.
func (m *Metal) Relu(x []float64) []float64 {
	m.stats.ReluOps.Add(1)
	for i := range x {
		if x[i] < 0 {
			x[i] = 0
		}
	}
	return x
}

// Softmax applies the softmax function.
func (m *Metal) Softmax(x []float64, dim int) ([]float64, error) {
	if len(x) == 0 {
		return nil, errors.New("empty input")
	}
	
	m.stats.SoftmaxOps.Add(1)
	
	maxVal := x[0]
	for _, v := range x {
		if v > maxVal {
			maxVal = v
		}
	}
	
	sum := 0.0
	for _, v := range x {
		sum += mathExp(v - maxVal)
	}
	
	out := make([]float64, len(x))
	for i, v := range x {
		out[i] = mathExp(v-maxVal) / sum
	}
	
	return out, nil
}

// Stats returns Metal statistics.
func (m *Metal) Stats() MetalStats {
	return m.stats
}

// Capabilities returns Metal capabilities.
func (m *Metal) Capabilities() Capabilities {
	return Capabilities{
		Devices:      []Device{DeviceMetal},
		Dtypes:       m.SupportedDtypes(),
		MaxMemory:    int64(m.device.maxBufferLength),
		ThreadCount:  int(m.device.maxThreadsPerThreadgroup.Width),
		HasVectorize: true,
		HasStreams:   true,
	}
}

// DirectML backend error definitions.
var (
	ErrDirectMLNotAvailable = errors.New("directml not available")
	ErrDirectMLDevice       = errors.New("directml device error")
	ErrDirectMLOperator     = errors.New("directml operator error")
)

// DirectMLDevice represents a DirectML device.
type DirectMLDevice struct {
	adapterName  string
	adapterIndex int
	isHardware   bool
	vendorID     uint32
	deviceID     uint32
}

// DirectML implements a DirectML backend with CPU fallback.
type DirectML struct {
	device       *DirectMLDevice
	available    bool
	stats        DirectMLStats
	mu           sync.RWMutex
}

// DirectMLStats tracks DirectML statistics.
type DirectMLStats struct {
	MatMulOps     atomic.Int64
	AddOps        atomic.Int64
	ReluOps       atomic.Int64
	SoftmaxOps    atomic.Int64
	ConvOps       atomic.Int64
	OperatorCompiles atomic.Int64
}

// NewDirectML creates a new DirectML backend.
func NewDirectML(adapterIndex int) (*DirectML, error) {
	device := &DirectMLDevice{
		adapterName:  fmt.Sprintf("DirectX 12 GPU (Simulated) %d", adapterIndex),
		adapterIndex: adapterIndex,
		isHardware:   false,
		vendorID:     0x10DE, // NVIDIA (simulated)
		deviceID:     0x2684,
	}
	
	d := &DirectML{
		device:    device,
		available: false, // Simulated
	}
	
	return d, nil
}

// Name returns the backend name.
func (d *DirectML) Name() string {
	return "directml"
}

// SupportedDtypes returns supported dtypes.
func (d *DirectML) SupportedDtypes() []string {
	return []string{"float64", "float32", "float16", "int64", "int32", "int16", "int8", "uint8"}
}

// Available returns whether DirectML is available.
func (d *DirectML) Available() bool {
	return d.available
}

// Device returns the DirectML device.
func (d *DirectML) Device() *DirectMLDevice {
	return d.device
}

// MatMul performs matrix multiplication (simulated).
func (d *DirectML) MatMul(a, b []float64, m, n, k int) ([]float64, error) {
	if len(a) != m*k {
		return nil, errors.New("invalid a dimensions")
	}
	if len(b) != k*n {
		return nil, errors.New("invalid b dimensions")
	}
	
	d.stats.MatMulOps.Add(1)
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
func (d *DirectML) Add(a, b []float64) ([]float64, error) {
	if len(a) != len(b) {
		return nil, errors.New("shape mismatch")
	}
	
	d.stats.AddOps.Add(1)
	out := make([]float64, len(a))
	for i := range a {
		out[i] = a[i] + b[i]
	}
	return out, nil
}

// Relu applies the ReLU activation.
func (d *DirectML) Relu(x []float64) []float64 {
	d.stats.ReluOps.Add(1)
	for i := range x {
		if x[i] < 0 {
			x[i] = 0
		}
	}
	return x
}

// Softmax applies the softmax function.
func (d *DirectML) Softmax(x []float64, dim int) ([]float64, error) {
	if len(x) == 0 {
		return nil, errors.New("empty input")
	}
	
	d.stats.SoftmaxOps.Add(1)
	
	maxVal := x[0]
	for _, v := range x {
		if v > maxVal {
			maxVal = v
		}
	}
	
	sum := 0.0
	for _, v := range x {
		sum += mathExp(v - maxVal)
	}
	
	out := make([]float64, len(x))
	for i, v := range x {
		out[i] = mathExp(v-maxVal) / sum
	}
	
	return out, nil
}

// Stats returns DirectML statistics.
func (d *DirectML) Stats() DirectMLStats {
	return d.stats
}

// Capabilities returns DirectML capabilities.
func (d *DirectML) Capabilities() Capabilities {
	return Capabilities{
		Devices:      []Device{DeviceCUDA}, // DirectML uses DirectX 12
		Dtypes:       d.SupportedDtypes(),
		MaxMemory:    8 * 1024 * 1024 * 1024, // 8GB default
		ThreadCount:  1,
		HasVectorize: true,
		HasStreams:   true,
	}
}