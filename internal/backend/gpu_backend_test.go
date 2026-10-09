package backend

import (
	"math"
	"testing"
)

func TestCUDACreation(t *testing.T) {
	c, err := NewCUDA(0, 1024)
	if err != nil {
		t.Fatal(err)
	}
	if c.Name() != "cuda" {
		t.Errorf("expected cuda, got %s", c.Name())
	}
}

func TestCUDADtypes(t *testing.T) {
	c, _ := NewCUDA(0, 1024)
	dtypes := c.SupportedDtypes()
	found := false
	for _, d := range dtypes {
		if d == "float16" {
			found = true
		}
	}
	if !found {
		t.Error("cuda should support float16")
	}
}

func TestCUDAMatMul(t *testing.T) {
	c, _ := NewCUDA(0, 1024)
	a := []float64{1, 2, 3, 4}
	b := []float64{1, 2, 3, 4}
	out, err := c.MatMul(a, b, 2, 2, 2)
	if err != nil {
		t.Fatal(err)
	}
	expected := []float64{7, 10, 15, 22}
	for i, v := range out {
		if math.Abs(v-expected[i]) > 1e-9 {
			t.Errorf("element %d: got %v, want %v", i, v, expected[i])
		}
	}
}

func TestCUDAMatMulTensorCores(t *testing.T) {
	c, _ := NewCUDA(0, 1024)
	if !c.HasTensorCores() {
		t.Error("expected tensor cores")
	}
	m := 16
	a := make([]float64, m*m)
	b := make([]float64, m*m)
	for i := range a {
		a[i] = float64(i % 5)
		b[i] = float64((i + 1) % 5)
	}
	out, err := c.MatMul(a, b, m, m, m)
	if err != nil {
		t.Fatal(err)
	}
	if len(out) != m*m {
		t.Errorf("expected %d elements, got %d", m*m, len(out))
	}
}

func TestCUDAMemoryPool(t *testing.T) {
	c, _ := NewCUDA(0, 1) // 1 MB
	id, err := c.Allocate(1024)
	if err != nil {
		t.Fatal(err)
	}
	c.Free(id)
	used, _, _ := c.MemoryStats()
	if used != 0 {
		t.Errorf("expected 0 used after free, got %d", used)
	}
}

func TestCUDAMemoryPoolOOM(t *testing.T) {
	c, _ := NewCUDA(0, 1)
	_, err := c.Allocate(10 * 1024 * 1024)
	if err != ErrCUDAMemory {
		t.Errorf("expected OOM error, got %v", err)
	}
}

func TestCUDAMemoryPoolPeak(t *testing.T) {
	c, _ := NewCUDA(0, 10)
	id1, _ := c.Allocate(1024)
	id2, _ := c.Allocate(2048)
	c.Free(id1)
	c.Free(id2)
	_, peak, _ := c.MemoryStats()
	if peak != 3072 {
		t.Errorf("expected peak 3072, got %d", peak)
	}
}

func TestCUDAStreams(t *testing.T) {
	c, _ := NewCUDA(0, 1024)
	s := c.GetStream(0)
	if s.ID() != 0 {
		t.Errorf("expected stream 0, got %d", s.ID())
	}
	if s.Device() != DeviceCUDA {
		t.Errorf("expected CUDA device")
	}
	if err := s.Synchronize(); err != nil {
		t.Fatal(err)
	}
}

func TestCUDACurrentStream(t *testing.T) {
	c, _ := NewCUDA(0, 1024)
	if err := c.SetCurrentStream(2); err != nil {
		t.Fatal(err)
	}
	if c.CurrentStream().ID() != 2 {
		t.Error("current stream should be 2")
	}
	if err := c.SetCurrentStream(99); err == nil {
		t.Error("expected error for invalid stream")
	}
}

func TestCUDAAdd(t *testing.T) {
	c, _ := NewCUDA(0, 1024)
	a := []float64{1, 2, 3}
	b := []float64{4, 5, 6}
	out, err := c.Add(a, b)
	if err != nil {
		t.Fatal(err)
	}
	for i := range out {
		if out[i] != a[i]+b[i] {
			t.Errorf("element %d mismatch", i)
		}
	}
}

func TestCUDARelu(t *testing.T) {
	c, _ := NewCUDA(0, 1024)
	x := []float64{-1, 0, 1}
	c.Relu(x)
	if x[0] != 0 || x[1] != 0 || x[2] != 1 {
		t.Error("relu failed")
	}
}

func TestCUDASoftmax(t *testing.T) {
	c, _ := NewCUDA(0, 1024)
	x := []float64{1, 2, 3}
	out, err := c.Softmax(x, 0)
	if err != nil {
		t.Fatal(err)
	}
	sum := 0.0
	for _, v := range out {
		sum += v
	}
	if math.Abs(sum-1.0) > 1e-9 {
		t.Errorf("softmax sum = %v", sum)
	}
}

func TestCUDAStats(t *testing.T) {
	c, _ := NewCUDA(0, 1024)
	c.MatMul(make([]float64, 4), make([]float64, 4), 2, 2, 2)
	stats := c.Stats()
	if stats.MatMulOps.Load() != 1 {
		t.Errorf("expected 1 matmul, got %d", stats.MatMulOps.Load())
	}
	if stats.KernelLaunches.Load() != 1 {
		t.Errorf("expected 1 launch, got %d", stats.KernelLaunches.Load())
	}
}

func TestCUDACapabilities(t *testing.T) {
	c, _ := NewCUDA(0, 2048)
	caps := c.Capabilities()
	if len(caps.Dtypes) == 0 {
		t.Error("expected dtypes")
	}
	if caps.MaxMemory != 2048*1024*1024 {
		t.Errorf("expected 2048MB, got %d", caps.MaxMemory)
	}
	if !caps.HasStreams {
		t.Error("expected streams support")
	}
}

func TestCUDAEvent(t *testing.T) {
	c, _ := NewCUDA(0, 1024)
	s := c.GetStream(0)
	e := &CUDAEvent{}
	if err := e.Record(s); err != nil {
		t.Fatal(err)
	}
	if !e.IsComplete() {
		t.Error("event should be complete")
	}
}

func TestCUDAKernelLaunch(t *testing.T) {
	c, _ := NewCUDA(0, 1024)
	launcher := NewCUDAKernelLauncher(c)
	kernel := &CUDAKernel{
		Name: "test",
		Fn:   func(args ...interface{}) error { return nil },
	}
	if err := launcher.Launch(kernel); err != nil {
		t.Fatal(err)
	}
	if c.stats.KernelLaunches.Load() != 1 {
		t.Error("kernel should be launched")
	}
}

func TestCUDAKernelLaunchConfig(t *testing.T) {
	kernel := &CUDAKernel{
		Name:      "test",
		GridDimX:  10,
		BlockDimX: 256,
		SharedMem: 1024,
	}
	config := kernel.LaunchConfig()
	if config == "" {
		t.Error("expected non-empty config")
	}
}

func TestCUDAGraph(t *testing.T) {
	c, _ := NewCUDA(0, 1024)
	g := NewCUDAGraph()
	launcher := NewCUDAKernelLauncher(c)
	
	g.BeginCapture()
	g.AddOp(&CUDAKernel{Name: "op1", Fn: func(args ...interface{}) error { return nil }})
	g.AddOp(&CUDAKernel{Name: "op2", Fn: func(args ...interface{}) error { return nil }})
	g.EndCapture()
	
	if err := g.Replay(launcher); err != nil {
		t.Fatal(err)
	}
	if g.instantiations.Load() != 1 {
		t.Error("graph should be replayed once")
	}
}

func TestVulkanCreation(t *testing.T) {
	v, err := NewVulkan(VulkanDeviceTypeDiscreteGPU, 1024)
	if err != nil {
		t.Fatal(err)
	}
	if v.Name() != "vulkan" {
		t.Errorf("expected vulkan, got %s", v.Name())
	}
}

func TestVulkanDeviceQueues(t *testing.T) {
	v, _ := NewVulkan(VulkanDeviceTypeDiscreteGPU, 1024)
	if len(v.device.computeQueues) == 0 {
		t.Error("expected compute queues")
	}
	if len(v.device.graphicsQueues) == 0 {
		t.Error("expected graphics queues")
	}
	if len(v.device.transferQueues) == 0 {
		t.Error("expected transfer queues")
	}
}

func TestVulkanMatMul(t *testing.T) {
	v, _ := NewVulkan(VulkanDeviceTypeDiscreteGPU, 1024)
	a := []float64{1, 2, 3, 4}
	b := []float64{1, 2, 3, 4}
	out, err := v.MatMul(a, b, 2, 2, 2)
	if err != nil {
		t.Fatal(err)
	}
	expected := []float64{7, 10, 15, 22}
	for i, val := range out {
		if math.Abs(val-expected[i]) > 1e-9 {
			t.Errorf("element %d: got %v, want %v", i, val, expected[i])
		}
	}
}

func TestVulkanPipeline(t *testing.T) {
	v, _ := NewVulkan(VulkanDeviceTypeDiscreteGPU, 1024)
	p, err := v.CreatePipeline("test", []byte("shader"))
	if err != nil {
		t.Fatal(err)
	}
	if !p.IsCompiled() {
		t.Error("pipeline should be compiled")
	}
	if p.ExecutionCount() != 0 {
		t.Error("pipeline should not be executed yet")
	}
}

func TestVulkanPipelineEmptyShader(t *testing.T) {
	v, _ := NewVulkan(VulkanDeviceTypeDiscreteGPU, 1024)
	_, err := v.CreatePipeline("bad", nil)
	if err != ErrVulkanPipeline {
		t.Errorf("expected pipeline error, got %v", err)
	}
}

func TestVulkanCommandBuffer(t *testing.T) {
	v, _ := NewVulkan(VulkanDeviceTypeDiscreteGPU, 1024)
	stream := v.GetStream(0)
	cb := stream.cmdBuffer
	if err := cb.Begin(); err != nil {
		t.Fatal(err)
	}
	if cb.state != VulkanCommandBufferStateRecording {
		t.Error("should be recording")
	}
	if err := cb.End(); err != nil {
		t.Fatal(err)
	}
}

func TestVulkanDispatch(t *testing.T) {
	v, _ := NewVulkan(VulkanDeviceTypeDiscreteGPU, 1024)
	p, _ := v.CreatePipeline("test", []byte("shader"))
	stream := v.GetStream(0)
	err := v.Dispatch(stream, p, 10, 10, 1, nil)
	if err != nil {
		t.Fatal(err)
	}
	if p.ExecutionCount() != 1 {
		t.Error("pipeline should be executed once")
	}
}

func TestVulkanMemoryAllocation(t *testing.T) {
	v, _ := NewVulkan(VulkanDeviceTypeDiscreteGPU, 1024)
	offset, err := v.Allocate(4096, true)
	if err != nil {
		t.Fatal(err)
	}
	if offset != 0 {
		t.Errorf("expected offset 0, got %d", offset)
	}
}

func TestVulkanSoftmax(t *testing.T) {
	v, _ := NewVulkan(VulkanDeviceTypeDiscreteGPU, 1024)
	x := []float64{1, 2, 3}
	out, err := v.Softmax(x, 0)
	if err != nil {
		t.Fatal(err)
	}
	sum := 0.0
	for _, val := range out {
		sum += val
	}
	if math.Abs(sum-1.0) > 1e-9 {
		t.Errorf("softmax sum = %v", sum)
	}
}

func TestVulkanSPIRVCompiler(t *testing.T) {
	c := NewVulkanSPIRVCompiler()
	spirv, err := c.CompileGLSL("#version 450\nvoid main() {}")
	if err != nil {
		t.Fatal(err)
	}
	if len(spirv) == 0 {
		t.Error("expected SPIR-V output")
	}
}

func TestMetalCreation(t *testing.T) {
	m, err := NewMetal(1024)
	if err != nil {
		t.Fatal(err)
	}
	if m.Name() != "metal" {
		t.Errorf("expected metal, got %s", m.Name())
	}
}

func TestMetalUnifiedMemory(t *testing.T) {
	m, _ := NewMetal(1024)
	if !m.device.hasUnifiedMemory {
		t.Error("Metal should have unified memory")
	}
}

func TestMetalBuffer(t *testing.T) {
	m, _ := NewMetal(1024)
	buf, err := m.CreateBuffer(1024)
	if err != nil {
		t.Fatal(err)
	}
	data := []byte{1, 2, 3, 4}
	if err := m.WriteBuffer(buf, data); err != nil {
		t.Fatal(err)
	}
	read, err := m.ReadBuffer(buf)
	if err != nil {
		t.Fatal(err)
	}
	for i, b := range data {
		if read[i] != b {
			t.Errorf("byte %d mismatch", i)
		}
	}
	m.ReleaseBuffer(buf)
}

func TestMetalBufferTooLarge(t *testing.T) {
	m, _ := NewMetal(1) // 1 MB
	_, err := m.CreateBuffer(10 * 1024 * 1024)
	if err != ErrMetalBuffer {
		t.Errorf("expected buffer error, got %v", err)
	}
}

func TestMetalPipeline(t *testing.T) {
	m, _ := NewMetal(1024)
	p, err := m.CreatePipeline("test", "main", "kernel void main() {}")
	if err != nil {
		t.Fatal(err)
	}
	if !p.IsCompiled() {
		t.Error("pipeline should be compiled")
	}
}

func TestMetalCommandBuffer(t *testing.T) {
	m, _ := NewMetal(1024)
	p, _ := m.CreatePipeline("test", "main", "kernel void main() {}")
	q := m.GetQueue(0)
	cb := m.CreateCommandBuffer(q)
	enc, err := m.CreateComputeEncoder(cb, p)
	if err != nil {
		t.Fatal(err)
	}
	enc.DispatchThreadgroups(10, 64)
	enc.EndEncoding()
	cb.Commit()
	cb.WaitUntilCompleted()
	if p.execCount.Load() < 1 {
		t.Errorf("pipeline should be executed, got %d", p.execCount.Load())
	}
}

func TestMetalMatMul(t *testing.T) {
	m, _ := NewMetal(1024)
	a := []float64{1, 2, 3, 4}
	b := []float64{1, 2, 3, 4}
	out, err := m.MatMul(a, b, 2, 2, 2)
	if err != nil {
		t.Fatal(err)
	}
	expected := []float64{7, 10, 15, 22}
	for i, v := range out {
		if math.Abs(v-expected[i]) > 1e-9 {
			t.Errorf("element %d: got %v, want %v", i, v, expected[i])
		}
	}
}

func TestMetalStats(t *testing.T) {
	m, _ := NewMetal(1024)
	m.MatMul(make([]float64, 4), make([]float64, 4), 2, 2, 2)
	stats := m.Stats()
	if stats.MatMulOps.Load() != 1 {
		t.Error("expected 1 matmul")
	}
}

func TestDirectMLCreation(t *testing.T) {
	d, err := NewDirectML(0)
	if err != nil {
		t.Fatal(err)
	}
	if d.Name() != "directml" {
		t.Errorf("expected directml, got %s", d.Name())
	}
}

func TestDirectMLMatMul(t *testing.T) {
	d, _ := NewDirectML(0)
	a := []float64{1, 2, 3, 4}
	b := []float64{1, 2, 3, 4}
	out, err := d.MatMul(a, b, 2, 2, 2)
	if err != nil {
		t.Fatal(err)
	}
	expected := []float64{7, 10, 15, 22}
	for i, v := range out {
		if math.Abs(v-expected[i]) > 1e-9 {
			t.Errorf("element %d: got %v, want %v", i, v, expected[i])
		}
	}
}

func TestDirectMLSoftmax(t *testing.T) {
	d, _ := NewDirectML(0)
	x := []float64{1, 2, 3}
	out, err := d.Softmax(x, 0)
	if err != nil {
		t.Fatal(err)
	}
	sum := 0.0
	for _, v := range out {
		sum += v
	}
	if math.Abs(sum-1.0) > 1e-9 {
		t.Error("softmax should sum to 1")
	}
}

func TestBackendSelectorPreferred(t *testing.T) {
	cpu := NewCPUBackend()
	selector := NewBackendSelector(BackendTypeMetal, cpu)
	selector.Register(cpu)
	metal, _ := NewMetal(1024)
	selector.Register(metal)
	
	// Metal is not available, should fall back to CPU
	selected := selector.Select()
	if selected.Name() != "cpu" {
		t.Errorf("expected cpu fallback, got %s", selected.Name())
	}
}

func TestBackendSelectorCPUOnly(t *testing.T) {
	cpu := NewCPUBackend()
	selector := NewBackendSelector(BackendTypeCUDA, cpu)
	selector.Register(cpu)
	selected := selector.Select()
	if selected.Name() != "cpu" {
		t.Errorf("expected cpu, got %s", selected.Name())
	}
}

func TestInitDefaultBackends(t *testing.T) {
	selector, err := InitDefaultBackends()
	if err != nil {
		t.Fatal(err)
	}
	backends := selector.AvailableBackends()
	if len(backends) < 2 {
		t.Errorf("expected at least 2 backends, got %d", len(backends))
	}
	selected := selector.Select()
	if selected == nil {
		t.Fatal("expected a backend")
	}
	if selected.Name() != "cpu" {
		t.Errorf("expected cpu fallback (no real GPU), got %s", selected.Name())
	}
}

func TestBackendTypeString(t *testing.T) {
	tests := []struct {
		bt   BackendType
		want string
	}{
		{BackendTypeCPU, "cpu"},
		{BackendTypeCUDA, "cuda"},
		{BackendTypeVulkan, "vulkan"},
		{BackendTypeMetal, "metal"},
		{BackendTypeDirectML, "directml"},
	}
	for _, tt := range tests {
		if tt.bt.String() != tt.want {
			t.Errorf("BackendType(%d).String() = %s, want %s", tt.bt, tt.bt.String(), tt.want)
		}
	}
}

func TestMathExp(t *testing.T) {
	if math.Abs(mathExp(0)-1.0) > 1e-9 {
		t.Error("exp(0) should be 1")
	}
	if math.Abs(mathExp(1)-math.E) > 1e-6 {
		t.Errorf("exp(1) = %v, want %v", mathExp(1), math.E)
	}
	if mathExp(100) != 1.7976931348623157e308 {
		t.Error("exp(100) should be max float64")
	}
	if mathExp(-100) != 0 {
		t.Error("exp(-100) should be 0")
	}
}