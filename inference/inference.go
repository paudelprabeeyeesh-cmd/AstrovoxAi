// Package inference provides a bounded, cancellable runtime for
// executing models over tensors.
//
// The executor is the single admission point for inference work. It
// enforces, in order: request validation, bounded queue admission
// (backpressure), submission deadlines, bounded worker concurrency, and
// graceful shutdown. Every refusal and failure is a typed error, so a
// caller never has to guess why work did not run.
//
// The executor builds on the existing bounded worker pool
// (github.com/astrovox/astrovox/runtime.Engine) instead of a second
// scheduler: one pool, one set of queue semantics.
package inference

import (
	"context"
	"sync"
	"time"

	"github.com/astrovox/astrovox/internal/errors"
	"github.com/astrovox/astrovox/runtime"
	"github.com/astrovox/astrovox/tensor"
)

// InputKey is the conventional input tensor name.
const InputKey = "input"

// OutputKey is the conventional output tensor name.
const OutputKey = "output"

// Executable is a model the runtime can execute. Implementations must be
// safe to call from the worker pool's goroutines, or must serialize
// internally: the executor does not lock the model itself.
type Executable interface {
	// Forward runs one request. It should honor ctx cancellation
	// between internal steps and return a typed error on failure.
	Forward(ctx context.Context, inputs map[string]*tensor.Tensor) (map[string]*tensor.Tensor, error)
}

// DefaultLimits are conservative bounds: small, bounded requests that
// are cheap to validate before admission.
var DefaultLimits = Limits{
	MaxInputs:         16,
	MaxElements:       1 << 22, // 4M elements per input tensor
	MaxOutputElements: 1 << 22,
}

// Limits bounds a single request. Zero values mean "use the default".
type Limits struct {
	// MaxInputs bounds the number of input tensors per request.
	MaxInputs int
	// MaxElements bounds the element count of any single input tensor.
	MaxElements int64
	// MaxOutputElements bounds the element count of any single output.
	MaxOutputElements int64
}

func (l Limits) withDefaults() Limits {
	if l.MaxInputs <= 0 {
		l.MaxInputs = DefaultLimits.MaxInputs
	}
	if l.MaxElements <= 0 {
		l.MaxElements = DefaultLimits.MaxElements
	}
	if l.MaxOutputElements <= 0 {
		l.MaxOutputElements = DefaultLimits.MaxOutputElements
	}
	return l
}

// Request is one inference job.
type Request struct {
	// ID is the caller's correlation identifier, echoed back on the
	// Result and used only for diagnostics.
	ID string
	// Inputs are the named input tensors.
	Inputs map[string]*tensor.Tensor
	// Deadline is the wall-clock time by which the request must
	// complete; zero means no deadline. An already-expired deadline is
	// refused at submission rather than executed and then declared late.
	Deadline time.Time
}

// Result reports one request's outcome. On failure Outputs is nil and
// Err is set: a failed request never carries partial outputs.
type Result struct {
	ID      string
	Outputs map[string]*tensor.Tensor
	Err     error
	// Wait is the time spent queued before a worker started.
	Wait time.Duration
	// Exec is the time spent executing inside the model.
	Exec time.Duration
}

// Future is the handle for a submitted request.
type Future struct {
	inner runtime.Future
	id    string
	// outputs, wait, and exec are written by the worker before the inner
	// future resolves, so Wait can attach them after inner.Wait returns.
	mu      sync.Mutex
	outputs map[string]*tensor.Tensor
	wait    time.Duration
	exec    time.Duration
	once    sync.Once
	res     Result
}

// Wait blocks until the request completes and returns the result.
func (f *Future) Wait() Result {
	f.once.Do(func() {
		_, err := f.inner.Wait()
		f.mu.Lock()
		f.res = Result{
			ID:      f.id,
			Outputs: f.outputs,
			Wait:    f.wait,
			Exec:    f.exec,
			Err:     err,
		}
		f.mu.Unlock()
	})
	return f.res
}

// Done reports whether the request has completed.
func (f *Future) Done() bool { return f.inner.Done() }

// Stats are executor counters. The set is fixed: no labels derived from
// request content, so a workload cannot explode metric cardinality.
type Stats struct {
	Submitted int64 // requests offered
	Accepted  int64 // requests that entered the queue
	Rejected  int64 // requests refused before execution
	Completed int64 // successful executions
	Failed    int64 // executions that returned an error
	Cancelled int64 // requests cancelled by context
	TimedOut  int64 // requests that exceeded their deadline
	WaitNanos int64 // total queue-wait time across completed requests
	ExecNanos int64 // total execution time across completed requests
	QueueLen  int   // current queue depth
	InFlight  int64 // requests accepted but not yet finished
}

// Executor runs inference requests on a bounded worker pool.
type Executor struct {
	model   Executable
	engine  *runtime.Engine
	limits  Limits
	workers int

	mu     sync.RWMutex
	closed bool
	stats  Stats
}

// NewExecutor builds an executor over the given model with the given
// worker count. Queue capacity follows the engine's rule: four slots
// per worker.
func NewExecutor(model Executable, workers int, limits Limits) (*Executor, error) {
	if model == nil {
		return nil, errors.New(errors.CodeInvalidArgument, "inference executor requires a model")
	}
	if workers <= 0 {
		workers = 1
	}
	return &Executor{
		model:   model,
		engine:  runtime.NewEngine(workers),
		limits:  limits.withDefaults(),
		workers: workers,
	}, nil
}

// Workers reports the configured concurrency.
func (e *Executor) Workers() int { return e.workers }

// Submit validates and enqueues a request. Refusals are typed:
//   - CodeInvalidArgument: malformed request (empty ID, no inputs).
//   - CodeResourceExhausted: request limits exceeded.
//   - CodeTimeout: the deadline has already expired.
//   - CodeCancelled: the executor is shutting down or ctx is done.
//   - CodeQueueFull: the bounded queue is at capacity.
func (e *Executor) Submit(ctx context.Context, req Request) (*Future, error) {
	e.mu.Lock()
	e.stats.Submitted++
	e.mu.Unlock()

	if err := e.validate(req); err != nil {
		e.countRejected()
		return nil, err
	}
	e.mu.RLock()
	closed := e.closed
	e.mu.RUnlock()
	if closed {
		e.countRejected()
		return nil, errors.New(errors.CodeCancelled, "executor is shutting down")
	}
	if !req.Deadline.IsZero() && !time.Now().Before(req.Deadline) {
		e.countRejected()
		return nil, errors.New(errors.CodeTimeout, "request deadline already expired").
			WithField("deadline", req.Deadline.Format(time.RFC3339Nano))
	}
	if err := ctx.Err(); err != nil {
		e.countRejected()
		return nil, errors.Wrap(err, errors.CodeCancelled, "context done before submission")
	}

	f := &Future{id: req.ID}
	submittedAt := time.Now()
	inner, err := e.engine.Submit(ctx, func(taskCtx context.Context) ([]*tensor.Tensor, error) {
		// Re-check the deadline at execution time: the request may have
		// waited in the queue past it.
		if !req.Deadline.IsZero() {
			if !time.Now().Before(req.Deadline) {
				e.countTimedOut()
				return nil, errors.New(errors.CodeTimeout, "request deadline expired in queue")
			}
			var cancel context.CancelFunc
			taskCtx, cancel = context.WithTimeout(taskCtx, time.Until(req.Deadline))
			defer cancel()
		}
		if err := taskCtx.Err(); err != nil {
			e.countCancelled()
			return nil, errors.Wrap(err, errors.CodeCancelled, "request context")
		}
		wait := time.Since(submittedAt)
		execStart := time.Now()
		out, err := e.model.Forward(taskCtx, req.Inputs)
		exec := time.Since(execStart)
		if err != nil {
			// Classify by the task context, not by the model's own
			// error code: a model may report a deadline as any code,
			// and the deadline is a property of the request.
			if taskCtx.Err() == context.DeadlineExceeded {
				e.countTimedOut()
				return nil, errors.New(errors.CodeTimeout, "request deadline exceeded during execution")
			}
			if errors.IsCode(err, errors.CodeTimeout) {
				e.countTimedOut()
			} else {
				e.countFailed()
			}
			return nil, err
		}
		if verr := e.validateOutputs(out); verr != nil {
			e.countFailed()
			return nil, verr
		}
		f.mu.Lock()
		f.outputs = out
		f.wait = wait
		f.exec = exec
		f.mu.Unlock()
		e.countCompleted(wait, exec)
		// The engine plumbing needs a tensor result; the real payload is
		// the map attached above.
		var first *tensor.Tensor
		for _, t := range out {
			first = t
			break
		}
		return []*tensor.Tensor{first}, nil
	})
	if err != nil {
		e.countRejected()
		return nil, err
	}
	e.mu.Lock()
	e.stats.Accepted++
	e.mu.Unlock()
	f.inner = inner
	return f, nil
}

// Run submits a request and blocks for its result.
func (e *Executor) Run(ctx context.Context, req Request) (Result, error) {
	f, err := e.Submit(ctx, req)
	if err != nil {
		return Result{ID: req.ID, Err: err}, err
	}
	res := f.Wait()
	return res, res.Err
}

// Shutdown stops accepting work and waits for accepted requests to
// drain, bounded by timeout. On timeout the executor keeps draining in
// the background and the error reports how many requests were still in
// flight: no result is silently dropped.
func (e *Executor) Shutdown(timeout time.Duration) error {
	e.mu.Lock()
	e.closed = true
	e.mu.Unlock()
	done := make(chan struct{})
	go func() {
		e.engine.Stop()
		close(done)
	}()
	select {
	case <-done:
		return nil
	case <-time.After(timeout):
		return errors.New(errors.CodeTimeout,
			"shutdown timed out: in-flight requests are still draining").
			WithField("in_flight", e.inFlight())
	}
}

// Stats returns a snapshot of the executor counters.
func (e *Executor) Stats() Stats {
	e.mu.RLock()
	defer e.mu.RUnlock()
	s := e.stats
	s.QueueLen = e.engine.QueueLen()
	s.InFlight = e.inFlight()
	return s
}

// validate applies request limits before admission.
func (e *Executor) validate(req Request) error {
	if req.ID == "" {
		return errors.New(errors.CodeInvalidArgument, "request ID is empty")
	}
	if len(req.Inputs) == 0 {
		return errors.New(errors.CodeInvalidArgument, "request has no inputs")
	}
	if len(req.Inputs) > e.limits.MaxInputs {
		return errors.New(errors.CodeResourceExhausted, "request exceeds the input count limit").
			WithField("inputs", len(req.Inputs)).
			WithField("limit", e.limits.MaxInputs)
	}
	if e.limits.MaxElements > 0 {
		for name, t := range req.Inputs {
			if t == nil {
				return errors.New(errors.CodeInvalidArgument, "nil input tensor").
					WithField("name", name)
			}
			if int64(t.NumElements()) > e.limits.MaxElements {
				return errors.New(errors.CodeResourceExhausted, "input exceeds the element limit").
					WithField("name", name).
					WithField("elements", t.NumElements()).
					WithField("limit", e.limits.MaxElements)
			}
		}
	}
	return nil
}

// validateOutputs enforces the output budget after execution. A model
// that returns nil outputs, a nil tensor, or an oversized tensor has
// violated the contract and must fail the request, not the caller.
func (e *Executor) validateOutputs(out map[string]*tensor.Tensor) error {
	if len(out) == 0 {
		return errors.New(errors.CodeInternal, "model returned no outputs")
	}
	if e.limits.MaxOutputElements > 0 {
		for name, t := range out {
			if t == nil {
				return errors.New(errors.CodeInternal, "model returned a nil output").
					WithField("name", name)
			}
			if int64(t.NumElements()) > e.limits.MaxOutputElements {
				return errors.New(errors.CodeResourceExhausted, "model output exceeds the element limit").
					WithField("name", name).
					WithField("elements", t.NumElements()).
					WithField("limit", e.limits.MaxOutputElements)
			}
		}
	}
	return nil
}

func (e *Executor) countRejected() {
	e.mu.Lock()
	e.stats.Rejected++
	e.mu.Unlock()
}

func (e *Executor) countCompleted(wait, exec time.Duration) {
	e.mu.Lock()
	e.stats.Completed++
	e.stats.WaitNanos += int64(wait)
	e.stats.ExecNanos += int64(exec)
	e.mu.Unlock()
}

func (e *Executor) countFailed() {
	e.mu.Lock()
	e.stats.Failed++
	e.mu.Unlock()
}

func (e *Executor) countCancelled() {
	e.mu.Lock()
	e.stats.Cancelled++
	e.stats.Failed++
	e.mu.Unlock()
}

func (e *Executor) countTimedOut() {
	e.mu.Lock()
	e.stats.TimedOut++
	e.stats.Failed++
	e.mu.Unlock()
}

// inFlight counts accepted-but-unfinished requests via the engine's own
// active counter, which decrements when the task closure returns.
func (e *Executor) inFlight() int64 {
	_, active, _, _ := e.engine.Stats()
	return active
}
