package runtime

import (
	"context"
	"errors"
	"sync"
	"testing"
	"time"
)

func TestSchedulerSubmit(t *testing.T) {
	s := NewScheduler(2)
	defer s.Stop()

	var mu sync.Mutex
	called := false
	f, err := s.Submit(func() error {
		mu.Lock()
		called = true
		mu.Unlock()
		return nil
	})
	if err != nil {
		t.Fatalf("submit: %v", err)
	}
	if err := f.Wait(); err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	mu.Lock()
	defer mu.Unlock()
	if !called {
		t.Fatal("task was not called")
	}
}

func TestSchedulerSubmitMany(t *testing.T) {
	s := NewScheduler(2)
	defer s.Stop()

	var count int
	var mu sync.Mutex
	tasks := []Task{
		func() error { mu.Lock(); count++; mu.Unlock(); return nil },
		func() error { mu.Lock(); count++; mu.Unlock(); return nil },
		func() error { mu.Lock(); count++; mu.Unlock(); return nil },
	}
	futures, err := s.SubmitMany(tasks)
	if err != nil {
		t.Fatalf("submit many: %v", err)
	}
	if err := s.Wait(futures...); err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if count != 3 {
		t.Fatalf("expected 3 tasks, got %d", count)
	}
}

func TestSchedulerDone(t *testing.T) {
	s := NewScheduler(1)
	defer s.Stop()

	f, err := s.Submit(func() error { return nil })
	if err != nil {
		t.Fatalf("submit: %v", err)
	}
	time.Sleep(10 * time.Millisecond)
	if !f.Done() {
		t.Fatal("expected future to be done")
	}
}

func TestProfilerTime(t *testing.T) {
	p := NewProfiler()
	p.Time("op", func() {})
	metrics := p.Metrics()
	if _, ok := metrics["op"]; !ok {
		t.Fatal("expected 'op' metric")
	}
}

func TestTracerEvents(t *testing.T) {
	tr := NewTracer()
	span := tr.Start("test")
	span.SetMeta("key", "value")
	span.End(nil)
	events := tr.Events()
	if len(events) != 1 {
		t.Fatalf("expected 1 event, got %d", len(events))
	}
	if events[0].Name != "test" {
		t.Errorf("event name = %s, want test", events[0].Name)
	}
}

func TestCancellableTask(t *testing.T) {
	parent := context.Background()
	ct := NewCancellableTask(parent)
	if ct.IsCancelled() {
		t.Fatal("task should not be cancelled yet")
	}
	ct.Cancel()
	if !ct.IsCancelled() {
		t.Fatal("task should be cancelled")
	}
	if err := ct.CheckContext(); !errors.Is(err, ErrCancelled) {
		t.Fatalf("expected ErrCancelled, got %v", err)
	}
}
