package scheduler

// Heuristics estimates scheduling properties of a task DAG.
type Heuristics struct{}

// NewHeuristics creates a new heuristics estimator.
func NewHeuristics() *Heuristics {
	return &Heuristics{}
}

// EstimateCriticality returns a importance score for a task based on its
// transitive dependencies and direct dependents.
func (h *Heuristics) EstimateCriticality(task *Task, dag *DAG) int {
	visited := make(map[string]bool)
	var countDeps func(id string) int
	countDeps = func(id string) int {
		if visited[id] {
			return 0
		}
		visited[id] = true
		total := 0
		if t, ok := dag.Nodes[id]; ok {
			for _, dep := range t.DependsOn {
				total += 1 + countDeps(dep)
			}
		}
		return total
	}
	return countDeps(task.ID) + len(dag.Dependents(task.ID))
}

// EstimateParallelism returns the maximum number of tasks that can run
// concurrently, i.e. the widest level of the dependency DAG.
func (h *Heuristics) EstimateParallelism(dag *DAG) int {
	remaining := make(map[string]bool)
	for id := range dag.Nodes {
		remaining[id] = true
	}

	maxWidth := 0
	for len(remaining) > 0 {
		var ready []string
		for id := range remaining {
			task := dag.Nodes[id]
			allDone := true
			for _, dep := range task.DependsOn {
				if remaining[dep] {
					allDone = false
					break
				}
			}
			if allDone {
				ready = append(ready, id)
			}
		}
		if len(ready) == 0 {
			break
		}
		if len(ready) > maxWidth {
			maxWidth = len(ready)
		}
		for _, id := range ready {
			delete(remaining, id)
		}
	}
	return maxWidth
}
