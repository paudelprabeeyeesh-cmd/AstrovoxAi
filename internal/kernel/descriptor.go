package kernel

import (
	"fmt"
	"strings"
)

// Descriptor describes a kernel's signature.
type Descriptor struct {
	Name         string
	Version      string
	Inputs       []TensorDesc
	Outputs      []TensorDesc
	Attributes   map[string]interface{}
	Backends     []string
	Tags         []string
}

// TensorDesc describes a tensor argument.
type TensorDesc struct {
	Name   string
	DType  string
	Shape  []int
	Stride []int
}

// Validate checks descriptor consistency.
func (d *Descriptor) Validate() error {
	if strings.TrimSpace(d.Name) == "" {
		return fmt.Errorf("kernel name is empty")
	}
	if len(d.Inputs) == 0 {
		return fmt.Errorf("kernel %s has no inputs", d.Name)
	}
	if len(d.Outputs) == 0 {
		return fmt.Errorf("kernel %s has no outputs", d.Name)
	}
	return nil
}

func (d *Descriptor) String() string {
	return fmt.Sprintf("%s@%s [%d in, %d out]", d.Name, d.Version, len(d.Inputs), len(d.Outputs))
}
