package controlplane

import (
	"context"
	"sync"
	"testing"
	"time"

	"github.com/astrovox/astrovox/internal/checkpoint"
)

// TestSubmitTaskAndGetStatus verifies task submission and status retrieval.
func TestSubmitTaskAndGetStatus(t *testing.T) {
	store := &mockStore{}
	coord := NewCoordinator(Config{
		QueueCapacity: 10,
	}, store)

	req := TaskRequest{
		ProtocolVersion: ProtocolVersion,
		TaskID:          "task-1",
		TenantID:        "tenant-1",
		Spec: TaskSpec{
			Operation: "echo",
			Payload:   []byte("hello"),
			ResourceRequirements: ResourceRequirements{
				CPU:       1.0,
				MemoryMB:  1024,
			},
		},
	}

	resp, err := coord.SubmitTask(context.Background(), req)
	if err != nil {
		t.Fatalf("SubmitTask: %v", err)
	}
	if resp.TaskID != "task-1" {
		t.Fatalf("TaskID = %q, want %q", resp.TaskID, "task-1")
	}
	if resp.State != TaskPending {
		t.Fatalf("State = %v, want %v", resp.State, TaskPending)
	}

	// Get status.
	got, err := coord.GetTaskStatus("task-1")
	if err != nil {
		t.Fatalf("GetTaskStatus: %v", err)
	}
	if got.State != TaskPending {
		t.Fatalf("GetTaskStatus.State = %v, want %v", got.State, TaskPending)
	}

	// Unknown task.
	if _, err := coord.GetTaskStatus("nonexistent"); err == nil {
		t.Fatal("expected error for nonexistent task")
	}
}

// TestSubmitTaskValidation verifies that invalid requests are refused.
func TestSubmitTaskValidation(t *testing.T) {
	coord := NewCoordinator(Config{QueueCapacity: 10}, nil)

		// Empty task ID.
		if _, err := coord.SubmitTask(context.Background(), TaskRequest{
			ProtocolVersion: ProtocolVersion,
			TaskID:          "",
			TenantID:        "tenant-1",
			Spec: TaskSpec{
				Operation: "echo",
				ResourceRequirements: ResourceRequirements{
					CPU:       1.0,
					MemoryMB:  1024,
				},
			},
		}); err == nil {
			t.Fatal("expected error for empty task ID")
		}

		// Empty operation.
		if _, err := coord.SubmitTask(context.Background(), TaskRequest{
			ProtocolVersion: ProtocolVersion,
			TaskID:          "t1",
			TenantID:        "tenant-1",
			Spec: TaskSpec{
				Operation: "",
				ResourceRequirements: ResourceRequirements{
					CPU:       1.0,
					MemoryMB:  1024,
				},
			},
		}); err == nil {
			t.Fatal("expected error for empty operation")
		}

		// Non-positive CPU.
		if _, err := coord.SubmitTask(context.Background(), TaskRequest{
			ProtocolVersion: ProtocolVersion,
			TaskID:          "t1",
			TenantID:        "tenant-1",
			Spec: TaskSpec{
				Operation: "echo",
				ResourceRequirements: ResourceRequirements{
					CPU:       0,
					MemoryMB:  1,
				},
			},
		}); err == nil {
			t.Fatal("expected error for non-positive CPU")
		}
}

// TestBackpressure verifies that the queue rejects submissions when full.
func TestBackpressure(t *testing.T) {
	coord := NewCoordinator(Config{QueueCapacity: 2}, nil)

	// Fill the queue.
	for i := 0; i < 2; i++ {
		_, err := coord.SubmitTask(context.Background(), TaskRequest{
			ProtocolVersion: ProtocolVersion,
			TaskID:          "t" + string(rune('0'+i)),
			TenantID:        "tenant-1",
			Spec:            TaskSpec{Operation: "echo",
				ResourceRequirements: ResourceRequirements{CPU: 1.0, MemoryMB: 1}},
		})
		if err != nil {
			t.Fatalf("SubmitTask %d: %v", i, err)
		}
	}

	// Third should be refused.
	if _, err := coord.SubmitTask(context.Background(), TaskRequest{
		ProtocolVersion: ProtocolVersion,
		TaskID:          "t3",
		TenantID:        "tenant-1",
		Spec:            TaskSpec{Operation: "echo",
			ResourceRequirements: ResourceRequirements{CPU: 1.0, MemoryMB: 1}},
	}); err == nil {
		t.Fatal("expected queue full error")
	}
}

// TestIdempotency verifies that submitting the same idempotency key
// returns the existing task instead of creating a duplicate.
func TestIdempotency(t *testing.T) {
	coord := NewCoordinator(Config{QueueCapacity: 10}, nil)

	req := TaskRequest{
		ProtocolVersion: ProtocolVersion,
		TaskID:          "task-1",
		TenantID:        "tenant-1",
		Spec:            TaskSpec{Operation: "echo",
			ResourceRequirements: ResourceRequirements{CPU: 1.0, MemoryMB: 1}},
		IdempotencyKey:  "key-1",
	}

	resp1, err := coord.SubmitTask(context.Background(), req)
	if err != nil {
		t.Fatalf("SubmitTask 1: %v", err)
	}

	resp2, err := coord.SubmitTask(context.Background(), req)
	if err != nil {
		t.Fatalf("SubmitTask 2: %v", err)
	}

	if resp2.TaskID != resp1.TaskID {
		t.Fatalf("TaskID = %q, want %q", resp2.TaskID, resp1.TaskID)
	}
}

// TestRegisterWorker verifies worker registration.
func TestRegisterWorker(t *testing.T) {
	coord := NewCoordinator(Config{QueueCapacity: 10}, nil)

	reg := WorkerRegistration{
		ProtocolVersion: ProtocolVersion,
		WorkerID:        "worker-1",
		Capabilities:    []string{"echo", "matmul"},
		Resources: ResourceRequirements{
			CPU:       2.0,
			MemoryMB:  1024,
		},
	}

	if err := coord.RegisterWorker(reg); err != nil {
		t.Fatalf("RegisterWorker: %v", err)
	}

	// Duplicate registration should fail.
	if err := coord.RegisterWorker(reg); err == nil {
		t.Fatal("expected error for duplicate worker registration")
	}
}

// TestWorkerHeartbeat verifies heartbeat handling.
func TestWorkerHeartbeat(t *testing.T) {
	coord := NewCoordinator(Config{QueueCapacity: 10}, nil)

	w := &WorkerRecord{
		WorkerID:       "worker-1",
		Capabilities:   []string{"echo"},
		Resources:      ResourceRequirements{CPU: 2.0, MemoryMB: 1024},
		State:          WorkerHealthy,
		LastHeartbeat:  time.Now(),
	}
	coord.workers["worker-1"] = w

	hb := WorkerHeartbeat{
		ProtocolVersion: ProtocolVersion,
		WorkerID:        "worker-1",
		Timestamp:       time.Now(),
		ActiveTasks:     0,
		CompletedTasks:  5,
		FailedTasks:     0,
	}

	if err := coord.WorkerHeartbeat(hb); err != nil {
		t.Fatalf("WorkerHeartbeat: %v", err)
	}

	// Unknown worker.
	if err := coord.WorkerHeartbeat(WorkerHeartbeat{
		ProtocolVersion: ProtocolVersion,
		WorkerID:        "nonexistent",
	}); err == nil {
		t.Fatal("expected error for unknown worker")
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