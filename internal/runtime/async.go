// Package runtime provides asynchronous execution engine.
package runtime

import (
	"context"
	"errors"
	"sync"
	"sync/atomic"
	"time"
)

// AsyncEngine provides high-level asynchronous execution with
// dependency tracking, cancellation, and streaming results.
type AsyncEngine struct {
	scheduler *WorkStealingScheduler
	tasks     map[string]*AsyncTask
	taskOrder []string
	deps      map[string][]string
	results   map[string]interface{}
	errors    map[string]error
	mu        sync.RWMutex
	ctx       context.Context
	cancel    context.CancelFunc
	running   atomic.Bool
	eventCh   chan TaskEvent
	streamCh  chan StreamResult
}

// AsyncTask represents an asynchronous task with dependencies.
type AsyncTask struct {
	ID         string
	Fn         func(ctx context.Context) (interface{}, error)
	Deps       []string
	Priority   int
	Timeout    time.Duration
	Retries    int
	RetryDelay time.Duration
	Metadata   map[string]string
}

// TaskEvent represents a task lifecycle event.
type TaskEvent struct {
	Type      EventType
	TaskID    string
	Timestamp time.Time
	Error     error
	Result    interface{}
}

// EventType represents the type of task event.
type EventType int

const (
	EventTaskCreated EventType = iota
	EventTaskQueued
	EventTaskStarted
	EventTaskCompleted
	EventTaskFailed
	EventTaskCancelled
	EventTaskRetried
)

// StreamResult represents a streaming result from a task.
type StreamResult struct {
	TaskID string
	Data   interface{}
	Index  int
	IsLast bool
	Error  error
}

// NewAsyncEngine creates a new async execution engine.
func NewAsyncEngine(workers int) *AsyncEngine {
	ctx, cancel := context.WithCancel(context.Background())
	ae := &AsyncEngine{
		scheduler: NewWorkStealingScheduler(workers),
		tasks:     make(map[string]*AsyncTask),
		deps:      make(map[string][]string),
		results:   make(map[string]interface{}),
		errors:    make(map[string]error),
		ctx:       ctx,
		cancel:    cancel,
		eventCh:   make(chan TaskEvent, 1024),
		streamCh:  make(chan StreamResult, 1024),
	}
	ae.running.Store(true)
	return ae
}

// AddTask adds a task to the execution graph.
func (ae *AsyncEngine) AddTask(task *AsyncTask) error {
	ae.mu.Lock()
	defer ae.mu.Unlock()

	if ae.tasks[task.ID] != nil {
		return errors.New("task already exists: " + task.ID)
	}

	for _, dep := range task.Deps {
		if ae.tasks[dep] == nil {
			return errors.New("dependency not found: " + dep)
		}
	}

	ae.tasks[task.ID] = task
	ae.deps[task.ID] = task.Deps
	ae.taskOrder = append(ae.taskOrder, task.ID)

	ae.emitEvent(TaskEvent{
		Type:      EventTaskCreated,
		TaskID:    task.ID,
		Timestamp: time.Now(),
	})

	return nil
}

// Execute runs the task graph to completion.
func (ae *AsyncEngine) Execute() error {
	ae.mu.RLock()
	taskCount := len(ae.tasks)
	ae.mu.RUnlock()

	if taskCount == 0 {
		return nil
	}

	completed := make(map[string]bool)
	var completedCount atomic.Int32
	var firstErr error
	var errMu sync.Mutex

	// executeTask executes a single task with retries and timeout.
	var executeTask func(taskID string) error
	executeTask = func(taskID string) error {
		ae.mu.RLock()
		task := ae.tasks[taskID]
		ae.mu.RUnlock()

		if task == nil {
			return errors.New("task not found: " + taskID)
		}

		ae.emitEvent(TaskEvent{
			Type:      EventTaskStarted,
			TaskID:    taskID,
			Timestamp: time.Now(),
		})

		taskCtx := ae.ctx
		if task.Timeout > 0 {
			var cancel context.CancelFunc
			taskCtx, cancel = context.WithTimeout(ae.ctx, task.Timeout)
			defer cancel()
		}

		var result interface{}
		var err error
		for attempt := 0; attempt <= task.Retries; attempt++ {
			select {
			case <-taskCtx.Done():
				err = taskCtx.Err()
			case <-ae.ctx.Done():
				err = ae.ctx.Err()
			default:
				result, err = task.Fn(taskCtx)
			}

			if err == nil {
				break
			}

			if attempt < task.Retries {
				ae.emitEvent(TaskEvent{
					Type:      EventTaskRetried,
					TaskID:    taskID,
					Timestamp: time.Now(),
					Error:     err,
				})
				time.Sleep(task.RetryDelay)
			}
		}

		ae.mu.Lock()
		if err != nil {
			ae.errors[taskID] = err
			if firstErr == nil {
				errMu.Lock()
				firstErr = err
				errMu.Unlock()
			}
			ae.emitEvent(TaskEvent{
				Type:      EventTaskFailed,
				TaskID:    taskID,
				Timestamp: time.Now(),
				Error:     err,
			})
		} else {
			ae.results[taskID] = result
			ae.emitEvent(TaskEvent{
				Type:      EventTaskCompleted,
				TaskID:    taskID,
				Timestamp: time.Now(),
				Result:    result,
			})
		}
		ae.mu.Unlock()

		completed[taskID] = true
		completedCount.Add(1)

		ae.scheduleReadyTasks(completed, executeTask)

		return err
	}

	// Initial scheduling
	ae.scheduleReadyTasks(completed, executeTask)

	// Wait for completion
	for completedCount.Load() < int32(taskCount) {
		select {
		case <-ae.ctx.Done():
			return ae.ctx.Err()
		case <-time.After(10 * time.Millisecond):
			if !ae.hasRunnableTasks(completed) && completedCount.Load() < int32(taskCount) {
				return errors.New("deadlock detected: no runnable tasks")
			}
		}
	}

	return firstErr
}

// scheduleReadyTasks submits tasks whose dependencies are met.
func (ae *AsyncEngine) scheduleReadyTasks(completed map[string]bool, executeTask func(string) error) {
	ae.mu.RLock()
	defer ae.mu.RUnlock()

	for _, taskID := range ae.taskOrder {
		if completed[taskID] {
			continue
		}

		task := ae.tasks[taskID]
		ready := true
		for _, dep := range task.Deps {
			if !completed[dep] {
				ready = false
				break
			}
		}

		if ready {
			completed[taskID] = true
			// The scheduler owns the returned future; the async engine
			// tracks completion through its own event stream.
			ae.scheduler.Submit(func() error {
				return executeTask(taskID)
			})
			ae.emitEvent(TaskEvent{
				Type:      EventTaskQueued,
				TaskID:    taskID,
				Timestamp: time.Now(),
			})
		}
	}
}

func (ae *AsyncEngine) hasRunnableTasks(completed map[string]bool) bool {
	ae.mu.RLock()
	defer ae.mu.RUnlock()

	for _, taskID := range ae.taskOrder {
		if completed[taskID] {
			continue
		}
		task := ae.tasks[taskID]
		ready := true
		for _, dep := range task.Deps {
			if !completed[dep] {
				ready = false
				break
			}
		}
		if ready {
			return true
		}
	}
	return false
}

// ExecuteStream executes tasks and streams results as they complete.
func (ae *AsyncEngine) ExecuteStream() (<-chan StreamResult, error) {
	errCh := make(chan error, 1)

	go func() {
		err := ae.Execute()
		if err != nil {
			errCh <- err
		}
		close(ae.streamCh)
	}()

	go func() {
		for event := range ae.eventCh {
			if event.Type == EventTaskCompleted || event.Type == EventTaskFailed {
				ae.streamCh <- StreamResult{
					TaskID: event.TaskID,
					Data:   event.Result,
					Error:  event.Error,
					IsLast: false,
				}
			}
		}
	}()

	return ae.streamCh, <-errCh
}

// Result returns the result of a completed task.
func (ae *AsyncEngine) Result(taskID string) (interface{}, error) {
	ae.mu.RLock()
	defer ae.mu.RUnlock()

	if err := ae.errors[taskID]; err != nil {
		return nil, err
	}
	return ae.results[taskID], nil
}

// Wait waits for a specific task to complete.
func (ae *AsyncEngine) Wait(taskID string) error {
	for {
		ae.mu.RLock()
		if ae.errors[taskID] != nil || ae.results[taskID] != nil {
			err := ae.errors[taskID]
			ae.mu.RUnlock()
			return err
		}
		ae.mu.RUnlock()

		select {
		case <-ae.ctx.Done():
			return ae.ctx.Err()
		case <-time.After(10 * time.Millisecond):
		}
	}
}

// Cancel cancels all pending tasks.
func (ae *AsyncEngine) Cancel() {
	ae.cancel()
}

// Stop stops the engine and scheduler.
func (ae *AsyncEngine) Stop() {
	ae.cancel()
	ae.scheduler.Stop()
	ae.running.Store(false)
}

// Events returns the event channel for monitoring.
func (ae *AsyncEngine) Events() <-chan TaskEvent {
	return ae.eventCh
}

// emitEvent emits a task event.
func (ae *AsyncEngine) emitEvent(event TaskEvent) {
	select {
	case ae.eventCh <- event:
	default:
	}
}

// Pipeline represents a data processing pipeline with stages.
type Pipeline struct {
	stages      []PipelineStage
	engine      *AsyncEngine
	bufferSize  int
	parallelism int
}

// PipelineStage represents a stage in the pipeline.
type PipelineStage struct {
	Name    string
	Fn      func(ctx context.Context, in <-chan interface{}) (<-chan interface{}, error)
	Workers int
	Buffer  int
}

// NewPipeline creates a new pipeline.
func NewPipeline(bufferSize, parallelism int) *Pipeline {
	return &Pipeline{
		stages:      []PipelineStage{},
		bufferSize:  bufferSize,
		parallelism: parallelism,
	}
}

// AddStage adds a stage to the pipeline.
func (p *Pipeline) AddStage(stage PipelineStage) {
	p.stages = append(p.stages, stage)
}

// Run executes the pipeline with input data.
func (p *Pipeline) Run(ctx context.Context, input <-chan interface{}) (<-chan interface{}, error) {
	if len(p.stages) == 0 {
		return nil, errors.New("pipeline has no stages")
	}

	currentIn := input
	var finalOut <-chan interface{}

	for i, stage := range p.stages {
		isLast := i == len(p.stages)-1
		out := make(chan interface{}, stage.Buffer)
		if isLast {
			finalOut = out
		}

		workers := stage.Workers
		if workers <= 0 {
			workers = p.parallelism
		}

		for w := 0; w < workers; w++ {
			go func(in <-chan interface{}, out chan<- interface{}) {
				defer func() {
					if w == workers-1 {
						close(out)
					}
				}()

				stageOut, err := stage.Fn(ctx, in)
				if err != nil {
					return
				}

				for item := range stageOut {
					select {
					case out <- item:
					case <-ctx.Done():
						return
					}
				}
			}(currentIn, out)
		}

		currentIn = out
	}

	return finalOut, nil
}

// FutureGroup manages a group of related futures.
type FutureGroup struct {
	futures []Future
	mu      sync.Mutex
	done    chan struct{}
}

func NewFutureGroup() *FutureGroup {
	return &FutureGroup{
		futures: []Future{},
		done:    make(chan struct{}),
	}
}

func (fg *FutureGroup) Add(f Future) {
	fg.mu.Lock()
	defer fg.mu.Unlock()
	fg.futures = append(fg.futures, f)
}

func (fg *FutureGroup) Wait() error {
	for _, f := range fg.futures {
		if err := f.Wait(); err != nil {
			return err
		}
	}
	close(fg.done)
	return nil
}

func (fg *FutureGroup) WaitAll() []error {
	errs := make([]error, len(fg.futures))
	for i, f := range fg.futures {
		errs[i] = f.Wait()
	}
	close(fg.done)
	return errs
}

func (fg *FutureGroup) Done() <-chan struct{} {
	return fg.done
}
