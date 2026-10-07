package runtime

import (
	"context"
	"errors"
	"sync"
	"testing"
	"time"
)

func TestSchedulerSubmitMultiple(t *testing.T) {
	s := NewScheduler(2)
	defer s.Stop()

	var mu sync.Mutex
	results := make([]int, 0)
	tasks := []Task{
		func() error { mu.Lock(); results = append(results, 1); mu.Unlock(); return nil },
		func() error { mu.Lock(); results = append(results, 2); mu.Unlock(); return nil },
		func() error { mu.Lock(); results = append(results, 3); mu.Unlock(); return nil },
	}
	futures := s.SubmitMany(tasks)
	if err := s.Wait(futures...); err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if len(results) != 3 {
		t.Fatalf("expected 3 results, got %d", len(results))
	}
}

func TestSchedulerWaitError(t *testing.T) {
	s := NewScheduler(1)
	defer s.Stop()

	expectedErr := ErrCancelled
	f := s.Submit(func() error { return expectedErr })
	if err := f.Wait(); err != expectedErr {
		t.Fatalf("expected ErrCancelled, got %v", err)
	}
}

func TestSchedulerDoneAfterWait(t *testing.T) {
	s := NewScheduler(1)
	defer s.Stop()

	f := s.Submit(func() error { return nil })
	f.Wait()
	if !f.Done() {
		t.Fatal("expected future to be done after wait")
	}
}

func TestProfilerMultipleMetrics(t *testing.T) {
	p := NewProfiler()
	p.Time("op1", func() {})
	p.Time("op2", func() {})
	metrics := p.Metrics()
	if len(metrics) != 2 {
		t.Fatalf("expected 2 metrics, got %d", len(metrics))
	}
	if _, ok := metrics["op1"]; !ok {
		t.Fatal("expected 'op1' metric")
	}
	if _, ok := metrics["op2"]; !ok {
		t.Fatal("expected 'op2' metric")
	}
}

func TestProfilerAccumulatesTime(t *testing.T) {
	p := NewProfiler()
	p.Time("op", func() { time.Sleep(1 * time.Millisecond) })
	p.Time("op", func() { time.Sleep(1 * time.Millisecond) })
	metrics := p.Metrics()
	if metrics["op"] < 2*time.Millisecond {
		t.Fatalf("expected at least 2ms, got %v", metrics["op"])
	}
}

func TestTracerMultipleSpans(t *testing.T) {
	tr := NewTracer()
	s1 := tr.Start("span1")
	s2 := tr.Start("span2")
	s1.End(nil)
	s2.End(nil)
	events := tr.Events()
	if len(events) != 2 {
		t.Fatalf("expected 2 events, got %d", len(events))
	}
}

func TestTracerSpanMeta(t *testing.T) {
	tr := NewTracer()
	span := tr.Start("op")
	span.SetMeta("key", "value")
	span.End(nil)
	events := tr.Events()
	if events[0].Meta["key"] != "value" {
		t.Fatalf("expected meta 'key' = 'value', got %v", events[0].Meta)
	}
}

func TestTracerSpanError(t *testing.T) {
	tr := NewTracer()
	span := tr.Start("op")
	expectedErr := context.DeadlineExceeded
	span.End(expectedErr)
	events := tr.Events()
	if events[0].Error != expectedErr {
		t.Fatalf("expected error %v, got %v", expectedErr, events[0].Error)
	}
}

func TestCancellableTaskNotCancelled(t *testing.T) {
	parent := context.Background()
	ct := NewCancellableTask(parent)
	if ct.IsCancelled() {
		t.Fatal("task should not be cancelled")
	}
	if err := ct.CheckContext(); err != nil {
		t.Fatalf("expected no error, got %v", err)
	}
}

func TestCancellableTaskCancelled(t *testing.T) {
	parent := context.Background()
	ct := NewCancellableTask(parent)
	ct.Cancel()
	if !ct.IsCancelled() {
		t.Fatal("task should be cancelled")
	}
	if err := ct.CheckContext(); !errors.Is(err, ErrCancelled) {
		t.Fatalf("expected ErrCancelled, got %v", err)
	}
}

func TestCancellableTaskContext(t *testing.T) {
	parent := context.Background()
	ct := NewCancellableTask(parent)
	if ct.Context() == nil {
		t.Fatal("expected non-nil context")
	}
}

func TestSchedulerWorkerCount(t *testing.T) {
	s := NewScheduler(4)
	defer s.Stop()
	if s.workers != 4 {
		t.Fatalf("expected 4 workers, got %d", s.workers)
	}
}

func TestSchedulerDefaultWorkers(t *testing.T) {
	s := NewScheduler(0)
	defer s.Stop()
	if s.workers <= 0 {
		t.Fatalf("expected positive workers, got %d", s.workers)
	}
}

func TestFutureWaitMultiple(t *testing.T) {
	s := NewScheduler(2)
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

func TestProfilerMetricsConcurrent(t *testing.T) {
	p := NewProfiler()
	var wg sync.WaitGroup
	for i := 0; i < 10; i++ {
		wg.Add(1)
		go func(i int) {
			defer wg.Done()
			p.Time("concurrent", func() {})
		}(i)
	}
	wg.Wait()
	metrics := p.Metrics()
	if _, ok := metrics["concurrent"]; !ok {
		t.Fatal("expected 'concurrent' metric")
	}
}

func TestTracerEmptyEvents(t *testing.T) {
	tr := NewTracer()
	events := tr.Events()
	if len(events) != 0 {
		t.Fatalf("expected 0 events, got %d", len(events))
	}
}

func TestCancellableTaskWithParent(t *testing.T) {
	parent, cancel := context.WithCancel(context.Background())
	defer cancel()
	ct := NewCancellableTask(parent)
	if ct.IsCancelled() {
		t.Fatal("task should not be cancelled yet")
	}
}

func TestSchedulerSubmitError(t *testing.T) {
	s := NewScheduler(1)
	defer s.Stop()

	expectedErr := context.DeadlineExceeded
	f := s.Submit(func() error { return expectedErr })
	if err := f.Wait(); err != expectedErr {
		t.Fatalf("expected %v, got %v", expectedErr, err)
	}
}
