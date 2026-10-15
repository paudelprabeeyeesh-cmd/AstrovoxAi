package stability

import (
	"errors"
	"sync"
	"sync/atomic"
	"testing"
	"time"

	"github.com/astrovox/astrovox/internal/backend"
	"github.com/astrovox/astrovox/internal/runtime"
)

const (
	// defaultCycles keeps the suite fast; long runs scale this up.
	defaultCycles = 200
	// errorsBudget is the failure ceiling observed while polling services.
	errorsBudget = 0
)

func cycles() int { return defaultCycles }

// TestSchedulerSustainedThroughput runs the scheduler under sustained load
// and verifies every task completes successfully.
func TestSchedulerSustainedThroughput(t *testing.T) {
	t.Parallel()
	sched := runtime.NewScheduler(4)
	defer sched.Stop()

	tasks := cycles()

	var done atomic.Int64
	futures := make([]runtime.Future, 0, tasks)
	// The bounded queue refuses overflow: drain accepted work and retry
	// rather than assuming unbounded admission.
	for submitted := 0; submitted < tasks; {
		f, err := sched.Submit(func() error {
			done.Add(1)
			return nil
		})
		if err != nil {
			if !errors.Is(err, runtime.ErrQueueFull) {
				t.Fatalf("submit %d: %v", submitted, err)
			}
			for _, w := range futures {
				if err := w.Wait(); err != nil {
					t.Fatalf("task failed: %v", err)
				}
			}
			futures = futures[:0]
			continue
		}
		futures = append(futures, f)
		submitted++
	}
	// A deliberately failing task proves the failure path also drains.
	failing, err := sched.Submit(func() error { return errors.New("boom") })
	if err != nil {
		t.Fatalf("submit failing task: %v", err)
	}

	if err := sched.Wait(futures...); err != nil {
		t.Errorf("successful tasks returned an error: %v", err)
	}
	if err := sched.Wait(failing); err == nil {
		t.Error("expected the failing task to report an error")
	}
	if int(done.Load()) != tasks {
		t.Errorf("completed %d tasks, want %d", done.Load(), tasks)
	}
}

// TestWorkStealingSchedulerDrains verifies the work-stealing scheduler
// completes every submitted task under contention.
func TestWorkStealingSchedulerDrains(t *testing.T) {
	t.Parallel()
	ws := runtime.NewWorkStealingScheduler(4)
	defer ws.Stop()

	var done atomic.Int64
	var wg sync.WaitGroup
	n := cycles()
	wg.Add(n)
	for i := 0; i < n; i++ {
		ws.SubmitToWorker(i%4, func() error {
			defer wg.Done()
			done.Add(1)
			return nil
		})
	}
	wg.Wait()
	if done.Load() != int64(n) {
		t.Errorf("completed %d, want %d", done.Load(), n)
	}
}

// TestPrioritySchedulerAcceptsUrgentWork verifies the priority path runs.
func TestPrioritySchedulerAcceptsUrgentWork(t *testing.T) {
	t.Parallel()
	ps := runtime.NewPriorityScheduler(2)
	defer ps.Stop()

	var ran atomic.Bool
	if fut := ps.SubmitHighPriority(func() error { ran.Store(true); return nil }); fut == nil {
		t.Fatal("expected a future")
	}
	deadline := time.Now().Add(2 * time.Second)
	for !ran.Load() && time.Now().Before(deadline) {
		time.Sleep(time.Millisecond)
	}
	if !ran.Load() {
		t.Error("high-priority task did not run")
	}
}

// TestSchedulerStopIsIdempotent verifies shutdown is safe to call twice.
func TestSchedulerStopIsIdempotent(t *testing.T) {
	t.Parallel()
	sched := runtime.NewScheduler(2)
	var futures []runtime.Future
	for i := 0; i < 10; i++ {
		f, err := sched.Submit(func() error { return nil })
		if err != nil {
			// Drain and retry: the queue is bounded.
			for _, w := range futures {
				w.Wait()
			}
			futures = nil
			if f, err = sched.Submit(func() error { return nil }); err != nil {
				t.Fatalf("submit %d after drain: %v", i, err)
			}
		}
		futures = append(futures, f)
	}
	for _, f := range futures {
		if err := f.Wait(); err != nil {
			t.Fatalf("task: %v", err)
		}
	}
	time.Sleep(5 * time.Millisecond)
	sched.Stop()
	sched.Stop() // must not panic or deadlock
}

// TestConcurrentBackendStress hammers a backend concurrently and checks
// results stay correct under contention.
func TestConcurrentBackendStress(t *testing.T) {
	t.Parallel()
	cpu := backend.NewCPUBackend()
	a := []float64{1, 2, 3, 4}
	b := []float64{5, 6, 7, 8}
	want := []float64{19, 22, 43, 50}

	var wg sync.WaitGroup
	for worker := 0; worker < 8; worker++ {
		wg.Add(1)
		go func() {
			defer wg.Done()
			for i := 0; i < cycles(); i++ {
				got, err := cpu.MatMul(a, b, 2, 2, 2)
				if err != nil {
					t.Errorf("matmul: %v", err)
					return
				}
				for j := range want {
					if got[j] != want[j] {
						t.Errorf("iteration %d: element %d = %f, want %f", i, j, got[j], want[j])
						return
					}
				}
			}
		}()
	}
	wg.Wait()
}

// TestSustainedMixedLoad reports zero unexpected failures across ops.
func TestSustainedMixedLoad(t *testing.T) {
	t.Parallel()
	var failures atomic.Int64
	cpu := backend.NewCPUBackend()
	var wg sync.WaitGroup
	for worker := 0; worker < 4; worker++ {
		wg.Add(1)
		go func() {
			defer wg.Done()
			for i := 0; i < cycles(); i++ {
				if _, err := cpu.MatMul([]float64{1, 2, 3, 4}, []float64{5, 6, 7, 8}, 2, 2, 2); err != nil {
					failures.Add(1)
				}
				if _, err := cpu.Softmax([]float64{1, 2, 3}, 0); err != nil {
					failures.Add(1)
				}
				if _, err := cpu.Add([]float64{1}, []float64{2}); err != nil {
					failures.Add(1)
				}
			}
		}()
	}
	wg.Wait()
	if f := failures.Load(); f != errorsBudget {
		t.Errorf("observed %d unexpected failures (budget %d)", f, errorsBudget)
	}
}

// TestRepeatedStartStopCycles exercises lifecycle stability.
func TestRepeatedStartStopCycles(t *testing.T) {
	t.Parallel()
	for round := 0; round < 20; round++ {
		sched := runtime.NewScheduler(2)
		futs := make([]runtime.Future, 0, 20)
		for i := 0; i < 20; i++ {
			f, err := sched.Submit(func() error { return nil })
			if err != nil {
				if !errors.Is(err, runtime.ErrQueueFull) {
					t.Fatalf("round %d submit %d: %v", round, i, err)
				}
				for _, w := range futs {
					if err := w.Wait(); err != nil {
						t.Fatalf("round %d: %v", round, err)
					}
				}
				futs = futs[:0]
				i-- // retry this slot
				continue
			}
			futs = append(futs, f)
		}
		_ = sched.Wait(futs...)
		sched.Stop()
	}
}
