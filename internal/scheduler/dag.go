package scheduler

// Task is a unit of work.
type Task struct {
	ID        string
	Run       func() error
	DependsOn []string
}

// DAG represents a directed acyclic graph of tasks.
type DAG struct {
	Nodes map[string]*Task
}

// NewDAG creates an empty DAG.
func NewDAG() *DAG {
	return &DAG{Nodes: make(map[string]*Task)}
}

// AddTask inserts a task.
func (d *DAG) AddTask(t *Task) {
	d.Nodes[t.ID] = t
}

// Dependents returns tasks that depend on the given task.
func (d *DAG) Dependents(taskID string) []string {
	var result []string
	for _, task := range d.Nodes {
		for _, dep := range task.DependsOn {
			if dep == taskID {
				result = append(result, task.ID)
				break
			}
		}
	}
	return result
}

// TopologicalOrder returns tasks in a valid execution order.
func (d *DAG) TopologicalOrder() ([]*Task, error) {
	inDegree := make(map[string]int)
	children := make(map[string][]string)
	for id := range d.Nodes {
		inDegree[id] = 0
		children[id] = nil
	}
	for _, task := range d.Nodes {
		for _, dep := range task.DependsOn {
			if _, ok := d.Nodes[dep]; !ok {
				return nil, &CycleError{missing: dep}
			}
			inDegree[task.ID]++
			children[dep] = append(children[dep], task.ID)
		}
	}

	var queue []string
	for id, deg := range inDegree {
		if deg == 0 {
			queue = append(queue, id)
		}
	}

	var order []*Task
	for len(queue) > 0 {
		cur := queue[0]
		queue = queue[1:]
		order = append(order, d.Nodes[cur])
		for _, child := range children[cur] {
			inDegree[child]--
			if inDegree[child] == 0 {
				queue = append(queue, child)
			}
		}
	}
	if len(order) != len(d.Nodes) {
		return nil, &CycleError{}
	}
	return order, nil
}

// CycleError indicates a cycle in the DAG.
type CycleError struct {
	missing string
}

func (e *CycleError) Error() string {
	if e.missing != "" {
		return "missing dependency: " + e.missing
	}
	return "cycle detected in task DAG"
}
