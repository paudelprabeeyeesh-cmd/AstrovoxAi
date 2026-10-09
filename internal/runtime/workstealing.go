// Package runtime provides a lock-free work-stealing scheduler.
package runtime

import (
	"context"
	"math"
	"runtime"
	"sync"
	"sync/atomic"
	"time"
)

// WorkDeque is a double-ended queue for work-stealing.
// Local pushes/pops happen at the bottom (LIFO for cache locality),
// steals happen at the top (FIFO for fairness).
type WorkDeque struct {
	buffer     []Task
	mask       int
	bottom     uint64 // atomic, only owner writes
	top        uint64 // atomic, owner reads, thieves CAS
	owner      int
	localPop   uint64 // statistics
	localPush  uint64
	stealCount uint64
	stealFail  uint64
}

// GlobalQueue is a lock-free MPMC queue for overflow and
// tasks submitted from non-worker threads.
type GlobalQueue struct {
	buffer []Task
	mask   int
	head   uint64
	tail   uint64
}

// WorkStealingScheduler implements a lock-free work-stealing scheduler
// based on the Chase-Lev deque algorithm.
type WorkStealingScheduler struct {
	workers    int
	deques     []*WorkDeque
	globalQ    *GlobalQueue
	workersWg  sync.WaitGroup
	ctx        context.Context
	cancel     context.CancelFunc
	workerIDs  []int
	stats      SchedulerStats
	running    atomic.Bool
}

// SchedulerStats holds scheduler statistics.
type SchedulerStats struct {
	Workers     int
	LocalPushes uint64
	LocalPops   uint64
	Steals      uint64
	StealFails  uint64
}

// NewWorkStealingScheduler creates a new work-stealing scheduler.
func NewWorkStealingScheduler(workers int) *WorkStealingScheduler {
	if workers <= 0 {
		workers = runtime.NumCPU()
	}

	ctx, cancel := context.WithCancel(context.Background())

	ws := &WorkStealingScheduler{
		workers:   workers,
		deques:    make([]*WorkDeque, workers),
		globalQ:   NewGlobalQueue(workers * 4),
		ctx:       ctx,
		cancel:    cancel,
		workerIDs: make([]int, workers),
	}

	// Initialize deques with power-of-2 sizes for fast modulo
	dequeSize := 1024
	for i := 0; i < workers; i++ {
		ws.deques[i] = NewWorkDeque(dequeSize, i)
		ws.workerIDs[i] = i
	}

	ws.running.Store(true)

	// Start workers
	for i := 0; i < workers; i++ {
		ws.workersWg.Add(1)
		go ws.worker(i)
	}

	return ws
}

// NewWorkDeque creates a new work deque.
func NewWorkDeque(size, owner int) *WorkDeque {
	// Round up to power of 2
	size = 1 << (uint(math.Ceil(math.Log2(float64(size)))))
	return &WorkDeque{
		buffer: make([]Task, size),
		mask:   size - 1,
		owner:  owner,
	}
}

// NewGlobalQueue creates a new global queue.
func NewGlobalQueue(size int) *GlobalQueue {
	size = 1 << (uint(math.Ceil(math.Log2(float64(size)))))
	return &GlobalQueue{
		buffer: make([]Task, size),
		mask:   size - 1,
	}
}

// PushBottom pushes a task to the bottom of the deque (LIFO).
// Only the owner thread calls this.
func (d *WorkDeque) PushBottom(task Task) bool {
	b := atomic.LoadUint64(&d.bottom)
	t := atomic.LoadUint64(&d.top)
	size := b - t
	if size >= uint64(len(d.buffer)) {
		return false
	}
	d.buffer[b&uint64(d.mask)] = task
	atomic.StoreUint64(&d.bottom, b+1)
	atomic.AddUint64(&d.localPush, 1)
	return true
}

// PopBottom pops a task from the bottom of the deque (LIFO).
// Only the owner thread calls this.
func (d *WorkDeque) PopBottom() (Task, bool) {
	b := atomic.LoadUint64(&d.bottom)
	if b == atomic.LoadUint64(&d.top) {
		return nil, false // Empty
	}
	b--
	atomic.StoreUint64(&d.bottom, b)
	task := d.buffer[b&uint64(d.mask)]
	d.buffer[b&uint64(d.mask)] = nil

	t := atomic.LoadUint64(&d.top)
	if b < t {
		atomic.StoreUint64(&d.bottom, b+1)
		return nil, false
	}
	if b == t {
		if !atomic.CompareAndSwapUint64(&d.top, t, t+1) {
			return nil, false
		}
	}
	atomic.AddUint64(&d.localPop, 1)
	return task, true
}

// PopTop steals a task from the top of the deque (FIFO).
// Thief threads call this.
func (d *WorkDeque) PopTop() (Task, bool) {
	for {
		t := atomic.LoadUint64(&d.top)
		b := atomic.LoadUint64(&d.bottom)
		if t >= b {
			atomic.AddUint64(&d.stealFail, 1)
			return nil, false
		}
		task := d.buffer[t&uint64(d.mask)]
		if atomic.CompareAndSwapUint64(&d.top, t, t+1) {
			atomic.AddUint64(&d.stealCount, 1)
			return task, true
		}
	}
}

// Push adds a task to the global queue.
func (g *GlobalQueue) Push(task Task) bool {
	for {
		tail := atomic.LoadUint64(&g.tail)
		head := atomic.LoadUint64(&g.head)
		if tail-head >= uint64(len(g.buffer)) {
			return false
		}
		g.buffer[tail&uint64(g.mask)] = task
		if atomic.CompareAndSwapUint64(&g.tail, tail, tail+1) {
			return true
		}
	}
}

// Pop removes a task from the global queue.
func (g *GlobalQueue) Pop() (Task, bool) {
	for {
		head := atomic.LoadUint64(&g.head)
		tail := atomic.LoadUint64(&g.tail)
		if head >= tail {
			return nil, false
		}
		task := g.buffer[head&uint64(g.mask)]
		if atomic.CompareAndSwapUint64(&g.head, head, head+1) {
			g.buffer[head&uint64(g.mask)] = nil
			return task, true
		}
	}
}

// worker is the main worker loop.
func (ws *WorkStealingScheduler) worker(id int) {
	defer ws.workersWg.Done()
	deque := ws.deques[id]
	rng := NewFastRand(uint64(id))

	for ws.running.Load() {
		if task, ok := deque.PopBottom(); ok {
			task()
			continue
		}

		if task, ok := ws.globalQ.Pop(); ok {
			task()
			continue
		}

		stolen := false
		for i := 0; i < ws.workers; i++ {
			victim := int(rng.Next()) % ws.workers
			if victim == id {
				continue
			}
			if task, ok := ws.deques[victim].PopTop(); ok {
				task()
				stolen = true
				break
			}
		}

		if !stolen {
			runtime.Gosched()
		}
	}
}

	// Submit submits a task to the scheduler.
	func (ws *WorkStealingScheduler) Submit(task Task) Future {
	f := &future{done: make(chan error, 1)}
	wrapped := func() error {
		err := task()
		select {
		case f.done <- err:
		default:
		}
		return err
	}

	idx := int(fastRand()) % ws.workers
	if !ws.deques[idx].PushBottom(wrapped) {
		ws.globalQ.Push(wrapped)
	}
	return f
}

// SubmitToWorker submits a task to a specific worker's deque.
func (ws *WorkStealingScheduler) SubmitToWorker(workerID int, task Task) Future {
	f := &future{done: make(chan error, 1)}
	wrapped := func() error {
		err := task()
		select {
		case f.done <- err:
		default:
		}
		return err
	}

	if workerID >= 0 && workerID < ws.workers {
		ws.deques[workerID].PushBottom(wrapped)
	} else {
		ws.globalQ.Push(wrapped)
	}
	return f
}

// Wait waits for all futures to complete.
func (ws *WorkStealingScheduler) Wait(futures ...Future) error {
	var firstErr error
	for _, f := range futures {
		if err := f.Wait(); err != nil && firstErr == nil {
			firstErr = err
		}
	}
	return firstErr
}

// Stop stops the scheduler.
func (ws *WorkStealingScheduler) Stop() {
	ws.cancel()
	ws.running.Store(false)
	ws.workersWg.Wait()
}

// Stats returns scheduler statistics.
func (ws *WorkStealingScheduler) Stats() SchedulerStats {
	stats := SchedulerStats{
		Workers:     ws.workers,
		LocalPushes: 0,
		LocalPops:   0,
		Steals:      0,
		StealFails:  0,
	}
	for _, d := range ws.deques {
		stats.LocalPushes += atomic.LoadUint64(&d.localPush)
		stats.LocalPops += atomic.LoadUint64(&d.localPop)
		stats.Steals += atomic.LoadUint64(&d.stealCount)
		stats.StealFails += atomic.LoadUint64(&d.stealFail)
	}
	return stats
}

// FastRand is a fast thread-local random number generator.
type FastRand struct {
	state uint64
}

func NewFastRand(seed uint64) *FastRand {
	return &FastRand{state: seed}
}

func (r *FastRand) Next() uint64 {
	r.state = r.state*6364136223846793005 + 1442695040888963407
	return r.state
}

var globalRand = NewFastRand(uint64(time.Now().UnixNano()))

func fastRand() uint64 {
	return globalRand.Next()
}

// PriorityTask represents a task with priority.
type PriorityTask struct {
	Task     Task
	Priority int
}

// PriorityScheduler wraps the work-stealing scheduler with priority support.
type PriorityScheduler struct {
	*WorkStealingScheduler
	highPriority *GlobalQueue
}

func NewPriorityScheduler(workers int) *PriorityScheduler {
	ws := NewWorkStealingScheduler(workers)
	return &PriorityScheduler{
		WorkStealingScheduler: ws,
		highPriority:          NewGlobalQueue(workers * 2),
	}
}

func (ps *PriorityScheduler) SubmitHighPriority(task Task) Future {
	f := &future{done: make(chan error, 1)}
	wrapped := func() error {
		err := task()
		select {
		case f.done <- err:
		default:
		}
		return err
	}
	ps.highPriority.Push(wrapped)
	return f
}

func (ps *PriorityScheduler) worker(id int) {
	defer ps.workersWg.Done()
	deque := ps.deques[id]
	rng := NewFastRand(uint64(id))

	for ps.running.Load() {
		if task, ok := ps.highPriority.Pop(); ok {
			task()
			continue
		}

		if task, ok := deque.PopBottom(); ok {
			task()
			continue
		}

		if task, ok := ps.globalQ.Pop(); ok {
			task()
			continue
		}

		stolen := false
		for i := 0; i < ps.workers; i++ {
			victim := int(rng.Next()) % ps.workers
			if victim == id {
				continue
			}
			if task, ok := ps.deques[victim].PopTop(); ok {
				task()
				stolen = true
				break
			}
		}

		if !stolen {
			runtime.Gosched()
		}
	}
}