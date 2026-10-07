package scheduler

import "sync"

// LoadBalancer distributes tasks across workers using round-robin assignment.
type LoadBalancer struct {
	mu    sync.Mutex
	loads []int
	next  int
}

// NewLoadBalancer creates a load balancer with the given worker count.
func NewLoadBalancer(workers int) *LoadBalancer {
	if workers <= 0 {
		workers = 1
	}
	return &LoadBalancer{loads: make([]int, workers)}
}

// Assign selects the next worker and increments its load.
func (lb *LoadBalancer) Assign() int {
	lb.mu.Lock()
	defer lb.mu.Unlock()
	w := lb.next % len(lb.loads)
	lb.next++
	lb.loads[w]++
	return w
}

// Release decrements the load of the given worker.
func (lb *LoadBalancer) Release(worker int) {
	lb.mu.Lock()
	defer lb.mu.Unlock()
	if worker >= 0 && worker < len(lb.loads) && lb.loads[worker] > 0 {
		lb.loads[worker]--
	}
}

// Loads returns a snapshot of per-worker loads.
func (lb *LoadBalancer) Loads() []int {
	lb.mu.Lock()
	defer lb.mu.Unlock()
	return append([]int(nil), lb.loads...)
}
