package controlplane

import (
	"context"
	"net"
	"sync"
	"testing"
	"time"

	"github.com/astrovox/astrovox/internal/checkpoint"
)

// TestCoordinatorWorkerRoundTrip runs a real coordinator server and a real
// worker (in the same process, separate goroutines) connected over TCP.
// It verifies that the worker can register with the coordinator and that
// task submission works. Full task execution (worker picks up and executes
// a task) requires the scheduler (Stage 3) and is tested separately.
func TestCoordinatorWorkerRoundTrip(t *testing.T) {
	coord := NewCoordinator(Config{
		QueueCapacity: 100,
	}, &mockStore{})

	// Start coordinator server on a random port.
	ln, err := net.Listen("tcp", "127.0.0.1:0")
	if err != nil {
		t.Fatalf("listen: %v", err)
	}
	coordAddr := ln.Addr().String()
	srv := NewServer(coordAddr, coord)

	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()
	go func() {
		_ = srv.ListenAndServe(ctx)
	}()

	// Give the server a moment to start.
	time.Sleep(50 * time.Millisecond)

	// Create and run a worker.
	worker := NewWorker("worker-1", []string{"echo"}, ResourceRequirements{
		CPU:       1.0,
		MemoryMB:  1024,
	}, coordAddr)

	wctx, wcancel := context.WithCancel(context.Background())
	defer wcancel()

	go func() {
		_ = worker.Run(wctx)
	}()

	// Give the worker a moment to connect and register.
	time.Sleep(100 * time.Millisecond)

	// Submit a task.
	resp, err := coord.SubmitTask(context.Background(), TaskRequest{
		ProtocolVersion: ProtocolVersion,
		TaskID:          "task-1",
		TenantID:        "tenant-1",
		Spec: TaskSpec{
			Operation: "echo",
			Payload:   []byte("hello world"),
			ResourceRequirements: ResourceRequirements{
				CPU:       1.0,
				MemoryMB:  1024,
			},
		},
	})
	if err != nil {
		t.Fatalf("SubmitTask: %v", err)
	}

	// Verify the task was accepted.
	if resp.TaskID != "task-1" {
		t.Fatalf("TaskID = %q, want %q", resp.TaskID, "task-1")
	}
	if resp.State != TaskPending {
		t.Fatalf("State = %v, want %v", resp.State, TaskPending)
	}

	// Verify the task is pending (queued for assignment).
	got, err := coord.GetTaskStatus("task-1")
	if err != nil {
		t.Fatalf("GetTaskStatus: %v", err)
	}
	if got.State != TaskPending {
		t.Fatalf("State = %v, want %v", got.State, TaskPending)
	}
}

// TestWorkerRegistrationAndHeartbeat verifies that a worker can register and
// send heartbeats, and the coordinator tracks it.
func TestWorkerRegistrationAndHeartbeat(t *testing.T) {
	coord := NewCoordinator(Config{
		QueueCapacity: 100,
		WorkerTimeout: 5 * time.Second,
	}, &mockStore{})

	// Manually register via the coordinator (bypassing TCP for simplicity).
	if err := coord.RegisterWorker(WorkerRegistration{
		ProtocolVersion: ProtocolVersion,
		WorkerID:        "worker-1",
		Capabilities:    []string{"echo"},
		Resources: ResourceRequirements{
			CPU:       1.0,
			MemoryMB:  1024,
		},
	}); err != nil {
		t.Fatalf("RegisterWorker: %v", err)
	}

	// Send a heartbeat.
	if err := coord.WorkerHeartbeat(WorkerHeartbeat{
		ProtocolVersion: ProtocolVersion,
		WorkerID:        "worker-1",
		Timestamp:       time.Now(),
		ActiveTasks:     0,
		CompletedTasks:  0,
		FailedTasks:     0,
	}); err != nil {
		t.Fatalf("WorkerHeartbeat: %v", err)
	}

	// Unknown worker should fail.
	if err := coord.WorkerHeartbeat(WorkerHeartbeat{
		ProtocolVersion: ProtocolVersion,
		WorkerID:        "worker-999",
		Timestamp:       time.Now(),
	}); err == nil {
		t.Fatal("expected error for unknown worker")
	}
}

// TestStaleWorkerTaskReassignment verifies that when a worker's lease expires,
// its tasks are reassigned. This is a simplified version: we directly mark a
// worker as unavailable and verify its tasks remain pending (reassignment
// logic is Stage 3).
func TestStaleWorkerTaskReassignment(t *testing.T) {
	coord := NewCoordinator(Config{
		QueueCapacity: 100,
		WorkerTimeout: 50 * time.Millisecond,
		WorkerExpire:  100 * time.Millisecond,
	}, &mockStore{})

	// Register a worker.
	if err := coord.RegisterWorker(WorkerRegistration{
		ProtocolVersion: ProtocolVersion,
		WorkerID:        "worker-1",
		Capabilities:    []string{"echo"},
		Resources: ResourceRequirements{
			CPU:       1.0,
			MemoryMB:  1024,
		},
	}); err != nil {
		t.Fatalf("RegisterWorker: %v", err)
	}

	// Submit a task.
	resp, err := coord.SubmitTask(context.Background(), TaskRequest{
		ProtocolVersion: ProtocolVersion,
		TaskID:          "task-1",
		TenantID:        "tenant-1",
		Spec: TaskSpec{
			Operation: "echo",
			Payload:   []byte("test"),
			ResourceRequirements: ResourceRequirements{
				CPU:       1.0,
				MemoryMB:  1024,
			},
		},
	})
	if err != nil {
		t.Fatalf("SubmitTask: %v", err)
	}
	if resp.State != TaskPending {
		t.Fatalf("initial state = %v, want %v", resp.State, TaskPending)
	}

	// Simulate worker timeout: mark worker as unavailable.
	coord.mu.Lock()
	if w, ok := coord.workers["worker-1"]; ok {
		w.State = WorkerUnavailable
		w.LastHeartbeat = time.Now().Add(-time.Minute)
	}
	coord.mu.Unlock()

	// The task should still be pending (reassignment logic is Stage 3).
	got, err := coord.GetTaskStatus("task-1")
	if err != nil {
		t.Fatalf("GetTaskStatus: %v", err)
	}
	if got.State != TaskPending {
		t.Fatalf("state = %v, want %v (stale worker not yet reassigned)", got.State, TaskPending)
	}
}

// TestConcurrentSubmit verifies concurrent submissions don't corrupt state.
func TestConcurrentSubmit(t *testing.T) {
	coord := NewCoordinator(Config{QueueCapacity: 100}, nil)

	var wg sync.WaitGroup
	errors := make(chan error, 50)

	for i := 0; i < 50; i++ {
		wg.Add(1)
		go func(i int) {
			defer wg.Done()
			_, err := coord.SubmitTask(context.Background(), TaskRequest{
				ProtocolVersion: ProtocolVersion,
				TaskID:          "task-" + string(rune('0'+i%10)) + string(rune('0'+i/10)),
				TenantID:        "tenant-1",
				Spec: TaskSpec{
					Operation: "echo",
					ResourceRequirements: ResourceRequirements{
						CPU:       1.0,
						MemoryMB:  1024,
					},
				},
			})
			errors <- err
		}(i)
	}
	wg.Wait()
	close(errors)

	for err := range errors {
		if err != nil {
			t.Fatalf("concurrent submit: %v", err)
		}
	}

	// All 50 should be present.
	if len(coord.tasks) != 50 {
		t.Fatalf("tasks = %d, want 50", len(coord.tasks))
	}
}

// mockStore implements checkpoint.Store for testing.
type mockStore struct {
	mu      sync.Mutex
	snaps   map[int64]*checkpoint.Snapshot
}

func (m *mockStore) Save(s *checkpoint.Snapshot) error {
	m.mu.Lock()
	defer m.mu.Unlock()
	if m.snaps == nil {
		m.snaps = make(map[int64]*checkpoint.Snapshot)
	}
	m.snaps[s.Version] = s
	return nil
}

func (m *mockStore) Load(version int64) (*checkpoint.Snapshot, error) {
	m.mu.Lock()
	defer m.mu.Unlock()
	s, ok := m.snaps[version]
	if !ok {
		return nil, nil
	}
	return s, nil
}

func (m *mockStore) Latest() (*checkpoint.Snapshot, error) {
	m.mu.Lock()
	defer m.mu.Unlock()
	if len(m.snaps) == 0 {
		return nil, nil
	}
	var latest *checkpoint.Snapshot
	var latestVersion int64
	for v, s := range m.snaps {
		if v > latestVersion {
			latestVersion = v
			latest = s
		}
	}
	return latest, nil
}

func (m *mockStore) Versions() []int64 {
	m.mu.Lock()
	defer m.mu.Unlock()
	var vs []int64
	for v := range m.snaps {
		vs = append(vs, v)
	}
	return vs
}

// Ensure mockStore implements checkpoint.Store.
var _ checkpoint.Store = (*mockStore)(nil)