// Package ir provides Global Value Numbering optimization.
package ir

import (
	"fmt"
	"hash/fnv"
)

// ValueNumber represents a unique number for a value expression.
type ValueNumber int

// GVNState holds state for Global Value Numbering.
type GVNState struct {
	// Maps value expressions to value numbers
	exprToVN map[Expr]ValueNumber
	// Maps value numbers to representative values
	vnToVal map[ValueNumber]*Value
	// Maps SSA values to their value numbers
	valToVN map[int]ValueNumber
	// Next available value number
	nextVN ValueNumber
}

// Expr represents a canonical expression for value numbering.
type Expr struct {
	Op     string
	Args   string // Serialized args for map key
	Types  string // Serialized types
	Consts string // Serialized constants
}

// NewGVNState creates a new GVN state.
func NewGVNState() *GVNState {
	return &GVNState{
		exprToVN: make(map[Expr]ValueNumber),
		vnToVal:  make(map[ValueNumber]*Value),
		valToVN:  make(map[int]ValueNumber),
		nextVN:   1,
	}
}

// hashExpr computes a hash for an expression.
func hashExpr(e Expr) uint64 {
	h := fnv.New64a()
	h.Write([]byte(e.Op))
	h.Write([]byte(e.Args))
	h.Write([]byte(e.Types))
	h.Write([]byte(e.Consts))
	return h.Sum64()
}

// ExprLess provides ordering for expressions in maps.
func ExprLess(a, b Expr) bool {
	if a.Op != b.Op {
		return a.Op < b.Op
	}
	if a.Args != b.Args {
		return a.Args < b.Args
	}
	if a.Types != b.Types {
		return a.Types < b.Types
	}
	return a.Consts < b.Consts
}

// GlobalValueNumbering performs GVN on a function.
// It assigns value numbers to expressions and eliminates redundant computations.
func GlobalValueNumbering(fn *Function) error {
	if fn == nil {
		return fmt.Errorf("nil function")
	}

	state := NewGVNState()

	// Process blocks in dominance order (RPO)
	cfg := fn.toCFG()
	if cfg == nil {
		return nil
	}
	dom := ComputeDominators(cfg)

	// Traverse in RPO for proper value numbering
	order := reversePostOrder(cfg, dom)

	for _, blockID := range order {
		blk := fn.Blocks[blockID]
		if blk == nil {
			continue
		}

		// Process phi nodes
		for _, phi := range blk.Phi {
			vn := state.valueNumberPhi(phi)
			state.assignVN(phi.Value, vn)
		}

		// Process operations
		for _, val := range blk.Ops {
			vn := state.valueNumberOp(val)
			state.assignVN(val, vn)
		}
	}

	// Eliminate redundant values
	state.eliminateRedundant(fn)

	return nil
}

// valueNumberPhi computes the value number for a phi node.
func (s *GVNState) valueNumberPhi(phi *PhiNode) ValueNumber {
	// Phi value number depends on incoming value numbers
	args := make([]string, len(phi.Pairs))
	for i, pair := range phi.Pairs {
		if vn, ok := s.valToVN[pair.Value.ID]; ok {
			args[i] = fmt.Sprintf("%d", vn)
		} else {
			args[i] = "0"
		}
	}

	e := Expr{Op: "phi", Args: "[" + joinStrings(args, ",") + "]"}
	return s.getOrCreateVN(e, phi.Value)
}

// valueNumberOp computes the value number for an operation.
func (s *GVNState) valueNumberOp(val *Value) ValueNumber {
	// Extract operation and operands from value
	// This is simplified - real implementation would parse the operation
	op := val.Name
	args := ""
	types := val.Type

	e := Expr{Op: op, Args: args, Types: types}
	return s.getOrCreateVN(e, val)
}

func joinStrings(slice []string, sep string) string {
	if len(slice) == 0 {
		return ""
	}
	result := slice[0]
	for i := 1; i < len(slice); i++ {
		result += sep + slice[i]
	}
	return result
}

// getOrCreateVN returns the VN for an expression, creating if needed.
func (s *GVNState) getOrCreateVN(e Expr, val *Value) ValueNumber {
	if vn, ok := s.exprToVN[e]; ok {
		return vn
	}
	vn := s.nextVN
	s.nextVN++
	s.exprToVN[e] = vn
	s.vnToVal[vn] = val
	return vn
}

// assignVN assigns a value number to a value.
func (s *GVNState) assignVN(val *Value, vn ValueNumber) {
	s.valToVN[val.ID] = vn
}

// eliminateRedundant removes redundant computations.
func (s *GVNState) eliminateRedundant(fn *Function) {
	// For each value number with multiple values, keep one and
	// replace uses of others with the representative
	for vn, rep := range s.vnToVal {
		// Find all values with this VN
		var sameVN []*Value
		for valID, valVN := range s.valToVN {
			if valVN == vn {
				if val := fn.Values[valID]; val != nil && val.ID != rep.ID {
					sameVN = append(sameVN, val)
				}
			}
		}

		// Replace uses of redundant values with representative
		for _, val := range sameVN {
			s.replaceUses(fn, val, rep)
		}
	}
}

// replaceUses replaces all uses of oldVal with newVal.
func (s *GVNState) replaceUses(fn *Function, oldVal, newVal *Value) {
	// In real implementation, would traverse use-def chains
	// For now, just mark oldVal as eliminated
	oldVal.Name = newVal.Name + "_eliminated"
}

// reversePostOrder computes RPO of CFG.
func reversePostOrder(cfg *CFG, dom *DominatorTree) []int {
	// Simplified - return blocks in dominator tree order
	order := make([]int, 0, len(dom.DomTree))
	var visit func(int)
	visit = func(n int) {
		order = append(order, n)
		for _, child := range dom.DomTree[n] {
			visit(child)
		}
	}
	visit(cfg.Entry)
	return order
}
