package arch

import "sort"

// Layer defines an architectural layer as a set of package path prefixes.
// Layers are ordered from highest (outermost) to lowest (innermost);
// dependencies may only flow downward to lower layers.
type Layer struct {
	Name     string
	Packages []string
}

// Violation describes a single architectural rule violation.
type Violation struct {
	From    string
	To      string
	Rule    string
	Message string
}

// DetectLayerViolations checks that dependencies flow downward through the
// given layers. A package belongs to the layer with the longest matching
// prefix. A dependency from layer i to layer j is a violation when j < i.
func DetectLayerViolations(g *DependencyGraph, layers []Layer) []Violation {
	layerOf := make(map[string]int)
	for i, layer := range layers {
		for _, prefix := range layer.Packages {
			if cur, ok := layerOf[prefix]; !ok || len(prefix) > len(layers[cur].Name) {
				layerOf[prefix] = i
			}
		}
	}

	var violations []Violation
	for from, edges := range g.edges {
		fromLayer := layerIndex(layerOf, from)
		if fromLayer < 0 {
			continue
		}
		for to := range edges {
			toLayer := layerIndex(layerOf, to)
			if toLayer < 0 || toLayer > fromLayer {
				continue
			}
			if toLayer == fromLayer {
				continue
			}
			violations = append(violations, Violation{
				From:    from,
				To:      to,
				Rule:    "layer",
				Message: from + " (layer " + layers[fromLayer].Name + ") must not import " + to + " (layer " + layers[toLayer].Name + ")",
			})
		}
	}

	sort.Slice(violations, func(i, j int) bool {
		if violations[i].From != violations[j].From {
			return violations[i].From < violations[j].From
		}
		return violations[i].To < violations[j].To
	})
	return violations
}

// layerIndex returns the index of the layer with the longest matching
// prefix for path, or -1 when no layer matches.
func layerIndex(layerOf map[string]int, path string) int {
	best := -1
	bestLen := -1
	for prefix, idx := range layerOf {
		if len(prefix) > bestLen && (path == prefix || len(path) > len(prefix) && path[:len(prefix)] == prefix) {
			best = idx
			bestLen = len(prefix)
		}
	}
	return best
}
