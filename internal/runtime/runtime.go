package runtime

import (
	"context"
	stderrors "errors"
	"fmt"
	"runtime"
	"sync"
	"time"

	axerrors "github.com/astrovox/astrovox/internal/errors"
)

// Task represents a unit of work.
type Task func() error

// Future represents the result of an asynchronous task.
type Future interface {
	Wait() error
	Done() bool
}

// Errors returned by Submit. They are typed errors, so callers can
// classify failures with errors.Is or CodeOf.
var (
	// ErrQueueFull means the bounded queue rejected the task because it
	// is at capacity: backpressure is explicit, never a silent block.
	ErrQueueFull = axerrors.New(axerrors.CodeQueueFull, "scheduler queue is full")
	// ErrSchedulerStopped means the scheduler was shut down and no
	// longer accepts work.
	ErrSchedulerStopped = axerrors.New(axerrors.CodeCancelled, "scheduler is stopped")
)

// Scheduler schedules and executes tasks.
//
// Concurrency contract: workers drain the bounded queue until the
// channel is closed, so Stop waits for already-accepted work instead of
// abandoning it. Submit is refused (not panicked, not blocked) once the
// scheduler is stopped or the queue is full.
type Scheduler struct {
	workers  int
	tasks    chan func()
	wg       sync.WaitGroup
	ctx      context.Context
	cancel   context.CancelFunc
	stopOnce sync.Once

	// submitMu serializes Submit against Stop's channel close. Without
	// it a Submit racing a Stop sends on a closed channel and panics.
	// The flag is checked under the same lock, so a stopped scheduler
	// can never reach the send.
	submitMu sync.RWMutex
	closed   bool
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

// worker drains tasks until the queue is closed. Draining (rather than
// exiting on ctx cancellation) is what makes Stop wait for accepted
// work: a cancelled context otherwise strands queued tasks with
// futures that never complete.
func (s *Scheduler) worker() {
	defer s.wg.Done()
	for task := range s.tasks {
		task()
	}
}

// QueueLen returns the number of tasks waiting in the queue.
func (s *Scheduler) QueueLen() int { return len(s.tasks) }

// Submit submits a task for execution. It returns ErrSchedulerStopped
// after Stop and ErrQueueFull when the bounded queue is at capacity.
func (s *Scheduler) Submit(task Task) (Future, error) {
	if task == nil {
		return nil, fmt.Errorf("%w: nil task", axerrors.New(axerrors.CodeInvalidArgument, "nil task"))
	}
	s.submitMu.RLock()
	defer s.submitMu.RUnlock()
	if s.closed {
		return nil, fmt.Errorf("%w: cannot submit to a stopped scheduler", ErrSchedulerStopped)
	}
	f := &future{
		done: make(chan error, 1),
	}
	select {
	case s.tasks <- func() {
		err := task()
		select {
		case f.done <- err:
		default:
		}
	}:
		return f, nil
	default:
		return nil, fmt.Errorf("%w: queue holds %d tasks", ErrQueueFull, len(s.tasks))
	}
}

// SubmitMany submits multiple tasks, stopping at the first refusal.
func (s *Scheduler) SubmitMany(tasks []Task) ([]Future, error) {
	futures := make([]Future, 0, len(tasks))
	for _, task := range tasks {
		f, err := s.Submit(task)
		if err != nil {
			return futures, err
		}
		futures = append(futures, f)
	}
	return futures, nil
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

// Stop stops the scheduler. It is safe to call more than once. Tasks
// already accepted are drained before Stop returns.
func (s *Scheduler) Stop() {
	s.cancel()
	s.stopOnce.Do(func() {
		s.submitMu.Lock()
		s.closed = true
		close(s.tasks)
		s.submitMu.Unlock()
	})
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
var ErrCancelled = stderrors.New("task cancelled")

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
