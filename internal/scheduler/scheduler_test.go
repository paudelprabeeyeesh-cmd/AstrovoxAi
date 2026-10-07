package scheduler

import (
	"sync"
	"testing"
)

func TestDAG_TopologicalOrder(t *testing.T) {
	dag := NewDAG()
	dag.AddTask(&Task{ID: "a"})
	dag.AddTask(&Task{ID: "b", DependsOn: []string{"a"}})
	dag.AddTask(&Task{ID: "c", DependsOn: []string{"b"}})

	order, err := dag.TopologicalOrder()
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if order[0].ID != "a" || order[1].ID != "b" || order[2].ID != "c" {
		t.Errorf("order wrong: %v", order)
	}
}

func TestDAG_Cycle(t *testing.T) {
	dag := NewDAG()
	dag.AddTask(&Task{ID: "a", DependsOn: []string{"b"}})
	dag.AddTask(&Task{ID: "b", DependsOn: []string{"a"}})
	_, err := dag.TopologicalOrder()
	if err == nil {
		t.Error("expected cycle error")
	}
}

func TestFindIndependentSets(t *testing.T) {
	dag := NewDAG()
	dag.AddTask(&Task{ID: "a"})
	dag.AddTask(&Task{ID: "b"})
	dag.AddTask(&Task{ID: "c", DependsOn: []string{"a", "b"}})

	sets, err := FindIndependentSets(dag)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if len(sets) != 2 {
		t.Errorf("got %d sets, want 2", len(sets))
	}
	if len(sets[0].Tasks) != 2 {
		t.Errorf("first set size = %d, want 2", len(sets[0].Tasks))
	}
	if len(sets[1].Tasks) != 1 {
		t.Errorf("second set size = %d, want 1", len(sets[1].Tasks))
	}
}

func TestWorkerPool_RunSet(t *testing.T) {
	wp := NewWorkerPool(2)
	defer wp.Stop()

	var mu sync.Mutex
	results := make([]string, 0)

	tasks := []*Task{
		{ID: "1", Run: func() error { mu.Lock(); results = append(results, "1"); mu.Unlock(); return nil }},
		{ID: "2", Run: func() error { mu.Lock(); results = append(results, "2"); mu.Unlock(); return nil }},
	}

	err := wp.RunSet(IndependentSet{Tasks: tasks})
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	if len(results) != 2 {
		t.Errorf("got %d results, want 2", len(results))
	}
}

func TestWorkerPool_Submit(t *testing.T) {
	wp := NewWorkerPool(1)
	defer wp.Stop()

	called := false
	wp.Submit(&Task{Run: func() error { called = true; return nil }})
	wp.Wait()
	if !called {
		t.Error("task was not called")
	}
}

func TestPriorityQueue_PopTask(t *testing.T) {
	pq := &PriorityQueue{}
	pq.PushTask(&Task{ID: "low"}, 10)
	pq.PushTask(&Task{ID: "high"}, 1)
	pq.PushTask(&Task{ID: "mid"}, 5)

	first := pq.PopTask()
	if first.ID != "high" {
		t.Errorf("first = %s, want high", first.ID)
	}
	second := pq.PopTask()
	if second.ID != "mid" {
		t.Errorf("second = %s, want mid", second.ID)
	}
}

func TestPriorityQueue_Empty(t *testing.T) {
	pq := &PriorityQueue{}
	if got := pq.PopTask(); got != nil {
		t.Errorf("empty pop = %v, want nil", got)
	}
}

func TestDependencyGraph_Dependents(t *testing.T) {
	d := NewDependencyGraph()
	d.AddEdge("a", "b")
	d.AddEdge("a", "c")

	deps := d.Dependents("a")
	if len(deps) != 2 {
		t.Errorf("dependents = %d, want 2", len(deps))
	}
}

func TestDependencyGraph_RemoveTask(t *testing.T) {
	d := NewDependencyGraph()
	d.AddEdge("a", "b")
	d.AddEdge("a", "c")
	d.RemoveTask("a")

	if deps := d.Dependents("a"); len(deps) != 0 {
		t.Errorf("after remove, dependents = %d, want 0", len(deps))
	}
}

func TestEventBus_Publish(t *testing.T) {
	bus := NewEventBus()
	var received string
	bus.Subscribe("test", func(e Event) {
		received = e.Task.ID
	})

	bus.Publish(Event{Type: "test", Task: &Task{ID: "x"}})
	if received != "x" {
		t.Errorf("received = %s, want x", received)
	}
}

func TestDynamicScheduler_SubmitRun(t *testing.T) {
	ds := NewDynamicScheduler()
	ds.Start()
	defer ds.Stop()

	ran := false
	ds.Submit(&Task{ID: "x", Run: func() error { ran = true; return nil }}, 0)
	ds.Run()
	if !ran {
		t.Error("task was not run")
	}
}

func TestLoadBalancer_Assign(t *testing.T) {
	lb := NewLoadBalancer(3)
	w1 := lb.Assign()
	w2 := lb.Assign()
	_ = w1
	_ = w2
	loads := lb.Loads()
	if len(loads) != 3 {
		t.Errorf("loads len = %d, want 3", len(loads))
	}
}

func TestLoadBalancer_Release(t *testing.T) {
	lb := NewLoadBalancer(2)
	w := lb.Assign()
	lb.Release(w)
	loads := lb.Loads()
	if loads[0] != 0 {
		t.Errorf("after release load = %d, want 0", loads[0])
	}
}

func TestHeuristics_Criticality(t *testing.T) {
	h := NewHeuristics()
	dag := NewDAG()
	dag.AddTask(&Task{ID: "a"})
	dag.AddTask(&Task{ID: "b", DependsOn: []string{"a"}})
	dag.AddTask(&Task{ID: "c", DependsOn: []string{"a"}})

	score := h.EstimateCriticality(dag.Nodes["b"], dag)
	if score <= 0 {
		t.Errorf("criticality = %d, want > 0", score)
	}
}

func TestHeuristics_Parallelism(t *testing.T) {
	h := NewHeuristics()
	dag := NewDAG()
	dag.AddTask(&Task{ID: "a"})
	dag.AddTask(&Task{ID: "b"})
	dag.AddTask(&Task{ID: "c", DependsOn: []string{"a", "b"}})

	p := h.EstimateParallelism(dag)
	if p != 2 {
		t.Errorf("parallelism = %d, want 2", p)
	}
}

func TestTaskStruct(t *testing.T) {
	task := Task{ID: "a", Run: func() error { return nil }}
	if task.ID != "a" {
		t.Fatal("unexpected task id")
	}
}

func TestIndependentSetStruct(t *testing.T) {
	set := IndependentSet{Tasks: []*Task{}}
	if len(set.Tasks) != 0 {
		t.Fatal("unexpected tasks")
	}
}

func TestCycleError(t *testing.T) {
	err := &CycleError{missing: "a"}
	if err.Error() != "missing dependency: a" {
		t.Fatalf("unexpected error: %v", err)
	}
}

func TestDAG_Dependents(t *testing.T) {
	dag := NewDAG()
	dag.AddTask(&Task{ID: "a"})
	dag.AddTask(&Task{ID: "b", DependsOn: []string{"a"}})
	deps := dag.Dependents("a")
	if len(deps) != 1 || deps[0] != "b" {
		t.Fatalf("unexpected dependents: %v", deps)
	}
}

func TestEventStruct(t *testing.T) {
	e := Event{Type: "test", Task: &Task{ID: "x"}, Time: 1}
	if e.Type != "test" || e.Task.ID != "x" || e.Time != 1 {
		t.Fatal("unexpected event")
	}
}

func TestNewEventBus(t *testing.T) {
	bus := NewEventBus()
	if bus.handlers == nil {
		t.Fatal("expected handlers map")
	}
}
