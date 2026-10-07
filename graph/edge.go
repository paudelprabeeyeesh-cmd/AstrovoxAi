package graph

import "github.com/astrovox/astrovox/internal/errors"

// EdgeSpec is the immutable description used when adding
// an edge to a graph builder.
type EdgeSpec struct {
	From     int
	To       int
	FromPort int
	ToPort   int
}

// Validate checks that an edge connects valid nodes and ports.
func (e EdgeSpec) Validate(nodeCount int, outPorts, inPorts map[int]int) error {
	if e.From < 0 || e.From >= nodeCount {
		return errors.New(errors.CodeInvalidArgument, "edge source node out of range").
			WithField("from", e.From).WithField("nodes", nodeCount)
	}
	if e.To < 0 || e.To >= nodeCount {
		return errors.New(errors.CodeInvalidArgument, "edge target node out of range").
			WithField("to", e.To).WithField("nodes", nodeCount)
	}
	if e.From == e.To {
		return errors.New(errors.CodeCycleDetected, "self-loop edges are forbidden").
			WithField("node", e.From)
	}
	if outPorts != nil {
		if max, ok := outPorts[e.From]; ok && e.FromPort >= max {
			return errors.New(errors.CodeInvalidArgument, "edge source port out of range").
				WithField("port", e.FromPort).WithField("max", max)
		}
	}
	if inPorts != nil {
		if max, ok := inPorts[e.To]; ok && e.ToPort >= max {
			return errors.New(errors.CodeInvalidArgument, "edge target port out of range").
				WithField("port", e.ToPort).WithField("max", max)
		}
	}
	return nil
}
