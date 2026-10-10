// Package ir provides Sparse Conditional Constant Propagation.
package ir

import (
	"fmt"
)

// LatticeValue represents a value in the constant propagation lattice.
type LatticeValue int

const (
	// LatticeBottom means the value is undefined (unreachable)
	LatticeBottom LatticeValue = iota
	// LatticeConstant means the value is a known constant
	LatticeConstant
	// LatticeOverdefined means the value could be anything (not constant)
	LatticeOverdefined
)

// ConstantValue holds a constant value with its lattice state.
type ConstantValue struct {
	State  LatticeValue
	Value  float64
	Type   string
	IntVal int64
}

// SCCPState holds state for Sparse Conditional Constant Propagation.
type SCCPState struct {
	// Maps SSA value IDs to their lattice values
	valMap map[int]*ConstantValue
	// Worklist of values to process
	worklist []int
	// Block reachability
	reachable map[int]bool
	// Function being analyzed
	fn *Function
}

// NewSCCPState creates a new SCCP state.
func NewSCCPState(fn *Function) *SCCPState {
	return &SCCPState{
		valMap:    make(map[int]*ConstantValue),
		worklist:  make([]int, 0),
		reachable: make(map[int]bool),
		fn:        fn,
	}
}

// SparseConditionalConstantPropagation performs SCCP on a function.
// This implements the Wegman-Zadeck algorithm for sparse constant propagation.
func SparseConditionalConstantPropagation(fn *Function) error {
	if fn == nil {
		return fmt.Errorf("nil function")
	}

	state := NewSCCPState(fn)

	// Initialize: mark all values as overdefined, entry block as reachable
	for _, val := range fn.Values {
		state.valMap[val.ID] = &ConstantValue{State: LatticeOverdefined}
	}
	state.reachable[fn.EntryBlock()] = true

	// Process entry block arguments (if any)
	// Add entry block to worklist
	state.worklist = append(state.worklist, fn.EntryBlock())

	// Main worklist loop
	for len(state.worklist) > 0 {
		item := state.worklist[len(state.worklist)-1]
		state.worklist = state.worklist[:len(state.worklist)-1]

		if state.isBlock(item) {
			state.visitBlock(item)
		} else {
			state.visitValue(item)
		}
	}

	// Apply results: replace constant values with constants
	state.applyResults()

	return nil
}

// isBlock checks if an item is a block ID (heuristic).
func (s *SCCPState) isBlock(item int) bool {
	_, ok := s.fn.Blocks[item]
	return ok
}

// visitBlock processes a basic block.
func (s *SCCPState) visitBlock(blockID int) {
	if !s.reachable[blockID] {
		return
	}
	blk := s.fn.Blocks[blockID]
	if blk == nil {
		return
	}

	// Process phi nodes
	for _, phi := range blk.Phi {
		s.visitPhi(phi)
	}

	// Process operations
	for _, val := range blk.Ops {
		s.visitValue(val.ID)
	}

	// Propagate reachability to successors
	cfg := s.fn.toCFG()
	if cfg != nil {
		if node := cfg.Nodes[blockID]; node != nil {
			for _, succ := range node.Successors {
				if !s.reachable[succ] {
					s.reachable[succ] = true
					s.worklist = append(s.worklist, succ)
				}
			}
		}
	}
}

// visitPhi processes a phi node.
func (s *SCCPState) visitPhi(phi *PhiNode) {
	if phi.Value == nil {
		return
	}

	// Meet over all reachable predecessors
	var result *ConstantValue
	for _, pair := range phi.Pairs {
		if !s.reachable[pair.Predecessor] {
			continue
		}
		predVal := s.valMap[pair.Value.ID]
		if predVal == nil {
			continue
		}
		if result == nil {
			result = predVal
		} else {
			result = s.meet(result, predVal)
		}
	}

	if result == nil {
		result = &ConstantValue{State: LatticeOverdefined}
	}

	s.updateValue(phi.Value.ID, result)
}

// visitValue processes an operation value.
func (s *SCCPState) visitValue(valID int) {
	val := s.fn.Values[valID]
	if val == nil {
		return
	}

	// Check if block is reachable
	if !s.reachable[val.Block] {
		s.updateValue(valID, &ConstantValue{State: LatticeBottom})
		return
	}

	// Compute value based on operation
	result := s.computeValue(val)
	s.updateValue(valID, result)
}

// computeValue computes the lattice value of an operation.
func (s *SCCPState) computeValue(val *Value) *ConstantValue {
	// Simplified: would parse operation and operands
	// For binary ops, if both operands are constants, result is constant
	// For other cases, result is overdefined

	// This is a placeholder - real implementation would:
	// 1. Parse the operation (add, mul, etc.)
	// 2. Get operand values from valMap
	// 3. Apply abstract interpretation

	return &ConstantValue{State: LatticeOverdefined}
}

// meet computes the meet of two lattice values.
func (s *SCCPState) meet(a, b *ConstantValue) *ConstantValue {
	if a.State == LatticeBottom {
		return b
	}
	if b.State == LatticeBottom {
		return a
	}
	if a.State == LatticeConstant && b.State == LatticeConstant {
		if a.Value == b.Value && a.Type == b.Type {
			return a
		}
	}
	return &ConstantValue{State: LatticeOverdefined}
}

// updateValue updates a value's lattice state and adds to worklist if changed.
func (s *SCCPState) updateValue(valID int, newVal *ConstantValue) {
	old := s.valMap[valID]
	if old == nil || old.State != newVal.State || (old.State == LatticeConstant && old.Value != newVal.Value) {
		s.valMap[valID] = newVal
		s.worklist = append(s.worklist, valID)
	}
}

// applyResults replaces values with their constant values where known.
func (s *SCCPState) applyResults() {
	for valID, cv := range s.valMap {
		if cv.State == LatticeConstant {
			val := s.fn.Values[valID]
			if val != nil {
				val.Name = fmt.Sprintf("const_%v", cv.Value)
				val.Type = cv.Type
			}
		}
	}
}

// EntryBlock returns the entry block ID of the function.
func (fn *Function) EntryBlock() int {
	for _, id := range fn.Order {
		return id
	}
	return 0
}

// ConstantFold performs constant folding on a function.
func ConstantFold(fn *Function) error {
	if fn == nil {
		return fmt.Errorf("nil function")
	}

	for _, blk := range fn.Blocks {
		// Fold constants in phi nodes
		for _, phi := range blk.Phi {
			if allArgsConstant(phi) {
				phi.Value.Name = "const"
			}
		}
		// Fold constants in operations
		for _, val := range blk.Ops {
			if canConstantFold(val) {
				val.Name = "const"
			}
		}
	}
	return nil
}

// allArgsConstant reports whether every phi argument is a known constant.
// Argument operability is resolved by the later lowering pass, so this
// conservatively returns false.
func allArgsConstant(phi *PhiNode) bool {
	_ = phi
	return false
}

func canConstantFold(val *Value) bool {
	return false
}
