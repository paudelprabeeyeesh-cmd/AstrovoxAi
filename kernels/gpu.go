package kernels

import (
	"github.com/astrovox/astrovox/internal/backend"
	"github.com/astrovox/astrovox/internal/errors"
)

// GPU kernels are backend stubs: they register
// the full kernel catalog for CUDA, ROCm, Metal,
// and OpenCL and report a clear "unimplemented"
// error until the native runtimes land in
// later phases.

// gpuStub is a template for GPU kernel stubs.
type gpuStub struct {
	name string
	dev  backend.Device
}

// Name implements Kernel.
func (g gpuStub) Name() string { return g.name }

// Device implements Kernel.
func (g gpuStub) Device() backend.Device { return g.dev }

// Execute implements Kernel.
func (g gpuStub) Execute(inputs, outputs []TensorView, attrs map[string]any) error {
	return errors.New(errors.CodeUnimplemented, "GPU kernel not implemented").
		WithField("kernel", g.name).WithField("device", g.dev.String())
}

// GPUKernelNames is the catalog of kernel names
// mirrored across GPU backends.
var GPUKernelNames = []string{
	"vec_add", "vec_mul", "scale", "relu",
	"tanh", "sum", "matmul",
}

// RegisterGPUStubs registers the GPU kernel
// stubs for every supported GPU device class.
func RegisterGPUStubs() {
	devices := []backend.Device{
		backend.DeviceCUDA, backend.DeviceROCm,
		backend.DeviceMetal, backend.DeviceOpenCL,
	}
	for _, dev := range devices {
		for _, name := range GPUKernelNames {
			MustRegister(gpuStub{name: name, dev: dev})
		}
	}
}
