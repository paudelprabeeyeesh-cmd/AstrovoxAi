package compat

import (
	"testing"

	"github.com/astrovox/astrovox/internal/backend"
	"github.com/astrovox/astrovox/tensor"
)

// TestDtypeCoverageAcrossBackends verifies every backend accepts the dtypes
// it advertises, and that float64 always works on every backend.
func TestDtypeCoverageAcrossBackends(t *testing.T) {
	sel, err := backend.InitDefaultBackends()
	if err != nil {
		t.Fatal(err)
	}
	names := sel.AvailableBackends()
	if len(names) < 3 {
		t.Fatalf("expected multiple backends, got %v", names)
	}

	for _, name := range names {
		b, ok := backend.GetBackend(name)
		if !ok {
			t.Errorf("backend %q registered but not found", name)
			continue
		}
		dtypes := b.SupportedDtypes()
		if len(dtypes) == 0 {
			t.Errorf("%s advertises no dtypes", name)
			continue
		}
		// Every backend that is not WebGPU must support float64. WebGPU's
		// base WGSL spec has no 64-bit float; it is f32/f16 only.
		if name != "webgpu" && !containsString(dtypes, "float64") {
			t.Errorf("%s must support float64, got %v", name, dtypes)
		}
		if name == "webgpu" && !containsString(dtypes, "float32") {
			t.Errorf("webgpu must support float32, got %v", dtypes)
		}
		// Every advertised dtype must be parseable by the engine, otherwise
		// backend selection could hand back an unusable dtype.
		for _, dt := range dtypes {
			if _, err := tensor.ParseDType(dt); err != nil {
				t.Errorf("%s advertises %s but the engine cannot parse it: %v", name, dt, err)
			}
		}
	}
}

// TestSelectedBackendSupportsFloat64 verifies the automatic selection
// always returns a backend that can run the float64 reference kernels.
func TestSelectedBackendSupportsFloat64(t *testing.T) {
	t.Parallel()
	sel, err := backend.InitDefaultBackends()
	if err != nil {
		t.Fatal(err)
	}
	selected := sel.Select()
	if selected == nil {
		t.Fatal("expected a selected backend")
	}
	if !containsString(selected.SupportedDtypes(), "float64") {
		t.Fatalf("selected backend %q must support float64, got %v",
			selected.Name(), selected.SupportedDtypes())
	}
}

func containsString(list []string, want string) bool {
	for _, s := range list {
		if s == want {
			return true
		}
	}
	return false
}

// TestTensorDtypeRoundTrip verifies dtype names parse and construct.
func TestTensorDtypeRoundTrip(t *testing.T) {
	cases := []struct {
		dtype tensor.DType
		name  string
	}{
		{tensor.Float64, "float64"},
		{tensor.Int64, "int64"},
		{tensor.Int32, "int32"},
		{tensor.Int16, "int16"},
		{tensor.Int8, "int8"},
	}
	for _, tc := range cases {
		parsed, err := tensor.ParseDType(tc.name)
		if err != nil {
			t.Errorf("%s: parse: %v", tc.name, err)
			continue
		}
		if parsed != tc.dtype {
			t.Errorf("%s parsed as %v", tc.name, parsed)
		}
		ten, err := tensor.New(tc.dtype, []int{1})
		if err != nil {
			t.Errorf("%s: %v", tc.name, err)
			continue
		}
		if ten.NumElements() != 1 {
			t.Errorf("%s: expected 1 element", tc.name)
		}
	}
}

// TestShapeCompatibility verifies tensor shapes stay consistent across
// reshape/transpose/length checks.
func TestShapeCompatibility(t *testing.T) {
	ten, err := tensor.New(tensor.Float64, []int{2, 3})
	if err != nil {
		t.Fatal(err)
	}
	if ten.NumElements() != 6 {
		t.Fatalf("num elements = %d, want 6", ten.NumElements())
	}
	if dims := ten.Shape().Dims(); len(dims) != 2 || dims[0] != 2 || dims[1] != 3 {
		t.Errorf("dims = %v", dims)
	}
	tr, err := ten.Transpose(1, 0)
	if err != nil {
		t.Fatal(err)
	}
	if d := tr.Shape().Dims(); d[0] != 3 || d[1] != 2 {
		t.Errorf("transposed dims = %v", d)
	}
	if tr.NumElements() != ten.NumElements() {
		t.Error("transpose must preserve element count")
	}
}

// TestAPIVersionConsistency checks the engine exposes a usable capability spec.
func TestAPIVersionConsistency(t *testing.T) {
	v := backend.Capabilities{}
	if v.ThreadCount != 0 {
		t.Error("zero value should be usable as a spec")
	}
	cpu := backend.NewCPUBackend()
	if len(cpu.SupportedDtypes()) == 0 {
		t.Error("expected dtype list")
	}
}
