package controlplane

import (
	"context"
	"testing"
	"time"
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