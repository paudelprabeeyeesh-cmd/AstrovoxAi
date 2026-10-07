package graph

import (
	"fmt"
	"io"
	"sort"
	"strings"

	"github.com/astrovox/astrovox/internal/errors"
)

// Visualizer exports graphs in GraphViz DOT format
// with op-class coloring and shape annotations.
type Visualizer struct {
	ShowShapes bool
	ShowAttrs  bool
	Rankdir    string
}

// DefaultVisualizer is the standard configuration.
var DefaultVisualizer = &Visualizer{ShowShapes: true, Rankdir: "LR"}

// DOT renders the graph in GraphViz DOT syntax.
func (v *Visualizer) DOT(g *Graph) (string, error) {
	if g == nil {
		return "", errors.New(errors.CodeInvalidArgument, "nil graph")
	}
	order, err := g.TopologicalSort()
	if err != nil {
		return "", err
	}
	var b strings.Builder
	b.WriteString("digraph astrovox {\n")
	rankdir := v.Rankdir
	if rankdir == "" {
		rankdir = "TB"
	}
	fmt.Fprintf(&b, "  rankdir=%s;\n", rankdir)
	b.WriteString("  node [shape=box, style=filled];\n")
	for _, id := range order {
		n, err := g.Node(id)
		if err != nil {
			return "", err
		}
		color := opColor(n.Op.Name())
		label := n.Op.Name()
		if v.ShowShapes && len(n.OutShapes()) > 0 {
			var dims []string
			for _, s := range n.OutShapes() {
				dims = append(dims, s.String())
			}
			label += " " + strings.Join(dims, "x")
		}
		if v.ShowAttrs && len(n.Attrs) > 0 {
			keys := make([]string, 0, len(n.Attrs))
			for k := range n.Attrs {
				keys = append(keys, k)
			}
			sort.Strings(keys)
			var parts []string
			for _, k := range keys {
				if k == "const" || k == "side_effect" {
					continue
				}
				parts = append(parts, fmt.Sprintf("%s=%v", k, n.Attrs[k]))
			}
			if len(parts) > 0 {
				label += "\\n" + strings.Join(parts, ", ")
			}
		}
		fmt.Fprintf(&b, "  n%d [label=%q, fillcolor=%q];\n", n.ID, label, color)
	}
	for _, e := range g.Edges() {
		fmt.Fprintf(&b, "  n%d -> n%d [label=\"%d→%d\"];\n",
			e.From, e.To, e.FromPort, e.ToPort)
	}
	b.WriteString("}\n")
	return b.String(), nil
}

// WriteDOT writes the DOT rendering to w.
func (v *Visualizer) WriteDOT(g *Graph, w io.Writer) error {
	dot, err := v.DOT(g)
	if err != nil {
		return err
	}
	_, err = w.Write([]byte(dot))
	return err
}

// Summary renders a textual graph summary.
func (v *Visualizer) Summary(g *Graph) (string, error) {
	if g == nil {
		return "", errors.New(errors.CodeInvalidArgument, "nil graph")
	}
	order, err := g.TopologicalSort()
	if err != nil {
		return "", err
	}
	var b strings.Builder
	fmt.Fprintf(&b, "graph %q: %d nodes, %d edges\n",
		g.Name(), g.NodeCount(), g.EdgeCount())
	for _, id := range order {
		n, err := g.Node(id)
		if err != nil {
			return "", err
		}
		var inIDs, outIDs []string
		for _, eid := range n.Inputs {
			e := g.Edges()[eid]
			inIDs = append(inIDs, fmt.Sprintf("n%d", e.From))
		}
		for _, eid := range n.Outputs {
			e := g.Edges()[eid]
			outIDs = append(outIDs, fmt.Sprintf("n%d", e.To))
		}
		fmt.Fprintf(&b, "  n%-4d %-24s in=[%s] out=[%s]\n",
			n.ID, n.Op.Name(), strings.Join(inIDs, " "), strings.Join(outIDs, " "))
	}
	return b.String(), nil
}

// opColor maps op names to GraphViz fill colors.
func opColor(op string) string {
	switch {
	case strings.Contains(op, "const"):
		return "#d4e6f1"
	case strings.Contains(op, "matmul") || strings.Contains(op, "gemm"):
		return "#fdebd0"
	case strings.Contains(op, "conv"):
		return "#fadbd8"
	case strings.Contains(op, "reduce") || strings.Contains(op, "sum"):
		return "#d5f5e3"
	case strings.Contains(op, "fused"):
		return "#e8daef"
	default:
		return "#e5e8e8"
	}
}
