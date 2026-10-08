package scheduler

import (
	"sync"
	"testing"
)

func TestDAG_AddTask(t *testing.T) {
	dag := NewDAG()
	dag.AddTask(&Task{ID: "a"})
	if len(dag.Nodes) != 1 {
		t.Fatalf("nodes = %d, want 1", len(dag.Nodes))
	}
}

func TestDAG_TopologicalOrderEmpty(t *testing.T) {
	dag := NewDAG()
	order, err := dag.TopologicalOrder()
	if err != nil {
		t.Fatalf("TopologicalOrder: %v", err)
	}
	if len(order) != 0 {
		t.Fatalf("order len = %d, want 0", len(order))
	}
}

func TestDAG_DependentsMissing(t *testing.T) {
	dag := NewDAG()
	if deps := dag.Dependents("missing"); deps != nil && len(deps) != 0 {
		t.Fatalf("dependents = %v, want empty", deps)
	}
}

func TestDAG_MultipleDependents(t *testing.T) {
	dag := NewDAG()
	dag.AddTask(&Task{ID: "root"})
	dag.AddTask(&Task{ID: "c1", DependsOn: []string{"root"}})
	dag.AddTask(&Task{ID: "c2", DependsOn: []string{"root"}})
	deps := dag.Dependents("root")
	if len(deps) != 2 {
		t.Fatalf("dependents = %d, want 2", len(deps))
	}
}

func TestDAG_MultiLevelDependency(t *testing.T) {
	dag := NewDAG()
	dag.AddTask(&Task{ID: "a"})
	dag.AddTask(&Task{ID: "b", DependsOn: []string{"a"}})
	dag.AddTask(&Task{ID: "c", DependsOn: []string{"b"}})
	order, err := dag.TopologicalOrder()
	if err != nil {
		t.Fatalf("TopologicalOrder: %v", err)
	}
	if order[0].ID != "a" || order[1].ID != "b" || order[2].ID != "c" {
		t.Fatalf("order = %v", order)
	}
}

func TestDAG_CycleDetection_Indirect(t *testing.T) {
	dag := NewDAG()
	dag.AddTask(&Task{ID: "a", DependsOn: []string{"c"}})
	dag.AddTask(&Task{ID: "b", DependsOn: []string{"a"}})
	dag.AddTask(&Task{ID: "c", DependsOn: []string{"b"}})
	_, err := dag.TopologicalOrder()
	if err == nil {
		t.Fatal("expected cycle error")
	}
}

func TestDependencyGraph_AddEdge(t *testing.T) {
	dg := NewDependencyGraph()
	dg.AddEdge("a", "b")
	deps := dg.Dependents("a")
	if len(deps) != 1 || deps[0] != "b" {
		t.Fatalf("dependents = %v, want [b]", deps)
	}
}

func TestDependencyGraph_RemoveSource(t *testing.T) {
	dg := NewDependencyGraph()
	dg.AddEdge("a", "b")
	dg.RemoveTask("a")
	_ = dg.Dependents("a") // should not panic
}

func TestDependencyGraph_MultipleEdges(t *testing.T) {
	dg := NewDependencyGraph()
	dg.AddEdge("a", "c")
	dg.AddEdge("b", "c")
	deps := dg.Dependents("c")
	if len(deps) != 0 {
		t.Fatalf("c dependents = %v, want []", deps)
	}
}

func TestEventBus_MultipleSubscribers(t *testing.T) {
	bus := NewEventBus()
	var count int
	bus.Subscribe("t", func(e Event) { count++ })
	bus.Subscribe("t", func(e Event) { count++ })
	bus.Publish(Event{Type: "t"})
	if count != 2 {
		t.Fatalf("count = %d, want 2", count)
	}
}

func TestEventBus_MultipleTopics(t *testing.T) {
	bus := NewEventBus()
	var got string
	bus.Subscribe("a", func(e Event) { got = e.Type })
	bus.Publish(Event{Type: "a"})
	if got != "a" {
		t.Fatalf("topic = %q, want a", got)
	}
}

func TestDynamicScheduler_EmptyRun(t *testing.T) {
	ds := NewDynamicScheduler()
	ds.Start()
	defer ds.Stop()
	ds.Run() // should not block forever
}

func TestDynamicScheduler_MultipleSubmissions(t *testing.T) {
	ds := NewDynamicScheduler()
	ds.Start()
	defer ds.Stop()
	count := 0
	for i := 0; i < 3; i++ {
		n := i
		ds.Submit(&Task{ID: string(rune('a' + n)), Run: func() error {
			count++
			return nil
		}}, 0)
	}
	ds.Run()
	if count != 3 {
		t.Fatalf("executed = %d, want 3", count)
	}
}

func TestLoadBalancer_MultipleAssign(t *testing.T) {
	lb := NewLoadBalancer(2)
	w0 := lb.Assign()
	w1 := lb.Assign()
	if w0 == w1 {
		t.Fatalf("both assigned to same worker %d", w0)
	}
}

func TestLoadBalancer_Loads(t *testing.T) {
	lb := NewLoadBalancer(4)
	for i := 0; i < 4; i++ {
		lb.Assign()
	}
	loads := lb.Loads()
	if len(loads) != 4 {
		t.Fatalf("loads len = %d, want 4", len(loads))
	}
}

func TestHeuristics_EmptyDAG(t *testing.T) {
	h := NewHeuristics()
	if c := h.EstimateCriticality(&Task{ID: "x"}, NewDAG()); c != 0 {
		t.Fatalf("criticality = %d, want 0", c)
	}
	if p := h.EstimateParallelism(NewDAG()); p != 0 {
		t.Fatalf("parallelism = %d, want 0", p)
	}
}

func TestFindIndependentSets_SingleTask(t *testing.T) {
	dag := NewDAG()
	dag.AddTask(&Task{ID: "a"})
	sets, err := FindIndependentSets(dag)
	if err != nil {
		t.Fatalf("FindIndependentSets: %v", err)
	}
	if len(sets) != 1 || len(sets[0].Tasks) != 1 {
		t.Fatalf("sets = %v", sets)
	}
}

func TestFindIndependentSets_Chain(t *testing.T) {
	dag := NewDAG()
	dag.AddTask(&Task{ID: "a"})
	dag.AddTask(&Task{ID: "b", DependsOn: []string{"a"}})
	dag.AddTask(&Task{ID: "c", DependsOn: []string{"b"}})
	sets, err := FindIndependentSets(dag)
	if err != nil {
		t.Fatalf("FindIndependentSets: %v", err)
	}
	if len(sets) != 3 {
		t.Fatalf("sets = %d, want 3", len(sets))
	}
}

func TestWorkerPool_SubmitMany(t *testing.T) {
	wp := NewWorkerPool(2)
	defer wp.Stop()
	var mu sync.Mutex
	count := 0
	tasks := make([]*Task, 5)
	for i := range tasks {
		n := i
		tasks[i] = &Task{Run: func() error { mu.Lock(); count++; mu.Unlock(); _ = n; return nil }}
	}
	wp.SubmitMany(tasks)
	wp.Wait()
	if count != 5 {
		t.Fatalf("count = %d, want 5", count)
	}
}

func TestWorkerPool_Stop(t *testing.T) {
	wp := NewWorkerPool(1)
	wp.Stop()
}

func TestWorkerPool_RunSetError(t *testing.T) {
	wp := NewWorkerPool(1)
	defer wp.Stop()
	err := wp.RunSet(IndependentSet{Tasks: []*Task{
		{Run: func() error { return nil }},
		{Run: func() error { return nil }},
	}})
	if err != nil {
		t.Fatalf("RunSet: %v", err)
	}
}

func TestPriorityQueue_PushPop(t *testing.T) {
	pq := PriorityQueue{}
	pq.PushTask(&Task{ID: "low"}, 1)
	pq.PushTask(&Task{ID: "high"}, 10)
	task := pq.PopTask()
	if task.ID != "low" {
		t.Fatalf("first pop = %s, want low", task.ID)
	}
}

func TestPriorityQueue_MultiplePops(t *testing.T) {
	pq := PriorityQueue{}
	pq.PushTask(&Task{ID: "a"}, 5)
	pq.PushTask(&Task{ID: "b"}, 3)
	pq.PushTask(&Task{ID: "c"}, 8)
	ids := []string{}
	for task := pq.PopTask(); task != nil; task = pq.PopTask() {
		ids = append(ids, task.ID)
	}
	if len(ids) != 3 {
		t.Fatalf("pops = %d, want 3", len(ids))
	}
}

func TestTask_RunField(t *testing.T) {
	called := false
	task := Task{Run: func() error { called = true; return nil }}
	if err := task.Run(); err != nil || !called {
		t.Fatal("task run not executed")
	}
}

func TestIndependentSet_Struct(t *testing.T) {
	set := IndependentSet{Tasks: []*Task{{ID: "a"}}}
	if len(set.Tasks) != 1 || set.Tasks[0].ID != "a" {
		t.Fatalf("set = %+v", set)
	}
}

func TestCycleError_Message(t *testing.T) {
	e := &CycleError{missing: "test cycle"}
	if e.Error() != "missing dependency: test cycle" {
		t.Fatalf("error = %q, want missing dependency: test cycle", e.Error())
	}
}

func TestEvent_Struct(t *testing.T) {
	e := Event{Type: "t", Task: &Task{ID: "x"}, Time: 1}
	if e.Type != "t" || e.Task.ID != "x" || e.Time != 1 {
		t.Fatalf("event = %+v", e)
	}
}
