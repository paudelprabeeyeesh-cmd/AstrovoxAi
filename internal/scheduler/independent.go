package scheduler

// IndependentSet groups tasks that can run in parallel.
type IndependentSet struct {
	Tasks []*Task
}

// FindIndependentSets partitions tasks into independent batches.
func FindIndependentSets(dag *DAG) ([]IndependentSet, error) {
	_, err := dag.TopologicalOrder()
	if err != nil {
		return nil, err
	}

	remaining := make(map[string]bool)
	for id := range dag.Nodes {
		remaining[id] = true
	}

	var sets []IndependentSet
	for len(remaining) > 0 {
		var set IndependentSet
		ready := make(map[string]bool)

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
				ready[id] = true
			}
		}

		for id := range ready {
			delete(remaining, id)
			set.Tasks = append(set.Tasks, dag.Nodes[id])
		}

		if len(set.Tasks) == 0 {
			break
		}
		sets = append(sets, set)
	}

	return sets, nil
}
