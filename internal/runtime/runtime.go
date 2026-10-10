package runtime

import (
	"context"
	"errors"
	"runtime"
	"sync"
	"time"
)

// Task represents a unit of work.
type Task func() error

// Future represents the result of an asynchronous task.
type Future interface {
	Wait() error
	Done() bool
}

// Scheduler schedules and executes tasks.
type Scheduler struct {
	workers  int
	tasks    chan func()
	wg       sync.WaitGroup
	ctx      context.Context
	cancel   context.CancelFunc
	stopOnce sync.Once
}

// NewScheduler creates a new scheduler with the given number of workers.
func NewScheduler(workers int) *Scheduler {
	if workers <= 0 {
		workers = runtime.NumCPU()
	}
	ctx, cancel := context.WithCancel(context.Background())
	s := &Scheduler{
		workers: workers,
		tasks:   make(chan func(), workers*4),
		ctx:     ctx,
		cancel:  cancel,
	}
	for i := 0; i < workers; i++ {
		s.wg.Add(1)
		go s.worker()
	}
	return s
}

// worker processes tasks from the queue.
func (s *Scheduler) worker() {
	defer s.wg.Done()
	for {
		select {
		case task, ok := <-s.tasks:
			if !ok {
				return
			}
			task()
		case <-s.ctx.Done():
			return
		}
	}
}

// Submit submits a task for execution.
func (s *Scheduler) Submit(task Task) Future {
	f := &future{
		done: make(chan error, 1),
	}
	s.tasks <- func() {
		err := task()
		select {
		case f.done <- err:
		default:
		}
	}
	return f
}

// SubmitMany submits multiple tasks.
func (s *Scheduler) SubmitMany(tasks []Task) []Future {
	futures := make([]Future, len(tasks))
	for i, task := range tasks {
		futures[i] = s.Submit(task)
	}
	return futures
}

// Wait waits for all futures to complete.
func (s *Scheduler) Wait(futures ...Future) error {
	var firstErr error
	for _, f := range futures {
		if err := f.Wait(); err != nil && firstErr == nil {
			firstErr = err
		}
	}
	return firstErr
}

// Stop stops the scheduler. It is safe to call more than once.
func (s *Scheduler) Stop() {
	s.cancel()
	// Closing the task channel twice would panic, so guard with sync.Once.
	s.stopOnce.Do(func() { close(s.tasks) })
	s.wg.Wait()
}

type future struct {
	done   chan error
	once   sync.Once
	err    error
	isDone bool
}

func (f *future) Wait() error {
	f.once.Do(func() {
		f.err = <-f.done
		f.isDone = true
	})
	return f.err
}

func (f *future) Done() bool {
	if f.isDone {
		return true
	}
	select {
	case <-f.done:
		f.isDone = true
		return true
	default:
		return false
	}
}

// Profiler records execution metrics.
type Profiler struct {
	metrics map[string]time.Duration
	mu      sync.Mutex
}

// NewProfiler creates a new profiler.
func NewProfiler() *Profiler {
	return &Profiler{metrics: make(map[string]time.Duration)}
}

// Time measures the duration of a function.
func (p *Profiler) Time(name string, fn func()) {
	start := time.Now()
	fn()
	elapsed := time.Since(start)
	p.mu.Lock()
	p.metrics[name] += elapsed
	p.mu.Unlock()
}

// Metrics returns recorded metrics.
func (p *Profiler) Metrics() map[string]time.Duration {
	p.mu.Lock()
	defer p.mu.Unlock()
	out := make(map[string]time.Duration)
	for k, v := range p.metrics {
		out[k] = v
	}
	return out
}

// Tracer traces execution flow.
type Tracer struct {
	events []TraceEvent
	mu     sync.Mutex
}

// TraceEvent is a single trace event.
type TraceEvent struct {
	Name  string
	Start time.Time
	End   time.Time
	Error error
	Meta  map[string]string
}

// NewTracer creates a new tracer.
func NewTracer() *Tracer {
	return &Tracer{events: make([]TraceEvent, 0)}
}

// Start begins a trace span.
func (t *Tracer) Start(name string) *TraceSpan {
	span := &TraceSpan{
		tracer: t,
		name:   name,
		start:  time.Now(),
		meta:   make(map[string]string),
	}
	return span
}

// TraceSpan represents a single trace span.
type TraceSpan struct {
	tracer *Tracer
	name   string
	start  time.Time
	end    time.Time
	error  error
	meta   map[string]string
}

// End ends a trace span.
func (s *TraceSpan) End(err error) {
	s.end = time.Now()
	s.error = err
	s.tracer.mu.Lock()
	s.tracer.events = append(s.tracer.events, TraceEvent{
		Name:  s.name,
		Start: s.start,
		End:   s.end,
		Error: err,
		Meta:  s.meta,
	})
	s.tracer.mu.Unlock()
}

// SetMeta sets metadata on a span.
func (s *TraceSpan) SetMeta(key, value string) {
	s.meta[key] = value
}

// Events returns all trace events.
func (t *Tracer) Events() []TraceEvent {
	t.mu.Lock()
	defer t.mu.Unlock()
	out := make([]TraceEvent, len(t.events))
	copy(out, t.events)
	return out
}

// ErrCancelled is returned when a task is cancelled.
var ErrCancelled = errors.New("task cancelled")

// CancellableTask wraps a task with cancellation support.
type CancellableTask struct {
	ctx    context.Context
	cancel context.CancelFunc
}

// NewCancellableTask creates a new cancellable task.
func NewCancellableTask(parent context.Context) *CancellableTask {
	ctx, cancel := context.WithCancel(parent)
	return &CancellableTask{ctx: ctx, cancel: cancel}
}

// Context returns the task context.
func (t *CancellableTask) Context() context.Context {
	return t.ctx
}

// Cancel cancels the task.
func (t *CancellableTask) Cancel() {
	t.cancel()
}

// IsCancelled returns true if the task was cancelled.
func (t *CancellableTask) IsCancelled() bool {
	return t.ctx.Err() != nil
}

// CheckContext checks if the context was cancelled.
func (t *CancellableTask) CheckContext() error {
	if t.ctx.Err() != nil {
		return ErrCancelled
	}
	return nil
}
