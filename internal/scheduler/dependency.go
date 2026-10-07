package scheduler

// DependencyGraph tracks dependency edges between tasks.
type DependencyGraph struct {
	edges map[string]map[string]struct{}
}

// NewDependencyGraph creates an empty dependency graph.
func NewDependencyGraph() *DependencyGraph {
	return &DependencyGraph{edges: make(map[string]map[string]struct{})}
}

// AddEdge records that task "to" depends on task "from".
func (d *DependencyGraph) AddEdge(from, to string) {
	if d.edges[from] == nil {
		d.edges[from] = make(map[string]struct{})
	}
	d.edges[from][to] = struct{}{}
}

// Dependents returns the IDs of tasks that depend on the given task.
func (d *DependencyGraph) Dependents(id string) []string {
	var result []string
	for to := range d.edges[id] {
		result = append(result, to)
	}
	return result
}

// RemoveTask removes a task and all edges referencing it.
func (d *DependencyGraph) RemoveTask(id string) {
	delete(d.edges, id)
	for from := range d.edges {
		delete(d.edges[from], id)
	}
}
