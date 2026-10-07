package kernel

import "testing"

func TestParseVersion(t *testing.T) {
	v, err := ParseVersion("1.2.3")
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if v.Major != 1 || v.Minor != 2 || v.Patch != 3 {
		t.Errorf("version = %v, want 1.2.3", v)
	}
}

func TestVersionLess(t *testing.T) {
	v1, _ := ParseVersion("1.0.0")
	v2, _ := ParseVersion("1.0.1")
	if !v1.Less(v2) {
		t.Error("1.0.0 should be less than 1.0.1")
	}
}

func TestVersionString(t *testing.T) {
	v, _ := ParseVersion("2.0.1")
	if v.String() != "2.0.1" {
		t.Errorf("string = %s, want 2.0.1", v.String())
	}
}

func TestDescriptor_Validate(t *testing.T) {
	d := &Descriptor{
		Name:     "matmul",
		Inputs:   []TensorDesc{{Name: "a"}},
		Outputs:  []TensorDesc{{Name: "c"}},
	}
	if err := d.Validate(); err != nil {
		t.Errorf("unexpected error: %v", err)
	}

	d.Name = ""
	if err := d.Validate(); err == nil {
		t.Error("empty name should fail validation")
	}
}

func TestRegistry_Register(t *testing.T) {
	r := NewRegistry()
	desc := &Descriptor{
		Name:    "relu",
		Version: "1.0.0",
		Inputs:  []TensorDesc{{Name: "x"}},
		Outputs: []TensorDesc{{Name: "y"}},
	}
	if err := r.Register(desc, func() {}); err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	entries := r.Lookup("relu")
	if len(entries) != 1 {
		t.Errorf("got %d entries, want 1", len(entries))
	}
}

func TestRegistry_Duplicate(t *testing.T) {
	r := NewRegistry()
	desc := &Descriptor{Name: "add", Version: "1.0.0", Inputs: []TensorDesc{{Name: "a"}}, Outputs: []TensorDesc{{Name: "c"}}}
	r.Register(desc, nil)
	err := r.Register(desc, nil)
	if err == nil {
		t.Error("duplicate should fail")
	}
}

func TestRegistry_List(t *testing.T) {
	r := NewRegistry()
	r.Register(&Descriptor{Name: "a", Version: "1.0.0", Inputs: []TensorDesc{{Name: "x"}}, Outputs: []TensorDesc{{Name: "y"}}}, nil)
	r.Register(&Descriptor{Name: "b", Version: "1.0.0", Inputs: []TensorDesc{{Name: "x"}}, Outputs: []TensorDesc{{Name: "y"}}}, nil)
	list := r.List()
	if len(list) != 2 {
		t.Errorf("list len = %d, want 2", len(list))
	}
}

func TestDispatcher_Dispatch(t *testing.T) {
	r := NewRegistry()
	r.Register(&Descriptor{
		Name: "matmul", Version: "1.0.0",
		Inputs: []TensorDesc{{Name: "a"}}, Outputs: []TensorDesc{{Name: "c"}},
		Backends: []string{"cpu"},
	}, "impl_cpu")

	d := NewDispatcher(r)
	result, err := d.Dispatch("matmul", "1.0.0", "cpu")
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if result != "impl_cpu" {
		t.Errorf("result = %v, want impl_cpu", result)
	}
}

func TestDispatcher_NotFound(t *testing.T) {
	r := NewRegistry()
	d := NewDispatcher(r)
	_, err := d.Dispatch("missing", "1.0.0", "cpu")
	if err == nil {
		t.Error("expected error for missing kernel")
	}
}

func TestSelector_Select_ExactMatch(t *testing.T) {
	r := NewRegistry()
	r.Register(&Descriptor{
		Name: "add", Version: "1.0.0",
		Inputs: []TensorDesc{{Name: "a"}}, Outputs: []TensorDesc{{Name: "c"}},
		Backends: []string{"cpu"},
	}, "impl1")
	r.Register(&Descriptor{
		Name: "add", Version: "2.0.0",
		Inputs: []TensorDesc{{Name: "a"}}, Outputs: []TensorDesc{{Name: "c"}},
		Backends: []string{"gpu"},
	}, "impl2")

	sel := NewSelector(r)
	entries := r.Lookup("add")
	entry := sel.Select(entries, "1.0.0", "cpu")
	if entry.Descriptor.Version != "1.0.0" {
		t.Errorf("selected version = %s, want 1.0.0", entry.Descriptor.Version)
	}
}

func TestCache_PutGet(t *testing.T) {
	c := NewCache(10)
	entry := &Entry{Descriptor: &Descriptor{Name: "x"}}
	c.Put("key1", entry)

	got := c.Get("key1")
	if got != entry {
		t.Error("cache miss")
	}
}

func TestCache_Eviction(t *testing.T) {
	c := NewCache(2)
	c.Put("1", &Entry{Descriptor: &Descriptor{Name: "a"}})
	c.Put("2", &Entry{Descriptor: &Descriptor{Name: "b"}})
	c.Put("3", &Entry{Descriptor: &Descriptor{Name: "c"}})

	if c.Size() > 2 {
		t.Errorf("cache size = %d, want <= 2", c.Size())
	}
}

func TestCache_Clear(t *testing.T) {
	c := NewCache(10)
	c.Put("x", &Entry{Descriptor: &Descriptor{Name: "x"}})
	c.Clear()
	if c.Size() != 0 {
		t.Error("cache should be empty")
	}
}

func TestAutoTuner_Record(t *testing.T) {
	a := NewAutoTuner()
	a.Record("matmul", map[string]int{"tile": 32}, 10)
	a.Record("matmul", map[string]int{"tile": 64}, 5)

	cfg, ok := a.BestConfig("matmul")
	if !ok {
		t.Fatal("expected best config")
	}
	if cfg["tile"] != 64 {
		t.Errorf("best config tile = %d, want 64", cfg["tile"])
	}
}

func TestAutoTuner_Suggest(t *testing.T) {
	a := NewAutoTuner()
	a.Record("add", map[string]int{"tile": 16}, 8)

	suggested := a.Suggest("add")
	if suggested["tile"] != 16 {
		t.Errorf("suggested tile = %d, want 16", suggested["tile"])
	}
}
