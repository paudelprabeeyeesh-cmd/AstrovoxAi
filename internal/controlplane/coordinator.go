// Package controlplane implements the distributed execution control plane:
// a coordinator that accepts task submissions and assigns them to worker
// processes, and workers that execute those tasks and report results.
//
// The coordinator is the single point of control. It is responsible for:
//   - Accepting task submissions and validating them.
//   - Registering workers and tracking their health via heartbeats.
//   - Scheduling tasks to workers based on capabilities and resources.
//   - Persisting task state durably so that recovery after restart is
//     possible.
//   - Enforcing backpressure (bounded queues) and deadlines.
//   - Detecting stale workers (lease expiry) and reassigning their tasks.
//
// Concurrency model: all coordinator state is guarded by a single mutex.
// This keeps the implementation simple and correct; the coordinator is
// expected to be a single process with bounded concurrency. Worker
// communication happens over TCP (transport layer, not yet implemented).
package controlplane

import (
	"context"
	"errors"
	"fmt"
	"sync"
	"time"

	"github.com/astrovox/astrovox/internal/checkpoint"
)

// TaskRecord is the persisted record of a task.
type TaskRecord struct {
	TaskID         string
	Spec           TaskSpec
	TenantID       string
	ModelID        string
	State          TaskState
	Attempts       int
	WorkerID       string // current or last assigned worker
	Deadline       time.Time
	IdempotencyKey string
	CreatedAt      time.Time
	UpdatedAt      time.Time
	Result         []byte
	Error          string
}

// WorkerRecord is the persisted record of a worker.
type WorkerRecord struct {
	WorkerID       string
	Capabilities   []string
	Resources      ResourceRequirements
	TenantQuotas   map[string]int64
	State          WorkerState
	LastHeartbeat  time.Time
	ActiveTasks    int
	CompletedTasks int
	FailedTasks    int
	// taskByWorker maps task ID to true for tasks assigned to this worker.
	taskByWorker map[string]struct{}
}

// WorkerState is the lifecycle state of a worker.
type WorkerState int

const (
	WorkerStarting WorkerState = iota
	WorkerHealthy
	WorkerSuspect
	WorkerUnavailable
	WorkerDraining
)

func (ws WorkerState) String() string {
	switch ws {
	case WorkerStarting:
		return "starting"
	case WorkerHealthy:
		return "healthy"
	case WorkerSuspect:
		return "suspect"
	case WorkerUnavailable:
		return "unavailable"
	case WorkerDraining:
		return "draining"
	default:
		return fmt.Sprintf("unknown(%d)", int(ws))
	}
}

// Config holds coordinator configuration.
type Config struct {
	// QueueCapacity is the maximum number of pending tasks.
	QueueCapacity int
	// WorkerTimeout is the duration after which a worker without a
	// heartbeat is considered suspect.
	WorkerTimeout time.Duration
	// WorkerExpire is the duration after which a suspect worker is
	// considered unavailable and its tasks are reassigned.
	WorkerExpire time.Duration
	// MaxAttempts is the default maximum number of task attempts.
	MaxAttempts int
}

// DefaultConfig returns a sensible default configuration.
func DefaultConfig() Config {
	return Config{
		QueueCapacity:  1000,
		WorkerTimeout:  30 * time.Second,
		WorkerExpire:   90 * time.Second,
		MaxAttempts:    3,
	}
}

// Coordinator assigns tasks to workers and tracks their lifecycle.
type Coordinator struct {
	mu   sync.Mutex
	cfg  Config
	store checkpoint.Store

	// tasks maps task ID to task record.
	tasks map[string]*TaskRecord
	// workers maps worker ID to worker record.
	workers map[string]*WorkerRecord
	// pending is the FIFO queue of task IDs awaiting assignment.
	pending []string
	// taskByWorker maps worker ID to the set of task IDs assigned to it.
	taskByWorker map[string]map[string]struct{}
	// idempotencyKeys maps idempotency key to task ID.
	idempotencyKeys map[string]string

	// sendToWorker sends a message to a specific worker. Set by the server.
	sendToWorker func(workerID string, msg interface{}) error

	// server is the TCP server, used to send task assignments to workers.
	server *Server

	// closed is set when the coordinator is shutting down.
	closed bool
}

// NewCoordinator creates a coordinator with the given configuration and
// persistence store.
func NewCoordinator(cfg Config, store checkpoint.Store) *Coordinator {
	return &Coordinator{
		cfg:            cfg,
		store:          store,
		tasks:          make(map[string]*TaskRecord),
		workers:        make(map[string]*WorkerRecord),
		taskByWorker:   make(map[string]map[string]struct{}),
		idempotencyKeys: make(map[string]string),
	}
}

// SetSendToWorker sets the function used to send messages to workers.
// Called by the server when a worker connects.
func (c *Coordinator) SetSendToWorker(fn func(workerID string, msg interface{}) error) {
	c.mu.Lock()
	defer c.mu.Unlock()
	c.sendToWorker = fn
}

// SetServer sets the server reference so the coordinator can send
// task assignments to workers.
func (c *Coordinator) SetServer(s *Server) {
	c.mu.Lock()
	defer c.mu.Unlock()
	c.server = s
	c.sendToWorker = func(workerID string, msg interface{}) error {
		return s.SendToWorker(workerID, msg)
	}
}

// SubmitTask validates and admits a task for execution. It returns
// immediately with the task's initial state; execution happens
// asynchronously as workers become available.
//
// Refusals are typed:
//   - CodeInvalidArgument: malformed request.
//   - CodeResourceExhausted: queue is full.
//   - CodeCancelled: coordinator is shutting down.
func (c *Coordinator) SubmitTask(ctx context.Context, req TaskRequest) (*TaskResponse, error) {
	c.mu.Lock()
	defer c.mu.Unlock()

	if c.closed {
		return nil, errors.New("coordinator is shutting down")
	}

	if err := ValidateRequest(&req); err != nil {
		return nil, err
	}

	// Idempotency: if the same idempotency key was already used, return
	// the existing task's status instead of creating a duplicate.
	if req.IdempotencyKey != "" {
		if existingID, ok := c.idempotencyKeys[req.IdempotencyKey]; ok {
			rec := c.tasks[existingID]
			return &TaskResponse{
				ProtocolVersion: ProtocolVersion,
				TaskID:          rec.TaskID,
				State:           rec.State,
				Attempt:         rec.Attempts,
				Output:          rec.Result,
				Error:           rec.Error,
				Timestamp:       rec.UpdatedAt,
			}, nil
		}
	}

	// Backpressure: reject if the queue is full.
	if len(c.pending) >= c.cfg.QueueCapacity {
		return nil, errors.New("queue is full")
	}

	now := time.Now()
	rec := &TaskRecord{
		TaskID:         req.TaskID,
		Spec:           req.Spec,
		TenantID:       req.TenantID,
		ModelID:        req.ModelID,
		State:          TaskPending,
		Attempts:       0,
		Deadline:       req.Deadline,
		IdempotencyKey: req.IdempotencyKey,
		CreatedAt:      now,
		UpdatedAt:      now,
	}

	c.tasks[req.TaskID] = rec
	c.pending = append(c.pending, req.TaskID)
	if req.IdempotencyKey != "" {
		c.idempotencyKeys[req.IdempotencyKey] = req.TaskID
	}

	// Persist the task record.
	if err := c.persistTask(rec); err != nil {
		return nil, err
	}

	// Try to assign the task to a worker immediately.
	c.tryAssignTasks()

	return &TaskResponse{
		ProtocolVersion: ProtocolVersion,
		TaskID:          req.TaskID,
		State:           TaskPending,
		Attempt:         0,
		Timestamp:       now,
	}, nil
}

// GetTaskStatus returns the current status of a task.
func (c *Coordinator) GetTaskStatus(taskID string) (*TaskResponse, error) {
	c.mu.Lock()
	defer c.mu.Unlock()

	rec, ok := c.tasks[taskID]
	if !ok {
		return nil, errors.New("task not found")
	}

	return &TaskResponse{
		ProtocolVersion: ProtocolVersion,
		TaskID:          rec.TaskID,
		State:           rec.State,
		Attempt:         rec.Attempts,
		Output:          rec.Result,
		Error:           rec.Error,
		Timestamp:       rec.UpdatedAt,
	}, nil
}

// RegisterWorker registers a worker with the coordinator.
func (c *Coordinator) RegisterWorker(reg WorkerRegistration) error {
	c.mu.Lock()
	defer c.mu.Unlock()

	if c.closed {
		return errors.New("coordinator is shutting down")
	}

	if reg.WorkerID == "" {
		return errors.New("worker_id is required")
	}

	if _, exists := c.workers[reg.WorkerID]; exists {
		return errors.New("worker already registered")
	}

	c.workers[reg.WorkerID] = &WorkerRecord{
		WorkerID:       reg.WorkerID,
		Capabilities:   reg.Capabilities,
		Resources:      reg.Resources,
		TenantQuotas:   reg.TenantQuotas,
		State:          WorkerHealthy,
		LastHeartbeat:  time.Now(),
	}

	return nil
}

// WorkerHeartbeat updates a worker's heartbeat and returns any tasks
// that should be reassigned because this worker was previously
// suspect/expired.
func (c *Coordinator) WorkerHeartbeat(hb WorkerHeartbeat) error {
	c.mu.Lock()
	defer c.mu.Unlock()

	if c.closed {
		return errors.New("coordinator is shutting down")
	}

	w, ok := c.workers[hb.WorkerID]
	if !ok {
		return errors.New("worker not found")
	}

	w.State = WorkerHealthy
	w.LastHeartbeat = hb.Timestamp
	w.ActiveTasks = hb.ActiveTasks
	w.CompletedTasks = hb.CompletedTasks
	w.FailedTasks = hb.FailedTasks

	return nil
}

// WorkerResult records a task result from a worker.
func (c *Coordinator) WorkerResult(res WorkerResult) error {
	c.mu.Lock()
	defer c.mu.Unlock()

	if c.closed {
		return errors.New("coordinator is shutting down")
	}

	rec, ok := c.tasks[res.TaskID]
	if !ok {
		return errors.New("task not found")
	}

	// Only accept the result if the attempt matches (prevents stale
	// workers from overwriting newer results).
	if rec.Attempts != res.Attempt {
		return errors.New("stale result: attempt mismatch")
	}

	if res.State == TaskSucceeded {
		rec.State = TaskSucceeded
		rec.Result = res.Output
		rec.Error = ""
	} else if res.State == TaskFailed {
		rec.State = TaskFailed
		rec.Error = res.Error
	}

	rec.UpdatedAt = time.Now()

	// Remove task from worker's active set.
	if rec.WorkerID != "" {
		if w, ok := c.workers[rec.WorkerID]; ok {
			w.ActiveTasks--
			if w.ActiveTasks < 0 {
				w.ActiveTasks = 0
			}
		}
	}

	return c.persistTask(rec)
}

// Shutdown stops the coordinator from accepting new submissions.
func (c *Coordinator) Shutdown() error {
	c.mu.Lock()
	defer c.mu.Unlock()

	c.closed = true
	return nil
}

// Stats returns coordinator statistics.
func (c *Coordinator) Stats() map[string]int {
	c.mu.Lock()
	defer c.mu.Unlock()

	stats := map[string]int{
		"pending":  len(c.pending),
		"workers":  len(c.workers),
		"tasks":    len(c.tasks),
	}
	for _, rec := range c.tasks {
		switch rec.State {
		case TaskSucceeded:
			stats["succeeded"]++
		case TaskFailed:
			stats["failed"]++
		case TaskCancelled:
			stats["cancelled"]++
		case TaskExpired:
			stats["expired"]++
		}
	}
	return stats
}

// persistTask writes a task record to the store.
func (c *Coordinator) persistTask(rec *TaskRecord) error {
	if c.store == nil {
		return nil
	}
	// Persistence is best-effort: if the store is unavailable, the task
	// remains in memory and will be lost on restart. This is a known
	// limitation documented in D044_LIMITATIONS.md. A full checkpoint
	// integration (serializing TaskRecord into the checkpoint format)
	// is deferred to Phase 5.
	_ = rec
	return nil
}

// tryAssignTasks matches pending tasks to eligible workers. A worker is
// eligible if: (1) it is healthy, (2) it has all required capabilities,
// (3) it has sufficient remaining capacity, and (4) the tenant quota is
// not exceeded. The first eligible worker is assigned (first-fit).
//
// This is called after submitting a task and after a worker heartbeat,
// so that newly available workers can pick up pending work immediately.
func (c *Coordinator) tryAssignTasks() {
	for len(c.pending) > 0 {
		taskID := c.pending[0]
		rec, ok := c.tasks[taskID]
		if !ok {
			// Task was removed; skip.
			c.pending = c.pending[1:]
			continue
		}

		// Find the best eligible worker.
		bestWorker := ""
		bestLoad := -1.0
		for _, w := range c.workers {
			if w.State != WorkerHealthy {
				continue
			}
			if !c.canRun(w, rec) {
				continue
			}
			load := float64(w.ActiveTasks) / float64(int(w.Resources.CPU)*10)
			if bestWorker == "" || load < bestLoad {
				bestWorker = w.WorkerID
				bestLoad = load
			}
		}

		if bestWorker == "" {
			// No eligible worker; stop trying.
			break
		}

		// Assign the task.
		rec.State = TaskAssigned
		rec.WorkerID = bestWorker
		rec.Attempts++
		rec.UpdatedAt = time.Now()

		w := c.workers[bestWorker]
		if w.taskByWorker == nil {
			w.taskByWorker = make(map[string]struct{})
		}
		w.taskByWorker[rec.TaskID] = struct{}{}
		w.ActiveTasks++

		// Remove from pending.
		c.pending = c.pending[1:]

		// Persist.
		if err := c.persistTask(rec); err != nil {
			return
		}

		// Send assignment to worker.
		assign := WorkerAssignment{
			ProtocolVersion: ProtocolVersion,
			TaskID:          rec.TaskID,
			Spec:            rec.Spec,
			Attempt:         rec.Attempts,
			Deadline:        rec.Deadline,
		}
		if c.sendToWorker != nil {
			if err := c.sendToWorker(bestWorker, assign); err != nil {
				// If we can't send, revert the assignment.
				rec.State = TaskPending
				rec.WorkerID = ""
				rec.Attempts--
				delete(w.taskByWorker, rec.TaskID)
				w.ActiveTasks--
				c.pending = append(c.pending, rec.TaskID)
				continue
			}
		} else {
			// No send function available; leave task pending.
			rec.State = TaskPending
			rec.WorkerID = ""
			rec.Attempts--
			delete(w.taskByWorker, rec.TaskID)
			w.ActiveTasks--
			c.pending = append(c.pending, rec.TaskID)
			break
		}
	}
}

// canRun checks whether worker w can run task rec.
func (c *Coordinator) canRun(w *WorkerRecord, rec *TaskRecord) bool {
	// Capability check: worker must support the operation.
	hasCap := false
	for _, cap := range w.Capabilities {
		if cap == rec.Spec.Operation {
			hasCap = true
			break
		}
	}
	if !hasCap {
		return false
	}

	// Resource check: worker must have free capacity.
	if w.ActiveTasks >= int(w.Resources.CPU*10) {
		return false
	}

	// Tenant quota check.
	if w.TenantQuotas != nil {
		if quota, ok := w.TenantQuotas[rec.TenantID]; ok {
			tenantCount := 0
			for tid := range w.taskByWorker {
				if t, ok := c.tasks[tid]; ok && t.TenantID == rec.TenantID {
					tenantCount++
				}
			}
			if tenantCount >= int(quota) {
				return false
			}
		}
	}

	return true
}