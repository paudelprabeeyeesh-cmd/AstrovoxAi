package runtime_test

import (
	"context"
	"sync"
	"sync/atomic"
	"testing"

	"github.com/astrovox/astrovox/internal/errors"
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
// 10k goroutines through a 4-worker engine. The bounded
// queue refuses overflow instead of blocking forever, so
// every accepted task must complete and every refusal
// must be the typed backpressure error: no panic, no
// silent acceptance, no stranded future.
func TestStress_HighConcurrency(t *testing.T) {
	e := runtime.NewEngine(4)
	ctx := context.Background()
	task := stressTask()
	const goroutines = 10_000
	var wg sync.WaitGroup
	errs := make(chan error, goroutines)
	var accepted, refused atomic.Int64
	start := make(chan struct{})
	for g := 0; g < goroutines; g++ {
		wg.Add(1)
		go func() {
			defer wg.Done()
			<-start
			f, err := e.Submit(ctx, task)
			if err != nil {
				// Refusal must be the typed backpressure error.
				if !errors.IsCode(err, errors.CodeQueueFull) {
					errs <- err
				}
				refused.Add(1)
				return
			}
			accepted.Add(1)
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
	if accepted.Load() == 0 {
		t.Fatal("no task was accepted")
	}
}

// TestStress_ThreadPoolSaturation drives 5000 tasks
// through a 2-worker engine, respecting backpressure: when
// the bounded queue refuses, the test drains accepted work
// and retries instead of assuming unbounded queueing.
func TestStress_ThreadPoolSaturation(t *testing.T) {
	e := runtime.NewEngine(2)
	ctx := context.Background()
	task := stressTask()
	const tasks = 5_000
	var pending []runtime.Future
	for done := 0; done < tasks; {
		// Fill the bounded queue, then drain everything and repeat.
		for done < tasks {
			f, err := e.Submit(ctx, task)
			if err != nil {
				if !errors.IsCode(err, errors.CodeQueueFull) {
					t.Fatalf("submit %d: unexpected error %v", done, err)
				}
				break
			}
			pending = append(pending, f)
			done++
		}
		for _, f := range pending {
			if _, err := f.Wait(); err != nil {
				t.Fatalf("task failed: %v", err)
			}
		}
		pending = pending[:0]
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
		f, err := e.Submit(ctx, task)
		if err != nil {
			t.Fatalf("submit %d: %v", i, err)
		}
		if _, err := f.Wait(); err != nil {
			t.Fatalf("task %d: %v", i, err)
		}
	}
}

// TestStress_SubmitAfterStopIsRefused verifies that
// submitting to a stopped engine returns the typed
// stopped error instead of panicking on a closed queue.
func TestStress_SubmitAfterStopIsRefused(t *testing.T) {
	e := runtime.NewEngine(1)
	e.Stop()
	if _, err := e.Submit(context.Background(), stressTask()); !errors.IsCode(err, errors.CodeCancelled) {
		t.Fatalf("submit after stop: %v, want a CodeCancelled error", err)
	}
	// A second Stop must not panic (channel close guard).
	e.Stop()
}
