package runtime

import (
	"context"
	"sync"

	"github.com/astrovox/astrovox/internal/errors"
	irt "github.com/astrovox/astrovox/internal/runtime"
	"github.com/astrovox/astrovox/tensor"
)

// Future is the handle returned by asynchronous
// submission. It wraps the internal scheduler
// future with typed tensor results.
type Future interface {
	// Wait blocks until the task completes and
	// returns the result.
	Wait() ([]*tensor.Tensor, error)
	// Done reports whether the task completed.
	Done() bool
}

// typedFuture adapts the internal future.
type typedFuture struct {
	inner  irt.Future
	result []*tensor.Tensor
	mu     sync.Mutex
}

// Wait implements Future.
func (f *typedFuture) Wait() ([]*tensor.Tensor, error) {
	if err := f.inner.Wait(); err != nil {
		return nil, err
	}
	f.mu.Lock()
	defer f.mu.Unlock()
	return f.result, nil
}

// Done implements Future.
func (f *typedFuture) Done() bool { return f.inner.Done() }

// setResult stores the task result.
func (f *typedFuture) setResult(out []*tensor.Tensor) {
	f.mu.Lock()
	defer f.mu.Unlock()
	f.result = out
}

// Task is an async execution unit producing
// tensor outputs.
type Task func(ctx context.Context) ([]*tensor.Tensor, error)

// Engine executes tasks asynchronously over a
// worker pool, returning typed futures.
type Engine struct {
	scheduler *irt.Scheduler
	mu        sync.RWMutex
	active    int64
	submitted int64
	completed int64
	failed    int64
}

// NewEngine creates an engine with the given
// worker count. Workers <= 0 selects the
// default pool size.
func NewEngine(workers int) *Engine {
	return &Engine{scheduler: irt.NewScheduler(workers)}
}

// Submit enqueues a task and returns its future. Submission is refused
// with a typed error when the scheduler is stopped (CodeCancelled) or
// its bounded queue is full (CodeQueueFull): backpressure is explicit,
// and a caller is never left with a silently blocked or panicking
// submit.
func (e *Engine) Submit(ctx context.Context, task Task) (Future, error) {
	if task == nil {
		return nil, errors.New(errors.CodeInvalidArgument, "nil task")
	}
	e.mu.Lock()
	e.submitted++
	e.mu.Unlock()
	f := &typedFuture{}
	inner, err := e.scheduler.Submit(func() error {
		e.mu.Lock()
		e.active++
		e.mu.Unlock()
		defer func() {
			e.mu.Lock()
			e.active--
			e.completed++
			e.mu.Unlock()
		}()
		out, err := task(ctx)
		if err != nil {
			e.mu.Lock()
			e.failed++
			e.mu.Unlock()
			return err
		}
		f.setResult(out)
		return nil
	})
	if err != nil {
		e.mu.Lock()
		e.submitted-- // the task never entered the queue
		e.mu.Unlock()
		return nil, err
	}
	f.inner = inner
	return f, nil
}

// SubmitMany enqueues several tasks, stopping at the first refusal.
func (e *Engine) SubmitMany(ctx context.Context, tasks []Task) ([]Future, error) {
	futures := make([]Future, 0, len(tasks))
	for _, t := range tasks {
		f, err := e.Submit(ctx, t)
		if err != nil {
			return futures, err
		}
		futures = append(futures, f)
	}
	return futures, nil
}

// Wait blocks until all futures complete.
func (e *Engine) Wait(futures ...Future) error {
	inner := make([]irt.Future, 0, len(futures))
	for _, f := range futures {
		tf, ok := f.(*typedFuture)
		if !ok {
			return errors.New(errors.CodeInvalidArgument, "foreign future type")
		}
		if tf.inner == nil {
			return errors.New(errors.CodeInvalidArgument, "future not submitted")
		}
		inner = append(inner, tf.inner)
	}
	return e.scheduler.Wait(inner...)
}

// QueueLen reports the number of tasks waiting for a worker.
func (e *Engine) QueueLen() int { return e.scheduler.QueueLen() }

// Stats returns engine counters.
func (e *Engine) Stats() (submitted, active, completed, failed int64) {
	e.mu.RLock()
	defer e.mu.RUnlock()
	return e.submitted, e.active, e.completed, e.failed
}

// Stop shuts down the worker pool. Tasks already
// accepted are drained first.
func (e *Engine) Stop() { e.scheduler.Stop() }
