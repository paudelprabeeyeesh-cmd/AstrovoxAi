package runtime_test

import (
	"testing"
	"time"

	"github.com/astrovox/astrovox/internal/runtime"
)

func TestRuntimeSchedulerSubmit(t *testing.T) {
	s := runtime.NewScheduler(1)
	defer s.Stop()
	f := s.Submit(func() error { return nil })
	if err := f.Wait(); err != nil {
		t.Fatalf("future failed: %v", err)
	}
}

func TestRuntimeSchedulerWaitError(t *testing.T) {
	s := runtime.NewScheduler(1)
	defer s.Stop()
	expectedErr := runtime.ErrCancelled
	f := s.Submit(func() error { return expectedErr })
	if err := f.Wait(); err != expectedErr {
		t.Fatalf("expected ErrCancelled, got %v", err)
	}
}

func TestRuntimeSchedulerDoneAfterWait(t *testing.T) {
	s := runtime.NewScheduler(1)
	defer s.Stop()
	f := s.Submit(func() error { return nil })
	f.Wait()
	if !f.Done() {
		t.Fatal("expected future to be done after wait")
	}
}

func TestRuntimeProfilerMultipleMetrics(t *testing.T) {
	p := runtime.NewProfiler()
	p.Time("op1", func() {})
	p.Time("op2", func() {})
	metrics := p.Metrics()
	if len(metrics) != 2 {
		t.Fatalf("expected 2 metrics, got %d", len(metrics))
	}
}

func TestRuntimeProfilerAccumulatesTime(t *testing.T) {
	p := runtime.NewProfiler()
	p.Time("op", func() { time.Sleep(1 * time.Millisecond) })
	p.Time("op", func() { time.Sleep(1 * time.Millisecond) })
	metrics := p.Metrics()
	if metrics["op"] < 2*time.Millisecond {
		t.Fatalf("expected at least 2ms, got %v", metrics["op"])
	}
}

func TestRuntimeTracerMultipleSpans(t *testing.T) {
	tr := runtime.NewTracer()
	s1 := tr.Start("span1")
	s2 := tr.Start("span2")
	s1.End(10)
	s2.End(20)
	events := tr.Events()
	if len(events) != 2 {
		t.Fatalf("expected 2 events, got %d", len(events))
	}
}

func TestRuntimeSubmitMany(t *testing.T) {
	s := runtime.NewScheduler(2)
	defer s.Stop()
	tasks := []runtime.Task{func() error { return nil }, func() error { return nil }}
	futures := s.SubmitMany(tasks)
	if len(futures) != 2 {
		t.Fatalf("expected 2 futures, got %d", len(futures))
	}
}

func TestRuntimeWaitMultiple(t *testing.T) {
	s := runtime.NewScheduler(2)
	defer s.Stop()
	f1 := s.Submit(func() error { return nil })
	f2 := s.Submit(func() error { return nil })
	if err := s.Wait(f1, f2); err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
}

func TestRuntimeFutureWaitMultiple(t *testing.T) {
	s := runtime.NewScheduler(2)
	defer s.Stop()
	f1 := s.Submit(func() error { return nil })
	f2 := s.Submit(func() error { return nil })
	if err := s.Wait(f1, f2); err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if !f1.Done() || !f2.Done() {
		t.Fatal("expected both futures to be done")
	}
}

func TestRuntimeProfilerMetricsConcurrent(t *testing.T) {
	p := runtime.NewProfiler()
	var wg sync.WaitGroup
	for i := 0; i < 10; i++ {
		wg.Add(1)
		go func(i int) {
			defer wg.Done()
			p.Time("op", func() {})
		}(i)
	}
	wg.Wait()
}
