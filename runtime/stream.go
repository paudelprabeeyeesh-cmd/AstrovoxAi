package runtime

import (
	"context"
	"sync"

	"github.com/astrovox/astrovox/internal/errors"
	"github.com/astrovox/astrovox/tensor"
)

// Stream is an ordered asynchronous
// execution queue: tasks execute in
// submission order on a dedicated worker,
// and callers synchronize explicitly.
type Stream struct {
	engine *Engine
	mu     sync.Mutex
	tasks  []Task
	closed bool
	// last tracks the tail future so
	// Synchronize waits for everything.
	last Future
}

// NewStream creates a stream backed by
// the engine.
func NewStream(engine *Engine) *Stream {
	return &Stream{engine: engine}
}

// Enqueue appends a task to the stream.
// The returned future completes when the
// task finishes.
func (s *Stream) Enqueue(task Task) (Future, error) {
	s.mu.Lock()
	defer s.mu.Unlock()
	if s.closed {
		return nil, errors.New(errors.CodeInvalidArgument, "stream closed")
	}
	if task == nil {
		return nil, errors.New(errors.CodeInvalidArgument, "nil task")
	}
	s.tasks = append(s.tasks, task)
	ctx := context.Background()
	f, err := s.engine.Submit(ctx, task)
	if err != nil {
		// The task never entered the engine: drop it from the stream so
		// Pending stays honest.
		s.tasks = s.tasks[:len(s.tasks)-1]
		return nil, err
	}
	s.last = f
	return f, nil
}

// EnqueueTensor wraps a tensor-typed task.
func (s *Stream) EnqueueTensor(task func(ctx context.Context) ([]*tensor.Tensor, error)) (Future, error) {
	return s.Enqueue(Task(task))
}

// Synchronize blocks until every enqueued
// task has completed.
func (s *Stream) Synchronize() error {
	s.mu.Lock()
	last := s.last
	s.mu.Unlock()
	if last == nil {
		return nil
	}
	_, err := last.Wait()
	return err
}

// Pending returns the count of enqueued
// tasks not yet synchronized.
func (s *Stream) Pending() int {
	s.mu.Lock()
	defer s.mu.Unlock()
	return len(s.tasks)
}

// Close marks the stream closed after
// synchronizing remaining tasks.
func (s *Stream) Close() error {
	if err := s.Synchronize(); err != nil {
		return err
	}
	s.mu.Lock()
	defer s.mu.Unlock()
	s.closed = true
	s.tasks = nil
	s.last = nil
	return nil
}
