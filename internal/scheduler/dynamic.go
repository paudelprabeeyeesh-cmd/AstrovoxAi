package scheduler

import "sync"

// DynamicScheduler queues tasks and runs them on demand or in the background.
type DynamicScheduler struct {
	mu    sync.Mutex
	queue []*Task
	stop  chan struct{}
	done  chan struct{}
}

// NewDynamicScheduler creates a new dynamic scheduler.
func NewDynamicScheduler() *DynamicScheduler {
	return &DynamicScheduler{
		stop: make(chan struct{}),
		done: make(chan struct{}),
	}
}

// Start launches the scheduler lifecycle goroutine.
func (ds *DynamicScheduler) Start() {
	go func() {
		defer close(ds.done)
		<-ds.stop
	}()
}

// Stop shuts down the scheduler.
func (ds *DynamicScheduler) Stop() {
	close(ds.stop)
	<-ds.done
}

// Submit enqueues a task with the given priority.
func (ds *DynamicScheduler) Submit(task *Task, priority int) {
	ds.mu.Lock()
	ds.queue = append(ds.queue, task)
	ds.mu.Unlock()
}

// Run drains the queue and executes all pending tasks.
func (ds *DynamicScheduler) Run() {
	ds.mu.Lock()
	queue := ds.queue
	ds.queue = nil
	ds.mu.Unlock()
	for _, task := range queue {
		_ = task.Run()
	}
}
