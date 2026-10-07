package scheduler

import (
	"context"
	"runtime"
	"sync"
)

// WorkerPool executes tasks in parallel.
type WorkerPool struct {
	workers int
	tasks   chan *Task
	ctx     context.Context
	cancel  context.CancelFunc
	wg      sync.WaitGroup
}

// NewWorkerPool creates a pool with the given worker count.
func NewWorkerPool(workers int) *WorkerPool {
	if workers <= 0 {
		workers = runtime.NumCPU()
	}
	ctx, cancel := context.WithCancel(context.Background())
	wp := &WorkerPool{
		workers: workers,
		tasks:   make(chan *Task, workers*4),
		ctx:     ctx,
		cancel:  cancel,
	}
	for i := 0; i < workers; i++ {
		wp.wg.Add(1)
		go wp.worker()
	}
	return wp
}

func (wp *WorkerPool) worker() {
	defer wp.wg.Done()
	for {
		select {
		case task, ok := <-wp.tasks:
			if !ok {
				return
			}
			_ = task.Run()
		case <-wp.ctx.Done():
			return
		}
	}
}

// Submit enqueues a task.
func (wp *WorkerPool) Submit(task *Task) {
	select {
	case wp.tasks <- task:
	case <-wp.ctx.Done():
	}
}

// SubmitMany enqueues multiple tasks.
func (wp *WorkerPool) SubmitMany(tasks []*Task) {
	for _, task := range tasks {
		wp.Submit(task)
	}
}

// Wait blocks until all submitted tasks complete.
func (wp *WorkerPool) Wait() {
	wp.wg.Wait()
}

// Stop shuts down the pool.
func (wp *WorkerPool) Stop() {
	wp.cancel()
	close(wp.tasks)
	wp.wg.Wait()
}

// RunSet executes an independent set in parallel and waits.
func (wp *WorkerPool) RunSet(set IndependentSet) error {
	var wg sync.WaitGroup
	errCh := make(chan error, len(set.Tasks))
	for _, task := range set.Tasks {
		wg.Add(1)
		go func(t *Task) {
			defer wg.Done()
			errCh <- t.Run()
		}(task)
	}
	wg.Wait()
	close(errCh)

	var first error
	for err := range errCh {
		if err != nil && first == nil {
			first = err
		}
	}
	return first
}
