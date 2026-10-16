package workflow

import (
	"context"
	"errors"
	"strings"
	"sync"
	"sync/atomic"
	"testing"
	"time"
)

// counterTask is a task that increments a counter when executed.
type counterTask struct {
	name string
	cnt  *int32
	fail *int32 // if set, fail this many times then succeed
}

func (ct *counterTask) Do(ctx context.Context) error {
	if ct.fail != nil {
		if n := atomic.AddInt32(ct.fail, 1); n <= *ct.fail {
			return errors.New("task not yet ready")
		}
	}
	atomic.AddInt32(ct.cnt, 1)
	return nil
}

func TestSequentialWorkflow(t *testing.T) {
	store := NewFileStore(t.TempDir())
	eng := NewEngine(store)

	order := make([]string, 0)
	var mu sync.Mutex

	def := &WorkflowDef{
		ID:   "seq",
		Name: "sequential",
		Tasks: map[string]*Task{
			"a": {ID: "a", Name: "A", Do: func(ctx context.Context) error {
				mu.Lock(); order = append(order, "a"); mu.Unlock(); return nil
			}},
			"b": {ID: "b", Name: "B", Deps: []string{"a"}, Do: func(ctx context.Context) error {
				mu.Lock(); order = append(order, "b"); mu.Unlock(); return nil
			}},
			"c": {ID: "c", Name: "C", Deps: []string{"b"}, Do: func(ctx context.Context) error {
				mu.Lock(); order = append(order, "c"); mu.Unlock(); return nil
			}},
		},
	}

	if err := eng.Run(context.Background(), def); err != nil {
		t.Fatalf("Run: %v", err)
	}

	expected := []string{"a", "b", "c"}
	mu.Lock()
	defer mu.Unlock()
	for i, v := range order {
		if v != expected[i] {
			t.Fatalf("order[%d] = %q, want %q", i, v, expected[i])
		}
	}

	// Verify all tasks are Succeeded.
	for id, ts := range eng.workflows[def.ID].tasks {
		if ts.state != Succeeded {
			t.Fatalf("task %s state = %v, want Succeeded", id, ts.state)
		}
	}
}

func TestDiamondWorkflow(t *testing.T) {
	store := NewFileStore(t.TempDir())
	eng := NewEngine(store)

	order := make([]string, 0)
	var mu sync.Mutex

	def := &WorkflowDef{
		ID:   "diamond",
		Name: "diamond",
		Tasks: map[string]*Task{
			"a": {ID: "a", Name: "A", Do: func(ctx context.Context) error {
				mu.Lock(); order = append(order, "a"); mu.Unlock(); return nil
			}},
			"b": {ID: "b", Name: "B", Deps: []string{"a"}, Do: func(ctx context.Context) error {
				mu.Lock(); order = append(order, "b"); mu.Unlock(); return nil
			}},
			"c": {ID: "c", Name: "C", Deps: []string{"a"}, Do: func(ctx context.Context) error {
				mu.Lock(); order = append(order, "c"); mu.Unlock(); return nil
			}},
			"d": {ID: "d", Name: "D", Deps: []string{"b", "c"}, Do: func(ctx context.Context) error {
				mu.Lock(); order = append(order, "d"); mu.Unlock(); return nil
			}},
		},
	}

	if err := eng.Run(context.Background(), def); err != nil {
		t.Fatalf("Run: %v", err)
	}

	mu.Lock()
	defer mu.Unlock()
	if order[0] != "a" {
		t.Fatalf("first = %q, want a", order[0])
	}
	if order[len(order)-1] != "d" {
		t.Fatalf("last = %q, want d", order[len(order)-1])
	}
	// b and c must both come before d.
	bIdx := -1
	cIdx := -1
	dIdx := -1
	for i, v := range order {
		switch v {
		case "b":
			bIdx = i
		case "c":
			cIdx = i
		case "d":
			dIdx = i
		}
	}
	if bIdx < 0 || cIdx < 0 || dIdx < 0 {
		t.Fatalf("missing tasks: order=%v", order)
	}
	if bIdx > dIdx || cIdx > dIdx {
		t.Fatalf("dependency violation: order=%v", order)
	}
}

func TestRetryOnFailure(t *testing.T) {
	store := NewFileStore(t.TempDir())
	eng := NewEngine(store)

	failCount := int32(0)
	def := &WorkflowDef{
		ID:   "retry",
		Name: "retry",
		Tasks: map[string]*Task{
			"flaky": {ID: "flaky", Name: "flaky", RetryPolicy: RetryPolicy{
				MaxAttempts:   3,
				InitialBackoff: 10 * time.Millisecond,
				MaxBackoff:    100 * time.Millisecond,
			}, Do: func(ctx context.Context) error {
				if atomic.AddInt32(&failCount, 1) < 3 {
					return errors.New("not yet")
				}
				return nil
			}},
		},
	}

	if err := eng.Run(context.Background(), def); err != nil {
		t.Fatalf("Run: %v", err)
	}
	if failCount != 3 {
		t.Fatalf("failCount = %d, want 3", failCount)
	}
}

func TestTaskFailureAfterMaxAttempts(t *testing.T) {
	store := NewFileStore(t.TempDir())
	eng := NewEngine(store)

	def := &WorkflowDef{
		ID:   "fail",
		Name: "fail",
		Tasks: map[string]*Task{
			"alwaysFail": {ID: "alwaysFail", Name: "alwaysFail", RetryPolicy: RetryPolicy{
				MaxAttempts:   2,
				InitialBackoff: 10 * time.Millisecond,
				MaxBackoff:    100 * time.Millisecond,
			}, Do: func(ctx context.Context) error {
				return errors.New("always fails")
			}},
		},
	}

	err := eng.Run(context.Background(), def)
	if err == nil {
		t.Fatal("expected error from failing task")
	}
	if !strings.Contains(err.Error(), "alwaysFail") {
		t.Fatalf("unexpected error: %v", err)
	}
}

func TestCancellation(t *testing.T) {
	store := NewFileStore(t.TempDir())
	eng := NewEngine(store)

	started := make(chan struct{})
	blocked := make(chan struct{})

	def := &WorkflowDef{
		ID:   "cancel",
		Name: "cancel",
		Tasks: map[string]*Task{
			"blocker": {ID: "blocker", Name: "blocker", Do: func(ctx context.Context) error {
				close(started)
				select {
				case <-blocked:
					return nil
				case <-ctx.Done():
					return ctx.Err()
				}
			}},
		},
	}

	ctx, cancel := context.WithCancel(context.Background())
	go func() {
		<-started
		time.Sleep(50 * time.Millisecond)
		cancel()
	}()

	err := eng.Run(ctx, def)
	if err == nil {
		t.Fatal("expected cancellation error")
	}
	if !errors.Is(err, context.Canceled) {
		t.Fatalf("err = %v, want context.Canceled", err)
	}
	close(blocked)
}

func TestIdempotencyKey(t *testing.T) {
	store := NewFileStore(t.TempDir())
	eng := NewEngine(store)

	execCount := int32(0)
	def := &WorkflowDef{
		ID:   "idem",
		Name: "idem",
		Tasks: map[string]*Task{
			"idemTask": {ID: "idemTask", Name: "idemTask", IdempotencyKey: "key-1", Do: func(ctx context.Context) error {
				atomic.AddInt32(&execCount, 1)
				return nil
			}},
		},
	}

	// First run.
	if err := eng.Run(context.Background(), def); err != nil {
		t.Fatalf("Run 1: %v", err)
	}
	if execCount != 1 {
		t.Fatalf("execCount after run 1 = %d, want 1", execCount)
	}

	// Second run with new engine but same store - idempotency should prevent re-execution.
	eng2 := NewEngine(store)
	if err := eng2.Run(context.Background(), def); err != nil {
		t.Fatalf("Run 2: %v", err)
	}
	if execCount != 1 {
		t.Fatalf("execCount after run 2 = %d, want 1 (idempotent)", execCount)
	}
}

func TestStorePersistence(t *testing.T) {
	dir := t.TempDir()
	store := NewFileStore(dir)

	snap := &StateSnapshot{
		Version:    1,
		WorkflowID: "wf-1",
		Tasks: map[string]*TaskStateRecord{
			"t1": {ID: "t1", State: Succeeded, Attempts: 1},
			"t2": {ID: "t2", State: Pending, Attempts: 0},
		},
	}

	if err := store.Save(snap); err != nil {
		t.Fatalf("Save: %v", err)
	}

	loaded, err := store.Load("wf-1")
	if err != nil {
		t.Fatalf("Load: %v", err)
	}
	if loaded == nil {
		t.Fatal("Load returned nil")
	}
	if loaded.WorkflowID != "wf-1" {
		t.Fatalf("WorkflowID = %q, want wf-1", loaded.WorkflowID)
	}
	if loaded.Tasks["t1"].State != Succeeded {
		t.Fatalf("t1 state = %v, want Succeeded", loaded.Tasks["t1"].State)
	}
	if loaded.Tasks["t2"].State != Pending {
		t.Fatalf("t2 state = %v, want Pending", loaded.Tasks["t2"].State)
	}

	// Non-existent workflow.
	loaded, err = store.Load("nonexistent")
	if err != nil {
		t.Fatalf("Load nonexistent: %v", err)
	}
	if loaded != nil {
		t.Fatalf("Load nonexistent = %+v, want nil", loaded)
	}
}
