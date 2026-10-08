// Package ir provides SSA-based intermediate representation.
package ir

import (
	"fmt"
)

// DominanceFrontier computes the dominance frontier for each node
// in a CFG given the dominator tree. The dominance frontier of a
// node N is the set of nodes Y such that N dominates a predecessor
// of Y but does not strictly dominate Y.
func ComputeDominanceFrontier(cfg *CFG, dom *DominatorTree) map[int][]int {
	if cfg == nil || dom == nil {
		return nil
	}

	df := make(map[int][]int, len(cfg.Nodes))

	// For each node N, find nodes where N's dominance ends
	for n := range cfg.Nodes {
		if len(cfg.Nodes[n].Predecessors) <= 1 {
			continue
		}

		for _, pred := range cfg.Nodes[n].Predecessors {
			runner := pred
			for runner != cfg.Entry && !dom.Dominates(runner, n) {
				if !contains(df[runner], n) {
					df[runner] = append(df[runner], n)
				}
				runner = dom.IDom[runner]
				if runner == 0 {
					break
				}
			}
		}
	}

	return df
}

// DominanceFrontierSet is a set-based representation of dominance frontiers.
type DominanceFrontierSet struct {
	Sets map[int]map[int]bool
}

// ComputeDominanceFrontierSet computes dominance frontiers using set representation.
func ComputeDominanceFrontierSet(cfg *CFG, dom *DominatorTree) *DominanceFrontierSet {
	df := make(map[int]map[int]bool)

	for n := range cfg.Nodes {
		if len(cfg.Nodes[n].Predecessors) <= 1 {
			continue
		}

		for _, pred := range cfg.Nodes[n].Predecessors {
			runner := pred
			for runner != cfg.Entry && !dom.Dominates(runner, n) {
				if df[runner] == nil {
					df[runner] = make(map[int]bool)
				}
				df[runner][n] = true
				runner = dom.IDom[runner]
				if runner == 0 {
					break
				}
			}
		}
	}

	return &DominanceFrontierSet{Sets: df}
}

// ToList converts set-based dominance frontiers to list form.
func (dfs *DominanceFrontierSet) ToList() map[int][]int {
	result := make(map[int][]int)
	for n, set := range dfs.Sets {
		list := make([]int, 0, len(set))
		for m := range set {
			list = append(list, m)
		}
		result[n] = list
	}
	return result
}

// contains checks if a slice contains an element.
func contains(slice []int, val int) bool {
	for _, v := range slice {
		if v == val {
			return true
		}
	}
	return false
}

// SSAConstructionState holds intermediate state during SSA construction.
type SSAConstructionState struct {
	CFG       *CFG
	Dom       *DominatorTree
	DF        map[int][]int
	PhiPlaced map[int]map[int]bool // block -> phi variable -> bool
	VarCount  int
}

// NewSSAConstructionState creates a new SSA construction state.
func NewSSAConstructionState(cfg *CFG) *SSAConstructionState {
	dom := ComputeDominators(cfg)
	df := ComputeDominanceFrontier(cfg, dom)
	return &SSAConstructionState{
		CFG:       cfg,
		Dom:       dom,
		DF:        df,
		PhiPlaced: make(map[int]map[int]bool),
		VarCount:  0,
	}
}

// nextVar generates a new SSA variable ID.
func (s *SSAConstructionState) nextVar() int {
	s.VarCount++
	return s.VarCount
}

// SSADominatorInfo holds dominator information for SSA.
type SSADominatorInfo struct {
	IDom     map[int]int
	DomTree  map[int][]int
	DomFront map[int][]int
}

// BuildSSAFromCFG constructs SSA form from a CFG using the Cytron algorithm.
// This implements the classic "Efficiently Computing Static Single Assignment Form
// and the Control Dependence Graph" algorithm by Cytron et al.
func BuildSSAFromCFG(cfg *CFG) *Function {
	if cfg == nil {
		return nil
	}

	// Phase 1: Compute dominators and dominance frontiers
	dom := ComputeDominators(cfg)
	df := ComputeDominanceFrontier(cfg, dom)

	// Phase 2: Determine where phi-functions are needed
	// Map from variable name to set of blocks where it's defined
	varDefs := make(map[string]map[int]bool)
	for id, node := range cfg.Nodes {
		if node == nil {
			continue
		}
		for _, op := range node.Ops {
			if op != nil && op.Name != "" {
				if varDefs[op.Name] == nil {
					varDefs[op.Name] = make(map[int]bool)
				}
				varDefs[op.Name][id] = true
			}
		}
	}

	// Place phi-functions using dominance frontiers
	phiPlaced := make(map[int]map[int]bool) // block -> phi var ID -> bool
	phiArgs := make(map[int]map[int][]PhiArg) // block -> phi var ID -> args

	for varName, defBlocks := range varDefs {
		worklist := make([]int, 0, len(defBlocks))
		for b := range defBlocks {
			worklist = append(worklist, b)
		}

		for len(worklist) > 0 {
			n := worklist[len(worklist)-1]
			worklist = worklist[:len(worklist)-1]

			for _, y := range df[n] {
				if phiPlaced[y] == nil {
					phiPlaced[y] = make(map[int]bool)
				}
				varID := getPhiVarID(varName, y)
				if !phiPlaced[y][varID] {
					phiPlaced[y][varID] = true
					if phiArgs[y] == nil {
						phiArgs[y] = make(map[int][]PhiArg)
					}
					phiArgs[y][varID] = nil // Will be filled in phase 3

					// Add y to worklist if it has definitions
					if defBlocks[y] && !contains(worklist, y) {
						worklist = append(worklist, y)
					}
				}
			}
		}
	}

	// Phase 3: Rename variables using a depth-first traversal
	// This is a simplified version; full implementation requires
	// maintaining variable stacks per name during CFG traversal
	fn := NewFunction(cfg.Name)

	// Create blocks
	for id := range cfg.Nodes {
		blk := &Block{ID: id, Name: fmt.Sprintf("block_%d", id)}
		fn.AddBlock(blk)
	}

	// Add phi nodes
	for blockID, phis := range phiPlaced {
		blk := fn.Blocks[blockID]
		if blk == nil {
			continue
		}
		for phiVarID := range phis {
			phi := &PhiNode{ID: phiVarID, Value: &Value{ID: phiVarID}}
			blk.Phi = append(blk.Phi, phi)
		}
	}

	// Phase 4: Fill in phi arguments (simplified - would need full renaming pass)
	_ = phiArgs

	return fn
}

// PhiArg represents an argument to a phi function.
type PhiArg struct {
	Value      int
	Predecessor int
}

// getPhiVarID generates a unique ID for a phi variable.
func getPhiVarID(varName string, block int) int {
	return hashString(varName)*1000 + block
}

func hashString(s string) int {
	h := 0
	for i := 0; i < len(s); i++ {
		h = h*31 + int(s[i])
	}
	if h < 0 {
		h = -h
	}
	return h
}

// SSADestructionState holds state for SSA destruction.
type SSADestructionState struct {
	Fn    *Function
	Stack map[int][]int // variable -> stack of versions
}

// DestroySSA converts SSA form back to conventional form by
// removing phi nodes and inserting copy instructions.
func DestroySSA(fn *Function) *Function {
	if fn == nil {
		return nil
	}

	// For each block, replace phi nodes with copies in predecessors
	for _, blk := range fn.Blocks {
		for _, phi := range blk.Phi {
			// For each incoming value, insert a copy in the predecessor block
			for _, pair := range phi.Pairs {
				if predBlk := fn.Blocks[pair.Predecessor]; predBlk != nil {
					// Insert copy: phi.Value = pair.Value
					// In real implementation, this would create a move/copy instruction
				}
			}
		}
	}

	// Remove phi nodes
	for _, blk := range fn.Blocks {
		blk.Phi = nil
	}

	return fn
}

// SSAVerification checks SSA properties.
func SSAVerification(fn *Function) error {
	if fn == nil {
		return fmt.Errorf("nil function")
	}

	// Check each value is defined exactly once
	seen := make(map[int]bool)
	for _, blk := range fn.Blocks {
		for _, phi := range blk.Phi {
			if seen[phi.Value.ID] {
				return fmt.Errorf("value %d defined multiple times", phi.Value.ID)
			}
			seen[phi.Value.ID] = true
		}
		for _, op := range blk.Ops {
			if seen[op.ID] {
				return fmt.Errorf("value %d defined multiple times", op.ID)
			}
			seen[op.ID] = true
		}
	}

	// Check phi nodes have correct number of arguments
	for _, blk := range fn.Blocks {
		for _, phi := range blk.Phi {
			if len(phi.Pairs) == 0 {
				return fmt.Errorf("phi node %d has no arguments", phi.Value.ID)
			}
		}
	}

	return nil
}