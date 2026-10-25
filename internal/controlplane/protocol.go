// Package controlplane implements the distributed execution control plane:
// a coordinator that accepts task submissions and assigns them to worker
// processes, and workers that execute those tasks and report results.
//
// The protocol is versioned and typed. Every message carries a protocol
// version so that coordinator and worker can detect mismatches and refuse
// to interoperate when they cannot understand each other.
//
// All requests are typed: invalid inputs are rejected with typed errors,
// never silently dropped. Backpressure is explicit: a full queue returns
// CodeQueueFull rather than blocking indefinitely.
//
// This package does not import internal/distributed; it defines its own
// wire protocol over TCP/JSON so that the coordinator and worker are
// independent processes that can be started, stopped, and upgraded
// independently.
package controlplane

import (
	"encoding/json"
	"errors"
	"fmt"
	"time"
)

// ProtocolVersion is the current wire-protocol version. The coordinator
// and worker must agree on this version; mismatches are refused at
// connection time.
const ProtocolVersion = 1

// Err* are the protocol-level errors returned by the coordinator and
// worker. They are typed so callers can classify failures with
// errors.Is / errors.As without string matching.
var (
	ErrProtocolMismatch = errors.New("protocol version mismatch")
	ErrUnknownTask      = errors.New("task not found")
	ErrUnknownWorker    = errors.New("worker not found")
	ErrTaskAlreadyAssigned = errors.New("task already assigned")
	ErrWorkerFull       = errors.New("worker queue is full")
	ErrWorkerUnhealthy  = errors.New("worker is unhealthy")
	ErrInvalidTask      = errors.New("invalid task specification")
	ErrDeadlineExpired  = errors.New("deadline expired")
	ErrTaskCancelled    = errors.New("task cancelled")
	ErrDuplicateSubmission = errors.New("duplicate submission")
)

// TaskState is the lifecycle state of a task.
type TaskState int

const (
	TaskPending TaskState = iota
	TaskAssigned
	TaskRunning
	TaskSucceeded
	TaskFailed
	TaskCancelled
	TaskExpired
)

func (ts TaskState) String() string {
	switch ts {
	case TaskPending:
		return "pending"
	case TaskAssigned:
		return "assigned"
	case TaskRunning:
		return "running"
	case TaskSucceeded:
		return "succeeded"
	case TaskFailed:
		return "failed"
	case TaskCancelled:
		return "cancelled"
	case TaskExpired:
		return "expired"
	default:
		return fmt.Sprintf("unknown(%d)", int(ts))
	}
}

// TaskSpec describes the computation to perform.
type TaskSpec struct {
	// Operation is the name of the operation to execute (e.g. "matmul",
	// "inference", "workflow.step").
	Operation string `json:"operation"`
	// Payload is the serialized input. Its format is determined by
	// Operation; the coordinator does not interpret it.
	Payload []byte `json:"payload"`
	// ResourceRequirements are the resources the task needs.
	ResourceRequirements ResourceRequirements `json:"resource_requirements"`
}

// ResourceRequirements are the resources a task needs.
type ResourceRequirements struct {
	// CPU is the number of CPU cores required (fractional allowed).
	CPU float64 `json:"cpu"`
	// MemoryMB is the memory required in megabytes.
	MemoryMB int64 `json:"memory_mb"`
	// GPU indicates whether a GPU is required.
	GPU bool `json:"gpu"`
}

// TaskRequest is one unit of work submitted to the coordinator.
type TaskRequest struct {
	// ProtocolVersion must match the coordinator's version.
	ProtocolVersion int `json:"protocol_version"`
	// TaskID uniquely identifies the task within the coordinator.
	TaskID string `json:"task_id"`
	// TenantID is the tenant that owns this task. It is used for
	// authorization and quota enforcement; it is never derived from
	// client-supplied data without validation.
	TenantID string `json:"tenant_id"`
	// ModelID identifies the model version (if any) used by this task.
	ModelID string `json:"model_id,omitempty"`
	// Spec is the computation to perform.
	Spec TaskSpec `json:"spec"`
	// Deadline is the wall-clock time by which the task must complete.
	// Zero means no deadline.
	Deadline time.Time `json:"deadline,omitempty"`
	// IdempotencyKey, when non-empty, prevents duplicate execution of
	// externally visible effects. The coordinator ensures that a task
	// with the same idempotency key is not executed twice.
	IdempotencyKey string `json:"idempotency_key,omitempty"`
	// TraceID correlates this task with related events across service
	// boundaries for diagnostics.
	TraceID string `json:"trace_id,omitempty"`
}

// TaskResponse is the coordinator's answer to a task request.
type TaskResponse struct {
	// ProtocolVersion must match the request's version.
	ProtocolVersion int `json:"protocol_version"`
	// TaskID echoes the request's task ID.
	TaskID string `json:"task_id"`
	// State is the current lifecycle state of the task.
	State TaskState `json:"state"`
	// Attempt is the monotonically increasing attempt generation.
	Attempt int `json:"attempt"`
	// Output is the serialized task result (populated when State is
	// TaskSucceeded).
	Output []byte `json:"output,omitempty"`
	// Error is set when the task failed (State is TaskFailed or
	// TaskExpired). It is a safe, non-sensitive diagnostic message.
	Error string `json:"error,omitempty"`
	// Timestamp is when the response was generated (coordinator wall
	// clock; not used for ordering).
	Timestamp time.Time `json:"timestamp"`
}

// WorkerRegistration is sent by the worker when it connects to the
// coordinator.
type WorkerRegistration struct {
	// ProtocolVersion must match the coordinator's version.
	ProtocolVersion int `json:"protocol_version"`
	// WorkerID uniquely identifies the worker.
	WorkerID string `json:"worker_id"`
	// Capabilities lists the operations this worker can execute.
	Capabilities []string `json:"capabilities"`
	// Resources are the resources this worker has available.
	Resources ResourceRequirements `json:"resources"`
	// TenantQuotas maps tenant ID to resource quota (in arbitrary units).
	TenantQuotas map[string]int64 `json:"tenant_quotas,omitempty"`
}

// WorkerHeartbeat is sent by the worker to the coordinator.
type WorkerHeartbeat struct {
	// ProtocolVersion must match the coordinator's version.
	ProtocolVersion int `json:"protocol_version"`
	// WorkerID identifies the worker.
	WorkerID string `json:"worker_id"`
	// Timestamp is the wall-clock time of the heartbeat.
	Timestamp time.Time `json:"timestamp"`
	// ActiveTasks is the number of tasks currently executing on this
	// worker.
	ActiveTasks int `json:"active_tasks"`
	// CompletedTasks is the number of tasks this worker has completed
	// since startup.
	CompletedTasks int `json:"completed_tasks"`
	// FailedTasks is the number of tasks this worker has failed since
	// startup.
	FailedTasks int `json:"failed_tasks"`
}

// WorkerAssignment is sent by the coordinator to assign a task to a
// worker.
type WorkerAssignment struct {
	// ProtocolVersion must match the coordinator's version.
	ProtocolVersion int `json:"protocol_version"`
	// TaskID is the task being assigned.
	TaskID string `json:"task_id"`
	// Spec is the task specification.
	Spec TaskSpec `json:"spec"`
	// Attempt is the attempt generation for this assignment.
	Attempt int `json:"attempt"`
	// Deadline is the task deadline (copied from the request).
	Deadline time.Time `json:"deadline,omitempty"`
}

// WorkerResult is sent by the worker to report task completion.
type WorkerResult struct {
	ProtocolVersion int    `json:"protocol_version"`
	TaskID          string `json:"task_id"`
	WorkerID        string `json:"worker_id"`
	Attempt         int    `json:"attempt"`
	State           TaskState `json:"state"`
	Output          []byte `json:"output,omitempty"`
	Error           string `json:"error,omitempty"`
}

// MarshalRequest serializes a TaskRequest to JSON bytes.
func MarshalRequest(req *TaskRequest) ([]byte, error) {
	return json.Marshal(req)
}

// UnmarshalRequest deserializes JSON bytes into a TaskRequest.
func UnmarshalRequest(data []byte) (*TaskRequest, error) {
	var req TaskRequest
	if err := json.Unmarshal(data, &req); err != nil {
		return nil, err
	}
	return &req, nil
}

// MarshalResponse serializes a TaskResponse to JSON bytes.
func MarshalResponse(res *TaskResponse) ([]byte, error) {
	return json.Marshal(res)
}

// UnmarshalResponse deserializes JSON bytes into a TaskResponse.
func UnmarshalResponse(data []byte) (*TaskResponse, error) {
	var res TaskResponse
	if err := json.Unmarshal(data, &res); err != nil {
		return nil, err
	}
	return &res, nil
}

// MarshalRegistration serializes a WorkerRegistration to JSON bytes.
func MarshalRegistration(reg *WorkerRegistration) ([]byte, error) {
	return json.Marshal(reg)
}

// UnmarshalRegistration deserializes JSON bytes into a WorkerRegistration.
func UnmarshalRegistration(data []byte) (*WorkerRegistration, error) {
	var reg WorkerRegistration
	if err := json.Unmarshal(data, &reg); err != nil {
		return nil, err
	}
	return &reg, nil
}

// MarshalHeartbeat serializes a WorkerHeartbeat to JSON bytes.
func MarshalHeartbeat(hb *WorkerHeartbeat) ([]byte, error) {
	return json.Marshal(hb)
}

// UnmarshalHeartbeat deserializes JSON bytes into a WorkerHeartbeat.
func UnmarshalHeartbeat(data []byte) (*WorkerHeartbeat, error) {
	var hb WorkerHeartbeat
	if err := json.Unmarshal(data, &hb); err != nil {
		return nil, err
	}
	return &hb, nil
}

// MarshalAssignment serializes a WorkerAssignment to JSON bytes.
func MarshalAssignment(assign *WorkerAssignment) ([]byte, error) {
	return json.Marshal(assign)
}

// UnmarshalAssignment deserializes JSON bytes into a WorkerAssignment.
func UnmarshalAssignment(data []byte) (*WorkerAssignment, error) {
	var assign WorkerAssignment
	if err := json.Unmarshal(data, &assign); err != nil {
		return nil, err
	}
	return &assign, nil
}

// MarshalResult serializes a WorkerResult to JSON bytes.
func MarshalResult(res *WorkerResult) ([]byte, error) {
	return json.Marshal(res)
}

// UnmarshalResult deserializes JSON bytes into a WorkerResult.
func UnmarshalResult(data []byte) (*WorkerResult, error) {
	var res WorkerResult
	if err := json.Unmarshal(data, &res); err != nil {
		return nil, err
	}
	return &res, nil
}

// ValidateRequest checks that a task request is well-formed.
func ValidateRequest(req *TaskRequest) error {
	if req.TaskID == "" {
		return errors.New("task_id is required")
	}
	if req.TenantID == "" {
		return errors.New("tenant_id is required")
	}
	if req.Spec.Operation == "" {
		return errors.New("operation is required")
	}
	return nil
}