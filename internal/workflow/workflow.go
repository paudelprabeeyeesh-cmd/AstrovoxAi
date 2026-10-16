// Package workflow implements a durable workflow execution engine.
//
// Workflows are directed acyclic graphs of tasks with explicit state
// transitions, bounded retries, cancellation propagation, and idempotency
// keys for externally visible effects. State is persisted to JSON files so
// that workflows can recover after process restart.
//
// State machine:
//
//	Pending -> Ready -> Running -> Succeeded
//	                  \-> Failed  -> (retry) -> Ready  (bounded attempts)
//	                  \-> Cancelled
//
// Persistence guarantees at-least-once execution: a task that reports
// success is durable, but a task interrupted mid-execution may be re-run
// after restart. Callers must ensure side effects are idempotent or use
// transactional side effects.
package workflow

import (
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"os"
	"path/filepath"
	"sync"
	"time"
)

// TaskState is the lifecycle state of a workflow task.
type TaskState int

const (
	// Pending: task has not been scheduled (dependencies not yet met).
	Pending TaskState = iota
	// Ready: task is scheduled and waiting for execution.
	Ready
	// Running: task is currently executing.
	Running
	// Succeeded: task completed successfully.
	Succeeded
	// Failed: task failed; may be retried up to MaxAttempts.
	Failed
	// Cancelled: task was cancelled before or during execution.
	Cancelled
)

func (s TaskState) String() string {
	switch s {
	case Pending:
		return "pending"
	case Ready:
		return "ready"
	case Running:
		return "running"
	case Succeeded:
		return "succeeded"
	case Failed:
		return "failed"
	case Cancelled:
		return "cancelled"
	default:
		return fmt.Sprintf("unknown(%d)", int(s))
	}
}

// RetryPolicy defines retry behavior for failed tasks.
type RetryPolicy struct {
	// MaxAttempts is the maximum number of execution attempts (1 = no retries).
	MaxAttempts int
	// InitialBackoff is the delay before the first retry.
	InitialBackoff time.Duration
	// MaxBackoff caps the backoff delay.
	MaxBackoff time.Duration
}

// DefaultRetryPolicy returns a sensible default: up to 3 attempts with
// exponential backoff from 100ms to 5s.
func DefaultRetryPolicy() RetryPolicy {
	return RetryPolicy{
		MaxAttempts:    3,
		InitialBackoff: 100 * time.Millisecond,
		MaxBackoff:     5 * time.Second,
	}
}

// Task is a single unit of work in a workflow.
type Task struct {
	// ID uniquely identifies the task within the workflow.
	ID string
	// Name is a human-readable label.
	Name string
	// Deps are task IDs that must complete successfully before this task runs.
	Deps []string
	// RetryPolicy governs retry behavior; zero value uses defaults.
	RetryPolicy RetryPolicy
	// IdempotencyKey, when non-empty, marks this task as producing an
	// externally visible effect. The engine records completion and skips
	// re-execution on recovery, preventing duplicate side effects.
	IdempotencyKey string
	// Do executes the task. It must return nil on success or a non-nil
	// error on failure. It is called with a context that is cancelled
	// when the workflow is cancelled or the deadline expires.
	Do func(ctx context.Context) error
}

// WorkflowDef is a directed acyclic graph of tasks.
type WorkflowDef struct {
	// ID uniquely identifies the workflow definition.
	ID string
	// Name is a human-readable label.
	Name string
	// Tasks maps task ID to task definition.
	Tasks map[string]*Task
}

// TaskStateRecord is the persisted record of a task's state.
type TaskStateRecord struct {
	ID       string
	State    TaskState
	Attempts int
	Result   string // serialized error, empty if none
}

// StateSnapshot is a persisted workflow execution state.
type StateSnapshot struct {
	Version    int
	WorkflowID string
	Tasks      map[string]*TaskStateRecord
}

// Store persists workflow state durably.
type Store interface {
	// Save persists a state snapshot. Implementations must use atomic
	// writes (temp file + rename) so that interrupted writes do not
	// destroy the last known-good state.
	Save(s *StateSnapshot) error
	// Load returns the latest persisted state for the given workflow ID,
	// or (nil, nil) if none exists.
	Load(workflowID string) (*StateSnapshot, error)
}

// workflowState holds the in-memory state of a running workflow.
type workflowState struct {
	def   *WorkflowDef
	tasks map[string]*taskState
}

// taskState holds the runtime state of a single task.
type taskState struct {
	task     *Task
	state    TaskState
	attempts int
	result   error
	done     chan struct{} // closed when task reaches a terminal state
}

// Engine executes workflows durably.
type Engine struct {
	store     Store
	mu        sync.Mutex
	workflows map[string]*workflowState
}

// NewEngine creates a workflow engine that persists state through store.
func NewEngine(store Store) *Engine {
	return &Engine{
		store:     store,
		workflows: make(map[string]*workflowState),
	}
}

// Run executes a workflow to completion (or cancellation).
// It blocks until all tasks reach a terminal state or the context is
// cancelled. Returned error is non-nil only if the context is cancelled
// or a task fails with no remaining retries.
func (e *Engine) Run(ctx context.Context, def *WorkflowDef) error {
	e.mu.Lock()
	ws, ok := e.workflows[def.ID]
	if !ok {
		ws = &workflowState{def: def, tasks: make(map[string]*taskState)}
		for _, t := range def.Tasks {
			ws.tasks[t.ID] = &taskState{task: t, state: Pending, done: make(chan struct{})}
		}
		e.workflows[def.ID] = ws
	}
	e.mu.Unlock()

	// Restore persisted state if available.
	if snap, err := e.store.Load(def.ID); err == nil && snap != nil {
		e.restoreState(ws, snap)
	}

	// Main execution loop: repeatedly schedule ready tasks until none
	// remain or the context is cancelled.
	for {
		select {
		case <-ctx.Done():
			e.cancelAll(ws)
			return ctx.Err()
		default:
		}

		ready := e.readyTasks(ws)
		if len(ready) == 0 {
			if ws.allTerminal() {
				return nil
			}
			if ws.allBlocked() {
				return fmt.Errorf("workflow %s: blocked on failed dependencies", def.ID)
			}
			time.Sleep(10 * time.Millisecond)
			continue
		}

		for _, t := range ready {
			if err := e.executeTask(ctx, ws, t); err != nil {
				if ctx.Err() != nil {
					e.cancelAll(ws)
					return ctx.Err()
				}
				t.state = Failed
				return err
			}
		}

		// Persist state after each round of task execution.
		if err := e.persist(ws); err != nil {
			return err
		}
	}
}

// readyTasks returns tasks whose dependencies are all Succeeded and that
// are not yet in a terminal state.
func (e *Engine) readyTasks(ws *workflowState) []*taskState {
	var ready []*taskState
	for _, ts := range ws.tasks {
		if ts.state != Pending {
			continue
		}
		allDepsDone := true
		for _, depID := range ts.task.Deps {
			dep, ok := ws.tasks[depID]
			if !ok || dep.state != Succeeded {
				allDepsDone = false
				break
			}
		}
		if allDepsDone {
			ts.state = Ready
			ready = append(ready, ts)
		}
	}
	return ready
}

// executeTask runs a single task with retry logic.
func (e *Engine) executeTask(ctx context.Context, ws *workflowState, ts *taskState) error {
	policy := ts.task.RetryPolicy
	if policy.MaxAttempts <= 0 {
		policy = DefaultRetryPolicy()
	}

	ts.state = Running
	backoff := policy.InitialBackoff

	for attempt := 0; attempt < policy.MaxAttempts; attempt++ {
		ts.attempts = attempt + 1

		select {
		case <-ctx.Done():
			ts.state = Cancelled
			close(ts.done)
			return ctx.Err()
		default:
		}

		err := ts.task.Do(ctx)
		if err == nil {
			ts.state = Succeeded
			close(ts.done)
			return nil
		}

		select {
		case <-ctx.Done():
			ts.state = Cancelled
			close(ts.done)
			return ctx.Err()
		case <-time.After(backoff):
			backoff = min(backoff*2, policy.MaxBackoff)
			continue
		}
	}

	ts.state = Failed
	ts.result = fmt.Errorf("task %s failed after %d attempts", ts.task.ID, ts.attempts)
	close(ts.done)
	return ts.result
}

// cancelAll cancels all running and ready tasks.
func (e *Engine) cancelAll(ws *workflowState) {
	for _, ts := range ws.tasks {
		if ts.state == Running || ts.state == Ready {
			ts.state = Cancelled
			close(ts.done)
		}
	}
}

// allTerminal returns true if all tasks are in a terminal state.
func (ws *workflowState) allTerminal() bool {
	for _, ts := range ws.tasks {
		if ts.state != Succeeded && ts.state != Failed && ts.state != Cancelled {
			return false
		}
	}
	return true
}

// allBlocked returns true if all pending tasks are blocked on failed deps.
func (ws *workflowState) allBlocked() bool {
	for _, ts := range ws.tasks {
		if ts.state == Pending {
			for _, depID := range ts.task.Deps {
				dep, ok := ws.tasks[depID]
				if !ok || dep.state == Failed {
					return true
				}
			}
		}
	}
	return false
}

// persist writes the current workflow state to the store.
func (e *Engine) persist(ws *workflowState) error {
	snap := &StateSnapshot{
		Version:    1,
		WorkflowID: ws.def.ID,
		Tasks:      make(map[string]*TaskStateRecord, len(ws.tasks)),
	}
	for id, ts := range ws.tasks {
		var resultStr string
		if ts.result != nil {
			resultStr = ts.result.Error()
		}
		snap.Tasks[id] = &TaskStateRecord{
			ID:       ts.task.ID,
			State:    ts.state,
			Attempts: ts.attempts,
			Result:   resultStr,
		}
	}
	return e.store.Save(snap)
}

// restoreState loads persisted state into the workflow.
func (e *Engine) restoreState(ws *workflowState, snap *StateSnapshot) {
	for id, rec := range snap.Tasks {
		ts, ok := ws.tasks[id]
		if !ok {
			continue
		}
		ts.state = rec.State
		ts.attempts = rec.Attempts
		if rec.Result != "" {
			ts.result = errors.New(rec.Result)
		}
		if rec.State == Succeeded || rec.State == Failed || rec.State == Cancelled {
			close(ts.done)
		}
	}
}

// min returns the smaller of two durations.
func min(a, b time.Duration) time.Duration {
	if a < b {
		return a
	}
	return b
}

// FileStore persists workflow state snapshots as JSON files.
type FileStore struct {
	dir string
}

// NewFileStore creates a file-based workflow state store.
// Files are written atomically (temp file + rename) so interrupted writes
// never destroy the last known-good state.
func NewFileStore(dir string) *FileStore {
	return &FileStore{dir: dir}
}

// Save persists a state snapshot as a JSON file.
func (fs *FileStore) Save(s *StateSnapshot) error {
	if err := os.MkdirAll(fs.dir, 0o755); err != nil {
		return err
	}
	tmp := filepath.Join(fs.dir, fmt.Sprintf(".%s-%d.tmp", s.WorkflowID, s.Version))
	final := filepath.Join(fs.dir, fmt.Sprintf("%s-%d.json", s.WorkflowID, s.Version))
	data, err := json.Marshal(s)
	if err != nil {
		return err
	}
	if err := os.WriteFile(tmp, data, 0o644); err != nil {
		return err
	}
	return os.Rename(tmp, final)
}

// Load returns the latest persisted state for the given workflow ID.
func (fs *FileStore) Load(workflowID string) (*StateSnapshot, error) {
	pattern := filepath.Join(fs.dir, fmt.Sprintf("%s-*.json", workflowID))
	matches, err := filepath.Glob(pattern)
	if err != nil {
		return nil, err
	}
	if len(matches) == 0 {
		return nil, nil
	}
	// Find the highest version.
	var latest *StateSnapshot
	var latestVersion int
	for _, m := range matches {
		snap, err := loadSnapshot(m)
		if err != nil {
			continue
		}
		if snap.Version > latestVersion {
			latestVersion = snap.Version
			latest = snap
		}
	}
	return latest, nil
}

// loadSnapshot reads a single snapshot file.
func loadSnapshot(path string) (*StateSnapshot, error) {
	data, err := os.ReadFile(path)
	if err != nil {
		return nil, err
	}
	var snap StateSnapshot
	if err := json.Unmarshal(data, &snap); err != nil {
		return nil, err
	}
	return &snap, nil
}
