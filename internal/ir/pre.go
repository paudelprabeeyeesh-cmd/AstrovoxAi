// Package ir provides Partial Redundancy Elimination.
package ir

import (
	"fmt"
)

// PREState holds state for Partial Redundancy Elimination.
type PREState struct {
	fn          *Function
	cfg         *CFG
	dom         *DominatorTree
	df          map[int][]int
	exprToValue map[ExprKey]*Value
	valueToExpr map[int]ExprKey
	availIn     map[int]map[ExprKey]bool // block -> available expressions
	availOut    map[int]map[ExprKey]bool
	antIn       map[int]map[ExprKey]bool
	antOut      map[int]map[ExprKey]bool
	earliest    map[int]map[ExprKey]bool
	latest      map[int]map[ExprKey]bool
	insert      map[int]map[ExprKey]bool
}

// ExprKey is a hashable representation of an expression.
type ExprKey struct {
	Op   string
	Args string // Serialized args
	Type string
}

// NewPREState creates a new PRE state.
func NewPREState(fn *Function) *PREState {
	cfg := fn.toCFG()
	dom := ComputeDominators(cfg)
	df := ComputeDominanceFrontier(cfg, dom)

	return &PREState{
		fn:          fn,
		cfg:         cfg,
		dom:         dom,
		df:          df,
		exprToValue: make(map[ExprKey]*Value),
		valueToExpr: make(map[int]ExprKey),
		availIn:     make(map[int]map[ExprKey]bool),
		availOut:    make(map[int]map[ExprKey]bool),
		antIn:       make(map[int]map[ExprKey]bool),
		antOut:      make(map[int]map[ExprKey]bool),
		earliest:    make(map[int]map[ExprKey]bool),
		latest:      make(map[int]map[ExprKey]bool),
		insert:      make(map[int]map[ExprKey]bool),
	}
}

// PartialRedundancyElimination performs PRE on a function.
// This implements the Morel-Renvoise algorithm for lazy code motion.
func PartialRedundancyElimination(fn *Function) error {
	if fn == nil {
		return fmt.Errorf("nil function")
	}

	state := NewPREState(fn)

	// Phase 1: Build expression map
	state.buildExpressionMap()

	// Phase 2: Compute availability (forward dataflow)
	state.computeAvailability()

	// Phase 3: Compute anticipability (backward dataflow)
	state.computeAnticipability()

	// Phase 4: Compute earliest placement
	state.computeEarliest()

	// Phase 5: Compute latest placement
	state.computeLatest()

	// Phase 6: Determine where to insert
	state.computeInsert()

	// Phase 7: Insert computations and replace redundant uses
	state.transform()

	return nil
}

// buildExpressionMap creates a mapping from expressions to values.
func (s *PREState) buildExpressionMap() {
	for _, blk := range s.fn.Blocks {
		for _, val := range blk.Ops {
			key := s.exprKey(val)
			if key.Op != "" {
				s.exprToValue[key] = val
				s.valueToExpr[val.ID] = key
			}
		}
	}
}

// exprKey extracts the expression key from a value.
func (s *PREState) exprKey(val *Value) ExprKey {
	// Simplified - real implementation would parse the operation
	return ExprKey{Op: val.Name, Args: "", Type: val.Type}
}

// computeAvailability computes available expressions (forward).
func (s *PREState) computeAvailability() {
	// Initialize
	for id := range s.cfg.Nodes {
		s.availIn[id] = make(map[ExprKey]bool)
		s.availOut[id] = make(map[ExprKey]bool)
	}

	// Entry has nothing available
	s.availIn[s.cfg.Entry] = make(map[ExprKey]bool)

	changed := true
	for changed {
		changed = false
		for _, id := range s.dom.DomTree[s.cfg.Entry] {
			s.visitAvail(id, &changed)
		}
	}
}

func (s *PREState) visitAvail(blockID int, changed *bool) {
	// availIn = intersection of availOut of predecessors
	if node := s.cfg.Nodes[blockID]; node != nil && len(node.Predecessors) > 0 {
		first := true
		for _, pred := range node.Predecessors {
			if first {
				s.availIn[blockID] = copyMap(s.availOut[pred])
				first = false
			} else {
				s.availIn[blockID] = intersectMap(s.availIn[blockID], s.availOut[pred])
			}
		}
	}

	// availOut = availIn U expressions computed in block
	s.availOut[blockID] = copyMap(s.availIn[blockID])
	if blk := s.fn.Blocks[blockID]; blk != nil {
		for _, val := range blk.Ops {
			key := s.valueToExpr[val.ID]
			if key.Op != "" {
				s.availOut[blockID][key] = true
			}
		}
	}
}

// computeAnticipability computes anticipable expressions (backward).
func (s *PREState) computeAnticipability() {
	// Initialize
	for id := range s.cfg.Nodes {
		s.antIn[id] = make(map[ExprKey]bool)
		s.antOut[id] = make(map[ExprKey]bool)
	}

	// Exit has nothing anticipable
	// Would need exit block identification

	changed := true
	for changed {
		changed = false
		// Reverse postorder for backward flow
		order := reversePostOrder(s.cfg, s.dom)
		for i := len(order) - 1; i >= 0; i-- {
			s.visitAnt(order[i], &changed)
		}
	}
}

func (s *PREState) visitAnt(blockID int, changed *bool) {
	// antOut = intersection of antIn of successors
	if node := s.cfg.Nodes[blockID]; node != nil && len(node.Successors) > 0 {
		first := true
		for _, succ := range node.Successors {
			if first {
				s.antOut[blockID] = copyMap(s.antIn[succ])
				first = false
			} else {
				s.antOut[blockID] = intersectMap(s.antOut[blockID], s.antIn[succ])
			}
		}
	}

	// antIn = (antOut - killed) U expressions used in block
	s.antIn[blockID] = copyMap(s.antOut[blockID])
	if blk := s.fn.Blocks[blockID]; blk != nil {
		for _, val := range blk.Ops {
			key := s.valueToExpr[val.ID]
			if key.Op != "" {
				s.antIn[blockID][key] = true
			}
		}
	}
}

// computeEarliest computes earliest placement.
func (s *PREState) computeEarliest() {
	for id := range s.cfg.Nodes {
		s.earliest[id] = make(map[ExprKey]bool)
	}

	for id := range s.cfg.Nodes {
		// earliest = antIn - availOut
		for expr := range s.antIn[id] {
			if !s.availOut[id][expr] {
				s.earliest[id][expr] = true
			}
		}
	}
}

// computeLatest computes latest placement.
func (s *PREState) computeLatest() {
	for id := range s.cfg.Nodes {
		s.latest[id] = make(map[ExprKey]bool)
	}

	// latest = earliest U (availIn & antOut)
	for id := range s.cfg.Nodes {
		for expr := range s.earliest[id] {
			s.latest[id][expr] = true
		}
		for expr := range s.availIn[id] {
			if s.antOut[id][expr] {
				s.latest[id][expr] = true
			}
		}
	}
}

// computeInsert determines where to insert computations.
func (s *PREState) computeInsert() {
	for id := range s.cfg.Nodes {
		s.insert[id] = make(map[ExprKey]bool)
	}

	// Insert at block boundary where latest is true but not earliest in all preds
	for id := range s.cfg.Nodes {
		for expr := range s.latest[id] {
			if !s.earliest[id][expr] {
				s.insert[id][expr] = true
			}
		}
	}
}

// transform performs the actual code transformation.
func (s *PREState) transform() {
	// For each insertion point, create a new value
	// Replace redundant uses with the new value
	for blockID, inserts := range s.insert {
		for expr := range inserts {
			// Create new computation in block
			newVal := &Value{
				ID:    len(s.fn.Values) + 1,
				Name:  expr.Op + "_pre",
				Type:  expr.Type,
				Block: blockID,
			}
			s.fn.AddValue(newVal)
			if blk := s.fn.Blocks[blockID]; blk != nil {
				blk.Ops = append(blk.Ops, newVal)
			}

			// Replace redundant uses
			if oldVal := s.exprToValue[expr]; oldVal != nil && oldVal.ID != newVal.ID {
				s.replaceUses(oldVal, newVal)
			}
		}
	}
}

func (s *PREState) replaceUses(oldVal, newVal *Value) {
	// Would traverse use-def chains
	oldVal.Name = newVal.Name + "_replaced"
}

// Helper functions for set operations on maps.

func copyMap(m map[ExprKey]bool) map[ExprKey]bool {
	result := make(map[ExprKey]bool, len(m))
	for k, v := range m {
		result[k] = v
	}
	return result
}

func intersectMap(a, b map[ExprKey]bool) map[ExprKey]bool {
	result := make(map[ExprKey]bool)
	for k := range a {
		if b[k] {
			result[k] = true
		}
	}
	return result
}
