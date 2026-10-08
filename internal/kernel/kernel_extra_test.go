package kernel

import (
	"testing"
)

func TestParseVersion_Invalid(t *testing.T) {
	for _, s := range []string{"1.2", "1", "a.b.c", "1.2.x", ""} {
		if _, err := ParseVersion(s); err == nil {
			t.Fatalf("expected error for %q, got nil", s)
		}
	}
}

func TestVersion_String(t *testing.T) {
	v := Version{Major: 2, Minor: 0, Patch: 1}
	if s := v.String(); s != "2.0.1" {
		t.Fatalf("String = %s, want 2.0.1", s)
	}
}

func TestVersion_Less(t *testing.T) {
	cases := []struct {
		a, b     Version
		wantLess bool
	}{
		{Version{1, 0, 0}, Version{2, 0, 0}, true},
		{Version{1, 2, 0}, Version{1, 3, 0}, true},
		{Version{1, 2, 3}, Version{1, 2, 4}, true},
		{Version{2, 0, 0}, Version{1, 0, 0}, false},
		{Version{1, 3, 0}, Version{1, 2, 0}, false},
		{Version{1, 2, 4}, Version{1, 2, 3}, false},
		{Version{1, 0, 0}, Version{1, 0, 0}, false},
	}
	for _, c := range cases {
		got := c.a.Less(c.b)
		if got != c.wantLess {
			t.Errorf("(%s).Less(%s) = %v, want %v", c.a, c.b, got, c.wantLess)
		}
	}
}

func TestDescriptor_Validate_EmptyName(t *testing.T) {
	d := &Descriptor{Name: "   ", Inputs: []TensorDesc{{}}, Outputs: []TensorDesc{{}}}
	if err := d.Validate(); err == nil {
		t.Fatal("expected error for empty name")
	}
}

func TestDescriptor_Validate_MissingInputs(t *testing.T) {
	d := &Descriptor{Name: "k", Inputs: nil, Outputs: []TensorDesc{{}}}
	if err := d.Validate(); err == nil {
		t.Fatal("expected error for missing inputs")
	}
}

func TestDescriptor_Validate_MissingOutputs(t *testing.T) {
	d := &Descriptor{Name: "k", Inputs: []TensorDesc{{}}, Outputs: nil}
	if err := d.Validate(); err == nil {
		t.Fatal("expected error for missing outputs")
	}
}

func TestDescriptor_Validate_Valid(t *testing.T) {
	d := &Descriptor{Name: "valid", Inputs: []TensorDesc{{Name: "x"}}, Outputs: []TensorDesc{{Name: "y"}}}
	if err := d.Validate(); err != nil {
		t.Fatalf("Validate: %v", err)
	}
}

func TestDescriptor_String(t *testing.T) {
	d := &Descriptor{Name: "matmul", Version: "1.0", Inputs: []TensorDesc{{}, {}}, Outputs: []TensorDesc{{}}}
	s := d.String()
	if s != "matmul@1.0 [2 in, 1 out]" {
		t.Fatalf("String = %q, want matmul@1.0 [2 in, 1 out]", s)
	}
}

func TestDescriptor_StringEmptyVersion(t *testing.T) {
	d := &Descriptor{Name: "k", Inputs: []TensorDesc{{}}, Outputs: []TensorDesc{{}}}
	if s := d.String(); s != "k@ [1 in, 1 out]" {
		t.Fatalf("String = %q", s)
	}
}

func TestRegistry_Lookup(t *testing.T) {
	r := NewRegistry()
	desc := &Descriptor{Name: "matmul", Version: "1.0", Inputs: []TensorDesc{{}}, Outputs: []TensorDesc{{}}}
	_ = r.Register(desc, "impl")
	entries := r.Lookup("matmul")
	if len(entries) != 1 {
		t.Fatalf("len = %d, want 1", len(entries))
	}
	if entries[0].Impl != "impl" {
		t.Fatalf("impl = %v, want impl", entries[0].Impl)
	}
}

func TestRegistry_LookupMissing(t *testing.T) {
	r := NewRegistry()
	if entries := r.Lookup("nonexistent"); entries != nil && len(entries) != 0 {
		t.Fatalf("expected empty, got %d", len(entries))
	}
}

func TestRegistry_InvalidDescriptor(t *testing.T) {
	r := NewRegistry()
	if err := r.Register(&Descriptor{}, "impl"); err == nil {
		t.Fatal("expected error for invalid descriptor")
	}
}

func TestRegistry_DifferentVersions(t *testing.T) {
	r := NewRegistry()
	d1 := &Descriptor{Name: "add", Version: "1.0", Inputs: []TensorDesc{{}}, Outputs: []TensorDesc{{}}}
	d2 := &Descriptor{Name: "add", Version: "2.0", Inputs: []TensorDesc{{}}, Outputs: []TensorDesc{{}}}
	if err := r.Register(d1, "impl1"); err != nil {
		t.Fatalf("Register v1: %v", err)
	}
	if err := r.Register(d2, "impl2"); err != nil {
		t.Fatalf("Register v2: %v", err)
	}
}

func TestSelector_NotFound(t *testing.T) {
	reg := NewRegistry()
	sel := NewSelector(reg)
	if e := sel.Select(nil, "1.0", "cpu"); e != nil {
		t.Fatal("expected nil for empty entries")
	}
}

func TestSelector_VersionFallback(t *testing.T) {
	reg := NewRegistry()
	_ = reg.Register(&Descriptor{Name: "add", Version: "1.0", Backends: []string{"cpu"}, Inputs: []TensorDesc{{}}, Outputs: []TensorDesc{{}}}, "v1")
	_ = reg.Register(&Descriptor{Name: "add", Version: "2.0", Backends: []string{"cpu"}, Inputs: []TensorDesc{{}}, Outputs: []TensorDesc{{}}}, "v2")
	sel := NewSelector(reg)
	e := sel.Select(reg.Lookup("add"), "3.0", "cpu")
	if e == nil {
		t.Fatal("expected fallback selection")
	}
}

func TestSelector_BackendFallback(t *testing.T) {
	reg := NewRegistry()
	_ = reg.Register(&Descriptor{Name: "add", Version: "1.0", Backends: []string{"cpu"}, Inputs: []TensorDesc{{}}, Outputs: []TensorDesc{{}}}, "cpu_impl")
	sel := NewSelector(reg)
	e := sel.Select(reg.Lookup("add"), "1.0", "gpu")
	if e == nil {
		t.Fatal("expected fallback to first entry")
	}
}

func TestCache_GetPresent(t *testing.T) {
	c := NewCache(10)
	entry := &Entry{Descriptor: &Descriptor{Name: "x"}}
	c.Put("key1", entry)
	got := c.Get("key1")
	if got != entry {
		t.Error("cache miss")
	}
}

func TestCache_Miss(t *testing.T) {
	c := NewCache(10)
	if c.Get("missing") != nil {
		t.Fatal("expected nil for missing key")
	}
}

func TestCache_Overwrite(t *testing.T) {
	c := NewCache(2)
	c.Put("k", &Entry{Descriptor: &Descriptor{Name: "v1"}})
	c.Put("k", &Entry{Descriptor: &Descriptor{Name: "v2"}})
	e := c.Get("k")
	if e.Descriptor.Name != "v2" {
		t.Fatalf("overwrite: got %s, want v2", e.Descriptor.Name)
	}
}

func TestCache_Size(t *testing.T) {
	c := NewCache(10)
	if s := c.Size(); s != 0 {
		t.Fatalf("size = %d, want 0", s)
	}
	c.Put("k1", &Entry{})
	c.Put("k2", &Entry{})
	if s := c.Size(); s != 2 {
		t.Fatalf("size = %d, want 2", s)
	}
}

func TestCache_EvictOldest(t *testing.T) {
	c := NewCache(2)
	c.Put("a", &Entry{Descriptor: &Descriptor{Name: "a"}})
	c.Put("b", &Entry{Descriptor: &Descriptor{Name: "b"}})
	c.Put("c", &Entry{Descriptor: &Descriptor{Name: "c"}})
	if c.Get("a") != nil {
		t.Fatal("expected a to be evicted")
	}
	if c.Get("b") == nil || c.Get("c") == nil {
		t.Fatal("expected b and c to remain")
	}
}

func TestCache_EmptyAfterClear(t *testing.T) {
	c := NewCache(10)
	c.Put("x", &Entry{})
	c.Put("y", &Entry{})
	c.Clear()
	if c.Size() != 0 {
		t.Fatalf("size after clear = %d, want 0", c.Size())
	}
	if c.Get("x") != nil {
		t.Fatal("expected nil after clear")
	}
}

func TestCache_ConcurrentAccess(t *testing.T) {
	c := NewCache(100)
	done := make(chan struct{})
	for i := 0; i < 10; i++ {
		go func(id int) {
			defer func() { <-done }()
			for j := 0; j < 50; j++ {
				key := string(rune('a' + id))
				c.Put(key, &Entry{Descriptor: &Descriptor{Name: key}})
				_ = c.Get(key)
			}
		}(i)
		done <- struct{}{}
	}
	for i := 0; i < 50; i++ {
		c.Put(string(rune('z'-i)), &Entry{Descriptor: &Descriptor{Name: "x"}})
	}
}

func TestAutoTuner_BestConfigAfterRecord(t *testing.T) {
	a := NewAutoTuner()
	a.Record("gemm", map[string]int{"tile": 32}, 10)
	a.Record("gemm", map[string]int{"tile": 64}, 5)
	cfg, ok := a.BestConfig("gemm")
	if !ok {
		t.Fatal("expected best config")
	}
	if cfg["tile"] != 64 {
		t.Fatalf("tile = %d, want 64", cfg["tile"])
	}
}

func TestAutoTuner_SuggestBest(t *testing.T) {
	a := NewAutoTuner()
	a.Record("conv", map[string]int{"block": 16}, 20)
	s := a.Suggest("conv")
	if s["block"] != 16 {
		t.Fatalf("suggest = %v, want block=16", s)
	}
}

func TestAutoTuner_SuggestDefault(t *testing.T) {
	a := NewAutoTuner()
	s := a.Suggest("unknown")
	if s["tile"] != 32 {
		t.Fatalf("default suggest = %v, want tile=32", s)
	}
}

func TestAutoTuner_BestConfigMissing(t *testing.T) {
	a := NewAutoTuner()
	if _, ok := a.BestConfig("none"); ok {
		t.Fatal("expected false for missing kernel")
	}
}

func TestAutoTuner_MultipleKernels(t *testing.T) {
	a := NewAutoTuner()
	a.Record("k1", map[string]int{"x": 1}, 5)
	a.Record("k2", map[string]int{"x": 2}, 3)
	cfg1, ok1 := a.BestConfig("k1")
	cfg2, ok2 := a.BestConfig("k2")
	if !ok1 || !ok2 {
		t.Fatal("expected both configs")
	}
	if cfg1["x"] != 1 || cfg2["x"] != 2 {
		t.Fatalf("configs = %v, %v", cfg1, cfg2)
	}
}

func TestDispatcher_DispatchExactMatch(t *testing.T) {
	reg := NewRegistry()
	desc := &Descriptor{Name: "add", Version: "1.0", Backends: []string{"cpu"}, Inputs: []TensorDesc{{}}, Outputs: []TensorDesc{{}}}
	impl := func() {}
	_ = reg.Register(desc, impl)
	d := NewDispatcher(reg)
	result, err := d.Dispatch("add", "1.0", "cpu")
	if err != nil {
		t.Fatalf("Dispatch: %v", err)
	}
	if result == nil {
		t.Fatal("expected non-nil result")
	}
}

func TestDispatcher_DispatchVersionMismatch(t *testing.T) {
	reg := NewRegistry()
	desc := &Descriptor{Name: "add", Version: "1.0", Backends: []string{"cpu"}, Inputs: []TensorDesc{{}}, Outputs: []TensorDesc{{}}}
	impl := "cpu_v1"
	_ = reg.Register(desc, impl)
	d := NewDispatcher(reg)
	// Version mismatch falls back to the latest entry that matches the backend.
	result, err := d.Dispatch("add", "2.0", "cpu")
	if err != nil {
		t.Fatalf("Dispatch fallback: %v", err)
	}
	if result != impl {
		t.Fatalf("fallback result = %v, want %s", result, impl)
	}
}
