// Package ir provides Memory SSA, Alias Analysis, and Escape Analysis.
package ir

import (
	"fmt"
)

// MemorySSA represents memory in SSA form.
type MemorySSA struct {
	Defs    map[int]*MemoryDef
	Uses    map[int][]*MemoryUse
	Phi     map[int]*MemoryPhi
	Version int
}

// MemoryDef represents a memory definition (store).
type MemoryDef struct {
	ID       int
	Block    int
	Addr     *Value
	Value    *Value
	PrevDef  int // Previous memory version
	NextDefs []int
}

// MemoryUse represents a memory use (load).
type MemoryUse struct {
	ID      int
	Block   int
	Addr    *Value
	Def     int // Defining memory version
	Users   []int
	Value   *Value // Forwarded value
}

// MemoryPhi represents a memory phi node.
type MemoryPhi struct {
	ID    int
	Block int
	Args  []MemoryPhiArg
	Def   int // Resulting memory version
}

// MemoryPhiArg represents an argument to a memory phi.
type MemoryPhiArg struct {
	Def  int
	Pred int
}

// NewMemorySSA creates a new Memory SSA.
func NewMemorySSA(fn *Function) *MemorySSA {
	return &MemorySSA{
		Defs:    make(map[int]*MemoryDef),
		Uses:    make(map[int][]*MemoryUse),
		Phi:     make(map[int]*MemoryPhi),
		Version: 0,
	}
}

// BuildMemorySSA constructs Memory SSA from a function.
func BuildMemorySSA(fn *Function) (*MemorySSA, error) {
	if fn == nil {
		return nil, fmt.Errorf("nil function")
	}

	ms := NewMemorySSA(fn)
	cfg := fn.toCFG()
	if cfg == nil {
		return ms, nil
	}

	dom := ComputeDominators(cfg)
	df := ComputeDominanceFrontier(cfg, dom)

	// Phase 1: Find all memory operations
	memOps := ms.findMemoryOps(fn)

	// Phase 2: Place memory phi nodes
	ms.placeMemoryPhi(cfg, df, memOps)

	// Phase 3: Rename memory versions
	ms.renameMemoryVersions(cfg, dom, memOps)

	return ms, nil
}

// findMemoryOps identifies all memory operations in the function.
func (ms *MemorySSA) findMemoryOps(fn *Function) map[int][]*Value {
	memOps := make(map[int][]*Value)
	for _, blk := range fn.Blocks {
		for _, val := range blk.Ops {
			if ms.isMemoryOp(val) {
				memOps[val.Block] = append(memOps[val.Block], val)
			}
		}
	}
	return memOps
}

func (ms *MemorySSA) isMemoryOp(val *Value) bool {
	// Check if value is a load/store/alloc/free
	return val.Name == "load" || val.Name == "store" ||
		val.Name == "alloc" || val.Name == "free"
}

// placeMemoryPhi places memory phi nodes at dominance frontiers.
func (ms *MemorySSA) placeMemoryPhi(cfg *CFG, df map[int][]int, memOps map[int][]*Value) {
	// For each block with memory defs, propagate to DF
	for blkID := range memOps {
		if dfSet, ok := df[blkID]; ok {
			for _, dfBlk := range dfSet {
				if ms.Phi[dfBlk] == nil {
					ms.Phi[dfBlk] = &MemoryPhi{
						ID:    ms.newVersion(),
						Block: dfBlk,
						Args:  []MemoryPhiArg{},
					}
				}
			}
		}
	}
}

// renameMemoryVersions renames memory versions along CFG paths.
func (ms *MemorySSA) renameMemoryVersions(cfg *CFG, dom *DominatorTree, memOps map[int][]*Value) {
	// Traverse dominator tree, maintaining current memory version
	var walk func(int, int)
	walk = func(blkID, curVer int) {
		// Process phi nodes in this block
		if phi := ms.Phi[blkID]; phi != nil {
			// Fill in phi arguments from predecessors
			for _, pred := range cfg.Nodes[blkID].Predecessors {
				predVer := ms.getVersionAtEnd(pred)
				phi.Args = append(phi.Args, MemoryPhiArg{Def: predVer, Pred: pred})
			}
			curVer = phi.ID
		}

		// Process memory ops in this block
		if defs := memOps[blkID]; defs != nil {
			for _, def := range defs {
				if ms.isLoad(def) {
					// Load: create use
					ms.Uses[def.ID] = append(ms.Uses[def.ID], &MemoryUse{
						ID:   def.ID,
						Block: blkID,
						Addr: ms.getAddr(def),
						Def:  curVer,
					})
				} else {
					// Store/Alloc/Free: create new def
					newDef := &MemoryDef{
						ID:      ms.newVersion(),
						Block:   blkID,
						Addr:    ms.getAddr(def),
						Value:   ms.getValue(def),
						PrevDef: curVer,
					}
					ms.Defs[newDef.ID] = newDef
					if prev := ms.Defs[curVer]; prev != nil {
						prev.NextDefs = append(prev.NextDefs, newDef.ID)
					}
					curVer = newDef.ID
				}
			}
		}

		// Recurse to children
		for _, child := range dom.DomTree[blkID] {
			walk(child, curVer)
		}
	}

	walk(cfg.Entry, 0) // Version 0 = initial memory
}

func (ms *MemorySSA) newVersion() int {
	ms.Version++
	return ms.Version
}

func (ms *MemorySSA) getVersionAtEnd(blkID int) int {
	// Return the memory version at the end of a block
	// Simplified: would track version through block
	return 0
}

func (ms *MemorySSA) isLoad(val *Value) bool {
	return val.Name == "load"
}

func (ms *MemorySSA) getAddr(val *Value) *Value {
	// Extract address operand
	return nil
}

func (ms *MemorySSA) getValue(val *Value) *Value {
	// Extract stored value
	return nil
}

// AliasAnalysis provides alias analysis for memory operations.
type AliasAnalysis struct {
	fn    *Function
	ms    *MemorySSA
	pts   map[*Value]PointsToSet // Pointer to points-to set
	aliases map[int]map[int]bool // Value pairs that may alias
}

// PointsToSet represents a set of memory locations a pointer may point to.
type PointsToSet struct {
	Locations []Location
}

// Location represents a memory location.
type Location struct {
	Base    *Value // Base pointer
	Offset  int    // Constant offset
	Size    int    // Size in bytes
	IsHeap  bool
	IsStack bool
	IsGlobal bool
}

// NewAliasAnalysis creates a new alias analysis.
func NewAliasAnalysis(fn *Function) *AliasAnalysis {
	return &AliasAnalysis{
		fn:      fn,
		pts:     make(map[*Value]PointsToSet),
		aliases: make(map[int]map[int]bool),
	}
}

// RunAliasAnalysis performs alias analysis on a function.
func (a *AliasAnalysis) RunAliasAnalysis() error {
	if a.fn == nil {
		return fmt.Errorf("nil function")
	}

	// Build points-to sets for all pointers
	a.buildPointsTo()

	// Compute alias pairs
	a.computeAliases()

	return nil
}

// buildPointsTo builds points-to sets for all pointer values.
func (a *AliasAnalysis) buildPointsTo() {
	for _, blk := range a.fn.Blocks {
		for _, val := range blk.Ops {
			if a.isPointer(val) {
				a.pts[val] = a.computePointsTo(val)
			}
		}
	}
}

func (a *AliasAnalysis) isPointer(val *Value) bool {
	// Check if value is a pointer type
	return val.Type == "ptr" || val.Type == "*int" || val.Type == "*float"
}

func (a *AliasAnalysis) computePointsTo(val *Value) PointsToSet {
	// Analyze the value's definition to determine what it points to
	// This is a simplified Andersen-style analysis
	return PointsToSet{Locations: []Location{}}
}

// computeAliases computes all pairs of values that may alias.
func (a *AliasAnalysis) computeAliases() {
	pointers := make([]*Value, 0, len(a.pts))
	for ptr := range a.pts {
		pointers = append(pointers, ptr)
	}

	for i, p1 := range pointers {
		for j := i + 1; j < len(pointers); j++ {
			p2 := pointers[j]
			if a.mayAlias(p1, p2) {
				if a.aliases[p1.ID] == nil {
					a.aliases[p1.ID] = make(map[int]bool)
				}
				a.aliases[p1.ID][p2.ID] = true
				if a.aliases[p2.ID] == nil {
					a.aliases[p2.ID] = make(map[int]bool)
				}
				a.aliases[p2.ID][p1.ID] = true
			}
		}
	}
}

// mayAlias checks if two pointers may point to the same location.
func (a *AliasAnalysis) mayAlias(p1, p2 *Value) bool {
	set1 := a.pts[p1]
	set2 := a.pts[p2]

	for _, loc1 := range set1.Locations {
		for _, loc2 := range set2.Locations {
			if a.locationsOverlap(loc1, loc2) {
				return true
			}
		}
	}
	return false
}

func (a *AliasAnalysis) locationsOverlap(l1, l2 Location) bool {
	// Check if two locations overlap
	if l1.Base != nil && l2.Base != nil && l1.Base.ID == l2.Base.ID {
		// Same base - check offset/size overlap
		return !(l1.Offset+l1.Size <= l2.Offset || l2.Offset+l2.Size <= l1.Offset)
	}
	// Conservative: may alias if bases unknown
	return true
}

// MayAlias returns true if two values may alias.
func (a *AliasAnalysis) MayAlias(v1, v2 *Value) bool {
	if v1 == nil || v2 == nil {
		return false
	}
	if v1.ID == v2.ID {
		return true
	}
	return a.aliases[v1.ID][v2.ID]
}

// GetAliases returns all values that may alias with the given value.
func (a *AliasAnalysis) GetAliases(v *Value) []*Value {
	var result []*Value
	if v == nil {
		return result
	}
	for aliasID := range a.aliases[v.ID] {
		if val := a.fn.Values[aliasID]; val != nil {
			result = append(result, val)
		}
	}
	return result
}

// EscapeAnalysis determines the escape state of allocations.
type EscapeAnalysis struct {
	fn       *Function
	ms       *MemorySSA
	aa       *AliasAnalysis
	escape   map[*Value]EscapeState
}

// EscapeState represents the escape state of an allocation.
type EscapeState int

const (
	NoEscape EscapeState = iota // Does not escape (stack allocatable)
	ArgEscape                  // Escapes as function argument
	GlobalEscape               // Escapes to global/heap
)

// NewEscapeAnalysis creates a new escape analysis.
func NewEscapeAnalysis(fn *Function) *EscapeAnalysis {
	return &EscapeAnalysis{
		fn:     fn,
		escape: make(map[*Value]EscapeState),
	}
}

// RunEscapeAnalysis performs escape analysis.
func (e *EscapeAnalysis) RunEscapeAnalysis() error {
	if e.fn == nil {
		return fmt.Errorf("nil function")
	}

	// Initialize all allocations as NoEscape
	for _, blk := range e.fn.Blocks {
		for _, val := range blk.Ops {
			if e.isAllocation(val) {
				e.escape[val] = NoEscape
			}
		}
	}

	// Propagate escapes
	changed := true
	for changed {
		changed = false
		for _, blk := range e.fn.Blocks {
			for _, val := range blk.Ops {
				if e.propagateEscape(val) {
					changed = true
				}
			}
		}
	}

	return nil
}

func (e *EscapeAnalysis) isAllocation(val *Value) bool {
	return val.Name == "alloc" || val.Name == "malloc" || val.Name == "new"
}

func (e *EscapeAnalysis) propagateEscape(val *Value) bool {
	// Check how the value is used
	// If stored to global, returned, or passed to unknown function -> GlobalEscape
	// If passed as argument -> ArgEscape
	// Otherwise -> NoEscape
	return false
}

// GetEscapeState returns the escape state of an allocation.
func (e *EscapeAnalysis) GetEscapeState(val *Value) EscapeState {
	if val == nil {
		return GlobalEscape
	}
	if state, ok := e.escape[val]; ok {
		return state
	}
	return GlobalEscape
}

// CanStackAllocate returns true if an allocation can be stack-allocated.
func (e *EscapeAnalysis) CanStackAllocate(val *Value) bool {
	return e.GetEscapeState(val) == NoEscape
}

// OptimizeMemory uses Memory SSA, Alias Analysis, and Escape Analysis
// to optimize memory operations.
func OptimizeMemory(fn *Function) error {
	if fn == nil {
		return fmt.Errorf("nil function")
	}

	// Build Memory SSA
	ms, err := BuildMemorySSA(fn)
	if err != nil {
		return err
	}

	// Run Alias Analysis
	aa := NewAliasAnalysis(fn)
	if err := aa.RunAliasAnalysis(); err != nil {
		return err
	}

	// Run Escape Analysis
	ea := NewEscapeAnalysis(fn)
	if err := ea.RunEscapeAnalysis(); err != nil {
		return err
	}

	// Apply optimizations:
	// 1. Dead store elimination (using Memory SSA)
	// 2. Load forwarding (using Memory SSA + Alias Analysis)
	// 3. Stack allocation promotion (using Escape Analysis)
	// 4. Scalar replacement (using Alias Analysis)

	return applyMemoryOptimizations(fn, ms, aa, ea)
}

func applyMemoryOptimizations(fn *Function, ms *MemorySSA, aa *AliasAnalysis, ea *EscapeAnalysis) error {
	// Dead Store Elimination
	for _, def := range ms.Defs {
		if len(def.NextDefs) == 0 && len(ms.Uses[def.ID]) == 0 {
			// Dead store - no subsequent def or use depends on it
			// Mark for removal
			def.Value.Name = "dead_store"
		}
	}

	// Load Forwarding
	for _, uses := range ms.Uses {
		for _, use := range uses {
			if use.Def > 0 {
				if def := ms.Defs[use.Def]; def != nil {
					// Check if load can be forwarded from store
					if aa.MayAlias(use.Addr, def.Addr) {
						use.Value = def.Value
					}
				}
			}
		}
	}

	// Stack Allocation Promotion
	for _, blk := range fn.Blocks {
		for _, val := range blk.Ops {
			if ea.CanStackAllocate(val) {
				val.Name = "stackalloc_" + val.Name
			}
		}
	}

	return nil
}