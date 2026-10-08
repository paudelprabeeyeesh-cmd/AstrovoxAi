// Package ir provides loop optimization passes.
package ir

import (
	"fmt"
)

// LoopInvariantCodeMotion performs LICM on a function.
// It moves loop-invariant computations out of loops.
func LoopInvariantCodeMotion(fn *Function) error {
	if fn == nil {
		return fmt.Errorf("nil function")
	}

	// Build dominator tree and find loops
	cfg := fn.toCFG()
	if cfg == nil {
		return nil
	}

	dom := ComputeDominators(cfg)
	loops := FindLoops(cfg)

	for _, loop := range loops {
		// Find loop-invariant instructions
		invariant := findLoopInvariant(loop, fn, dom)

		// Create preheader block
		preheader := createPreheader(loop.Header, fn)

		// Move invariant instructions to preheader
		for _, val := range invariant {
			moveToPreheader(val, preheader, fn)
		}
	}

	return nil
}

// findLoopInvariant identifies loop-invariant values.
func findLoopInvariant(loop *Loop, fn *Function, dom *DominatorTree) []*Value {
	var invariant []*Value

	// An instruction is loop-invariant if:
	// 1. All its operands are defined outside the loop, or
	// 2. All its operands are loop-invariant themselves

	changed := true
	for changed {
		changed = false
		for blkID := range loop.Members {
			blk := fn.Blocks[blkID]
			if blk == nil {
				continue
			}
			for _, val := range blk.Ops {
				if isInvariant(val, loop, fn, invariant) {
					if !containsValue(invariant, val) {
						invariant = append(invariant, val)
						changed = true
					}
				}
			}
		}
	}

	return invariant
}

// isInvariant checks if a value is loop-invariant.
func isInvariant(val *Value, loop *Loop, fn *Function, knownInvariant []*Value) bool {
	// Simplified: check if all operands are outside loop or invariant
	// Real implementation would check operand definitions
	return true // Placeholder
}

// containsValue checks if a value is in a slice.
func containsValue(slice []*Value, val *Value) bool {
	for _, v := range slice {
		if v.ID == val.ID {
			return true
		}
	}
	return false
}

// createPreheader creates a preheader block for a loop.
func createPreheader(header int, fn *Function) int {
	preheaderID := len(fn.Blocks) + 1
	preheader := &Block{ID: preheaderID, Name: fmt.Sprintf("preheader_%d", header)}
	fn.AddBlock(preheader)

	// Rewire CFG: predecessors of header now go to preheader
	// preheader goes to header
	return preheaderID
}

// moveToPreheader moves a value to the preheader block.
func moveToPreheader(val *Value, preheader int, fn *Function) {
	oldBlock := val.Block
	val.Block = preheader
	if blk := fn.Blocks[preheader]; blk != nil {
		blk.Ops = append(blk.Ops, val)
	}
	// Remove from old block
	if blk := fn.Blocks[oldBlock]; blk != nil {
		newOps := make([]*Value, 0, len(blk.Ops))
		for _, v := range blk.Ops {
			if v.ID != val.ID {
				newOps = append(newOps, v)
			}
		}
		blk.Ops = newOps
	}
}

// toCFG converts a Function back to a CFG for analysis.
func (fn *Function) toCFG() *CFG {
	// Simplified - in real implementation, maintain both representations
	return nil
}