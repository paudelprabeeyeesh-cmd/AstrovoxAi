package arch

import "sort"

// FindImportCycles returns all import cycles in the graph as sorted lists
// of package paths, using Tarjan's strongly connected components algorithm.
func (g *DependencyGraph) FindImportCycles() [][]string {
	var (
		index   int
		stack   []string
		onStack = make(map[string]bool)
		indices = make(map[string]int)
		lowlink = make(map[string]int)
		cycles  [][]string
	)

	var strongconnect func(v string)
	strongconnect = func(v string) {
		indices[v] = index
		lowlink[v] = index
		index++
		stack = append(stack, v)
		onStack[v] = true

		for w := range g.edges[v] {
			if _, ok := g.nodes[w]; !ok {
				continue
			}
			if _, visited := indices[w]; !visited {
				strongconnect(w)
				if lowlink[w] < lowlink[v] {
					lowlink[v] = lowlink[w]
				}
			} else if onStack[w] {
				if indices[w] < lowlink[v] {
					lowlink[v] = indices[w]
				}
			}
		}

		if lowlink[v] == indices[v] {
			var scc []string
			for {
				w := stack[len(stack)-1]
				stack = stack[:len(stack)-1]
				onStack[w] = false
				scc = append(scc, w)
				if w == v {
					break
				}
			}
			if len(scc) > 1 {
				sort.Strings(scc)
				cycles = append(cycles, scc)
			}
		}
	}

	for path := range g.nodes {
		if _, ok := indices[path]; !ok {
			strongconnect(path)
		}
	}

	sort.Slice(cycles, func(i, j int) bool {
		return cycles[i][0] < cycles[j][0]
	})
	return cycles
}
