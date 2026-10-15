package inference_test

import (
	"context"
	"sync"
	"testing"
	"time"

	"github.com/astrovox/astrovox/inference"
	"github.com/astrovox/astrovox/internal/errors"
	"github.com/astrovox/astrovox/model"
	"github.com/astrovox/astrovox/tensor"
)

func registryModel(t *testing.T, in, out int) model.Module {
	t.Helper()
	m, err := model.NewMLP("mlp", []int{in, 4, out}, model.ActRelu, 42)
	if err != nil {
		t.Fatal(err)
	}
	return m
}

func TestRegistryRegisterAndRun(t *testing.T) {
	reg := inference.NewRegistry(2, inference.DefaultLimits)
	defer reg.Shutdown(2 * time.Second)
	m := registryModel(t, 2, 2)
	rm, err := reg.Register("demo", m)
	if err != nil {
		t.Fatalf("register: %v", err)
	}
	if rm.Version != 1 {
		t.Fatalf("first version = %d, want 1", rm.Version)
	}
	// Re-registration increments the version (model replacement).
	rm2, err := reg.Register("demo", registryModel(t, 2, 2))
	if err != nil {
		t.Fatalf("re-register: %v", err)
	}
	if rm2.Version != 2 {
		t.Fatalf("second version = %d, want 2", rm2.Version)
	}
	if got := reg.Versions("demo"); len(got) != 2 || got[0] != 1 || got[1] != 2 {
		t.Fatalf("versions = %v, want [1 2]", got)
	}

	// Run against the latest version through the registry.
	in, err := tensor.Zeros(tensor.Float64, []int{1, 2})
	if err != nil {
		t.Fatal(err)
	}
	res, err := reg.RunLatest(context.Background(), "demo", inference.Request{
		ID:     "r1",
		Inputs: map[string]*tensor.Tensor{inference.InputKey: in},
	})
	if err != nil {
		t.Fatalf("run latest: %v", err)
	}
	if res.Outputs[inference.OutputKey] == nil {
		t.Fatal("no output")
	}

	// Unknown model and version are typed errors.
	if _, err := reg.RunLatest(context.Background(), "nope", inference.Request{
		ID: "x", Inputs: map[string]*tensor.Tensor{inference.InputKey: in},
	}); !errors.IsCode(err, errors.CodeNotFound) {
		t.Fatalf("unknown model: %v, want NOT_FOUND", err)
	}
	if _, err := reg.Get("demo", 99); !errors.IsCode(err, errors.CodeNotFound) {
		t.Fatalf("unknown version: %v, want NOT_FOUND", err)
	}
	// Registration validation.
	if _, err := reg.Register("", m); !errors.IsCode(err, errors.CodeInvalidArgument) {
		t.Fatal("empty name accepted")
	}
	if _, err := reg.Register("nil", nil); !errors.IsCode(err, errors.CodeInvalidArgument) {
		t.Fatal("nil module accepted")
	}
}

func TestRegistryHealthAndUnload(t *testing.T) {
	reg := inference.NewRegistry(1, inference.DefaultLimits)
	defer reg.Shutdown(2 * time.Second)
	rm, err := reg.Register("m", registryModel(t, 2, 1))
	if err != nil {
		t.Fatal(err)
	}
	if !rm.IsLoaded() {
		t.Fatal("model should be loaded after registration")
	}
	h := rm.Health()
	if !h.Loaded || h.Name != "m" || h.Version != 1 {
		t.Fatalf("health = %+v", h)
	}
	// Unload drains and marks unloaded; a second unload is a no-op.
	if err := rm.Unload(2 * time.Second); err != nil {
		t.Fatalf("unload: %v", err)
	}
	if rm.IsLoaded() {
		t.Fatal("model still loaded after unload")
	}
	if err := rm.Unload(time.Second); err != nil {
		t.Fatalf("second unload: %v", err)
	}
	// Running an unloaded model fails with a cancelled executor, not a panic.
	in, _ := tensor.Zeros(tensor.Float64, []int{1, 2})
	if _, err := rm.Run(context.Background(), inference.Request{
		ID: "x", Inputs: map[string]*tensor.Tensor{inference.InputKey: in},
	}); !errors.IsCode(err, errors.CodeCancelled) {
		t.Fatalf("run on unloaded model: %v, want CANCELLED", err)
	}
	// Registry health lists every version.
	hs := reg.Health()
	if len(hs) != 1 || hs[0].Loaded {
		t.Fatalf("registry health = %+v", hs)
	}
}

// TestRegistryConcurrentRegistration hammers registration and run to
// prove the registry's lock discipline under load.
func TestRegistryConcurrentRegistration(t *testing.T) {
	reg := inference.NewRegistry(2, inference.DefaultLimits)
	defer reg.Shutdown(5 * time.Second)
	in, err := tensor.Zeros(tensor.Float64, []int{1, 2})
	if err != nil {
		t.Fatal(err)
	}
	var wg sync.WaitGroup
	errs := make(chan error, 64)
	for i := 0; i < 16; i++ {
		wg.Add(1)
		go func(i int) {
			defer wg.Done()
			rm, err := reg.Register("m", registryModel(t, 2, 1))
			if err != nil {
				errs <- err
				return
			}
			if rm.Version < 1 {
				errs <- errors.New(errors.CodeInternal, "bad version")
			}
			if _, err := rm.Run(context.Background(), inference.Request{
				ID: "c", Inputs: map[string]*tensor.Tensor{inference.InputKey: in},
			}); err != nil {
				errs <- err
			}
		}(i)
	}
	wg.Wait()
	close(errs)
	for err := range errs {
		t.Fatalf("concurrent registry use: %v", err)
	}
	if got := len(reg.Versions("m")); got != 16 {
		t.Fatalf("versions = %d, want 16", got)
	}
}
