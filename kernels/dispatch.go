package kernels

import (
	"github.com/astrovox/astrovox/internal/backend"
	"github.com/astrovox/astrovox/internal/errors"
)

// Dispatcher selects and executes kernels
// against a target device, with automatic
// fallback to the CPU when the requested
// device lacks the kernel.
type Dispatcher struct {
	device backend.Device
	// Fallback controls whether missing GPU
	// kernels fall back to the CPU implementation.
	Fallback bool
}

// NewDispatcher creates a dispatcher bound to a
// device. GPU devices get fallback enabled by
// default.
func NewDispatcher(dev backend.Device) *Dispatcher {
	d := &Dispatcher{device: dev}
	switch dev {
	case backend.DeviceCUDA, backend.DeviceROCm,
		backend.DeviceMetal, backend.DeviceOpenCL:
		d.Fallback = true
	default:
		d.Fallback = false
	}
	return d
}

// Device returns the bound device.
func (d *Dispatcher) Device() backend.Device { return d.device }

// Run looks up the kernel and executes it.
// When the bound device's kernel reports
// CodeUnimplemented (a GPU stub) and fallback
// is enabled, the CPU implementation runs
// instead.
func (d *Dispatcher) Run(name string, inputs, outputs []TensorView, attrs map[string]any) error {
	k, err := Lookup(d.device, name)
	if err != nil {
		if d.Fallback && d.device != backend.DeviceCPU {
			k, ferr := Lookup(backend.DeviceCPU, name)
			if ferr != nil {
				return errors.Wrap(err, errors.CodeNotFound, "kernel unavailable").
					WithField("name", name).WithField("device", d.device.String())
			}
			return k.Execute(inputs, outputs, attrs)
		}
		return errors.Wrap(err, errors.CodeNotFound, "kernel unavailable").
			WithField("name", name).WithField("device", d.device.String())
	}
	err = k.Execute(inputs, outputs, attrs)
	if err != nil && d.Fallback && d.device != backend.DeviceCPU &&
		errors.CodeOf(err) == errors.CodeUnimplemented {
		// GPU stub: retry on the CPU backend.
		cpu, ferr := Lookup(backend.DeviceCPU, name)
		if ferr != nil {
			return errors.Wrap(err, errors.CodeUnimplemented, "kernel unimplemented").
				WithField("name", name).WithField("device", d.device.String())
		}
		return cpu.Execute(inputs, outputs, attrs)
	}
	return err
}

// RunAny looks up the kernel on any device,
// preferring the dispatcher's bound device.
func (d *Dispatcher) RunAny(name string, inputs, outputs []TensorView, attrs map[string]any) error {
	k, err := LookupAny(d.device, name)
	if err != nil {
		return errors.Wrap(err, errors.CodeNotFound, "kernel unavailable").
			WithField("name", name)
	}
	return k.Execute(inputs, outputs, attrs)
}

// ExecuteVecAdd dispatches an elementwise add.
func (d *Dispatcher) ExecuteVecAdd(a, b, out TensorView) error {
	return d.Run("vec_add", []TensorView{a, b}, []TensorView{out}, nil)
}

// ExecuteVecMul dispatches an elementwise mul.
func (d *Dispatcher) ExecuteVecMul(a, b, out TensorView) error {
	return d.Run("vec_mul", []TensorView{a, b}, []TensorView{out}, nil)
}

// ExecuteScale dispatches a scalar multiply.
func (d *Dispatcher) ExecuteScale(a, out TensorView, scalar float64) error {
	return d.Run("scale", []TensorView{a}, []TensorView{out},
		map[string]any{"scalar": scalar})
}

// ExecuteRelu dispatches the ReLU activation.
func (d *Dispatcher) ExecuteRelu(a, out TensorView) error {
	return d.Run("relu", []TensorView{a}, []TensorView{out}, nil)
}

// ExecuteMatMul dispatches a matmul.
func (d *Dispatcher) ExecuteMatMul(a, b, out TensorView) error {
	return d.Run("matmul", []TensorView{a, b}, []TensorView{out}, nil)
}

// init registers the CPU kernel catalog.
func init() {
	MustRegister(VecAddKernel{})
	MustRegister(VecMulKernel{})
	MustRegister(ScaleKernel{})
	MustRegister(ReluKernel{})
	MustRegister(TanhKernel{})
	MustRegister(SumKernel{})
	MustRegister(MatMulKernel{})
	RegisterGPUStubs()
}
