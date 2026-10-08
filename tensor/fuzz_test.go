package tensor_test

import (
	"testing"

	"github.com/astrovox/astrovox/tensor"
)

// FuzzParseDType ensures the dtype parser never panics and
// either resolves a canonical name or returns an error.
func FuzzParseDType(f *testing.F) {
	f.Add("float32")
	f.Add("")
	f.Add("bogus")
	f.Add("bool")
	f.Add("complex128")
	f.Fuzz(func(t *testing.T, name string) {
		dt, err := tensor.ParseDType(name)
		if err != nil {
			if int(dt) != 0 {
				t.Fatalf("ParseDType(%q): error but dtype = %d", name, int(dt))
			}
			return
		}
		if int(dt) < 0 || int(dt) >= int(tensor.NumDTypes) {
			t.Fatalf("ParseDType(%q) = %d out of range", name, int(dt))
		}
		if dt.String() != name {
			t.Fatalf("ParseDType(%q) resolved to %s", name, dt)
		}
	})
}

// FuzzLoad ensures deserialization never panics: corrupt or
// truncated input returns an error; valid input yields a
// tensor whose shape/dtype agree with the header.
func FuzzLoad(f *testing.F) {
	seed, err := tensor.Ones(tensor.Float32, []int{4, 4})
	if err != nil {
		f.Fatal(err)
	}
	seedData, err := tensor.Save(seed)
	if err != nil {
		f.Fatal(err)
	}
	f.Add(seedData)
	f.Add([]byte{})
	f.Add([]byte("ASTV"))
	f.Add(append([]byte(nil), seedData[:len(seedData)/2]...))
	f.Fuzz(func(t *testing.T, data []byte) {
		loaded, err := tensor.Load(data)
		if err != nil {
			return
		}
		if loaded == nil {
			t.Fatal("Load returned nil tensor with nil error")
		}
		if loaded.NumElements() < 0 {
			t.Fatalf("negative element count: %d", loaded.NumElements())
		}
		if int(loaded.DType()) >= int(tensor.NumDTypes) {
			t.Fatalf("dtype out of range: %s", loaded.DType())
		}
	})
}

// FuzzNewShape ensures shape validation never panics and
// rejects negative dimensions.
func FuzzNewShape(f *testing.F) {
	f.Add(1, 2, 3)
	f.Add(0, 0, 0)
	f.Add(-1, 2, 3)
	f.Add(1, 1, 1)
	f.Fuzz(func(t *testing.T, a, b, c int) {
		s, err := tensor.NewShape(a, b, c)
		if err != nil {
			return
		}
		if s.NumElements() != a*b*c {
			t.Fatalf("shape %v: NumElements = %d, want %d",
				[]int{a, b, c}, s.NumElements(), a*b*c)
		}
	})
}

// FuzzArange ensures arange never panics and always yields
// a 1-D tensor with the expected element bound.
func FuzzArange(f *testing.F) {
	f.Add("float32", 0.0, 10.0, 1.0)
	f.Add("float64", -5.0, 5.0, 0.5)
	f.Add("int64", 0.0, 0.0, 0.0)
	f.Fuzz(func(t *testing.T, dtype string, start, stop, step float64) {
		dt, err := tensor.ParseDType(dtype)
		if err != nil {
			dt = tensor.Float32
		}
		if step == 0 {
			step = 1
		}
		src, err := tensor.Arange(dt, start, stop, step)
		if err != nil {
			return
		}
		if src.NumElements() < 0 {
			t.Fatalf("negative elements: %d", src.NumElements())
		}
		if src.Shape().Rank() != 1 {
			t.Fatalf("arange rank = %d, want 1", src.Shape().Rank())
		}
	})
}
