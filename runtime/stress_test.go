package runtime_test

import (
	"context"
	"sync"
	"testing"

	"github.com/astrovox/astrovox/runtime"
	"github.com/astrovox/astrovox/tensor"
)

func stressTask() runtime.Task {
	return func(ctx context.Context) ([]*tensor.Tensor, error) {
		t, err := tensor.Zeros(tensor.Float32, []int{4, 4})
		if err != nil {
			return nil, err
		}
		return []*tensor.Tensor{t}, nil
	}
}

// TestStress_HighConcurrency submits 10k tasks from
// 10k goroutines through a 4-worker engine.
func TestStress_HighConcurrency(t *testing.T) {
	e := runtime.NewEngine(4)
	ctx := context.Background()
	task := stressTask()
	const goroutines = 10_000
	var wg sync.WaitGroup
	errs := make(chan error, goroutines)
	start := make(chan struct{})
	for g := 0; g < goroutines; g++ {
		wg.Add(1)
		go func() {
			defer wg.Done()
			<-start
			f := e.Submit(ctx, task)
			if _, err := f.Wait(); err != nil {
				errs <- err
			}
		}()
	}
	close(start)
	wg.Wait()
	close(errs)
	for err := range errs {
		t.Fatalf("task failed: %v", err)
	}
}

// TestStress_ThreadPoolSaturation saturates the engine
// with more queued tasks than workers and verifies all
// complete.
func TestStress_ThreadPoolSaturation(t *testing.T) {
	e := runtime.NewEngine(2)
	ctx := context.Background()
	task := stressTask()
	const tasks = 5_000
	futures := make([]runtime.Future, tasks)
	for i := range futures {
		futures[i] = e.Submit(ctx, task)
	}
	for i, f := range futures {
		if _, err := f.Wait(); err != nil {
			t.Fatalf("task %d: %v", i, err)
		}
	}
}

// TestStress_SessionManySteps runs a session with a
// deep graph under load.
func TestStress_SessionManySteps(t *testing.T) {
	g := graphChain(t, 500)
	s, err := runtime.NewSession(g)
	if err != nil {
		t.Fatal(err)
	}
	input, err := tensor.Ones(tensor.Float32, []int{8, 8})
	if err != nil {
		t.Fatal(err)
	}
	ctx := context.Background()
	for i := 0; i < 100; i++ {
		if _, err := s.Run(ctx, []*tensor.Tensor{input}); err != nil {
			t.Fatalf("run %d: %v", i, err)
		}
	}
}

// TestStress_RepeatedSubmit allocates and completes
// 100k tasks sequentially to detect leaks via
// bounded growth (no crash, all succeed).
func TestStress_RepeatedSubmit(t *testing.T) {
	e := runtime.NewEngine(2)
	ctx := context.Background()
	task := stressTask()
	const tasks = 100_000
	for i := 0; i < tasks; i++ {
		f := e.Submit(ctx, task)
		if _, err := f.Wait(); err != nil {
			t.Fatalf("task %d: %v", i, err)
		}
	}
}
