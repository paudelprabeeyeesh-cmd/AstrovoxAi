// Package debugger provides a runtime debugger for graph execution:
// breakpoints, stepping, variable inspection, and a trace log.
package debugger

import (
	"errors"
	"fmt"
	"sort"
	"sync"
	"sync/atomic"
	"time"
)

// Debugger errors.
var (
	ErrNoSession  = errors.New("no debug session")
	ErrBreakpoint = errors.New("breakpoint not found")
)

// StepKind identifies a debugger step granularity.
type StepKind int

const (
	StepNode StepKind = iota
	StepMicrobatch
	StepEpoch
)

func (s StepKind) String() string {
	switch s {
	case StepNode:
		return "node"
	case StepMicrobatch:
		return "microbatch"
	case StepEpoch:
		return "epoch"
	default:
		return "unknown"
	}
}

// Breakpoint pauses execution when a node is reached.
type Breakpoint struct {
	ID        int
	Node      string
	Condition func(vars map[string]interface{}) bool
	Hits      atomic.Int64
	Enabled   bool
}

// ShouldBreak reports whether the breakpoint fires for a node state.
func (b *Breakpoint) ShouldBreak(node string, vars map[string]interface{}) bool {
	if !b.Enabled || b.Node != node {
		return false
	}
	if b.Condition != nil && !b.Condition(vars) {
		return false
	}
	b.Hits.Add(1)
	return true
}

// TraceEntry records one execution step.
type TraceEntry struct {
	Seq       int64
	Node      string
	Kind      StepKind
	StartedAt time.Time
	DurUs     int64
	Vars      map[string]interface{}
}

// Debugger controls and inspects execution.
type Debugger struct {
	mu          sync.RWMutex
	session     *Session
	breakpoints []*Breakpoint
	nextBPID    int
	trace       []TraceEntry
	maxTrace    int
	stepping    atomic.Bool
	stepMode    StepKind
	stats       Stats
}

// Stats tracks debugger statistics.
type Stats struct {
	Steps     atomic.Int64
	Breaks    atomic.Int64
	Continues atomic.Int64
	TraceLen  atomic.Int64
}

// NewDebugger creates a debugger.
func NewDebugger(maxTrace int) *Debugger {
	if maxTrace <= 0 {
		maxTrace = 4096
	}
	return &Debugger{maxTrace: maxTrace, stepMode: StepNode}
}

// AddBreakpoint registers a breakpoint.
func (d *Debugger) AddBreakpoint(node string, cond func(map[string]interface{}) bool) *Breakpoint {
	d.mu.Lock()
	defer d.mu.Unlock()
	d.nextBPID++
	bp := &Breakpoint{ID: d.nextBPID, Node: node, Condition: cond, Enabled: true}
	d.breakpoints = append(d.breakpoints, bp)
	return bp
}

// RemoveBreakpoint deletes a breakpoint by id.
func (d *Debugger) RemoveBreakpoint(id int) error {
	d.mu.Lock()
	defer d.mu.Unlock()
	for i, bp := range d.breakpoints {
		if bp.ID == id {
			d.breakpoints = append(d.breakpoints[:i], d.breakpoints[i+1:]...)
			return nil
		}
	}
	return fmt.Errorf("%w: id %d", ErrBreakpoint, id)
}

// Breakpoints returns all breakpoints.
func (d *Debugger) Breakpoints() []*Breakpoint {
	d.mu.RLock()
	defer d.mu.RUnlock()
	return append([]*Breakpoint(nil), d.breakpoints...)
}

// Enable toggles a breakpoint.
func (d *Debugger) Enable(id int, on bool) error {
	d.mu.Lock()
	defer d.mu.Unlock()
	for _, bp := range d.breakpoints {
		if bp.ID == id {
			bp.Enabled = on
			return nil
		}
	}
	return fmt.Errorf("%w: id %d", ErrBreakpoint, id)
}

// Session is an active debug session.
type Session struct {
	Name      string
	StepKind  StepKind
	StartedAt time.Time
	Vars      map[string]interface{}
	LastNode  string
	StepCount int64
	Paused    atomic.Bool
}

// Start begins a session.
func (d *Debugger) Start(name string) *Session {
	d.mu.Lock()
	defer d.mu.Unlock()
	d.session = &Session{
		Name:      name,
		StepKind:  d.stepMode,
		StartedAt: time.Now(),
		Vars:      make(map[string]interface{}),
	}
	return d.session
}

// Stop ends the session.
func (d *Debugger) Stop() {
	d.mu.Lock()
	d.session = nil
	d.mu.Unlock()
}

// Session returns the current session.
func (d *Debugger) Session() *Session {
	d.mu.RLock()
	defer d.mu.RUnlock()
	return d.session
}

// OnNode is called by the runtime before executing a node. It returns
// true when execution should continue.
func (d *Debugger) OnNode(session *Session, node string, vars map[string]interface{}) bool {
	if session == nil {
		return true
	}
	session.LastNode = node
	session.StepCount++
	d.stats.Steps.Add(1)

	d.mu.RLock()
	bps := append([]*Breakpoint(nil), d.breakpoints...)
	d.mu.RUnlock()

	for _, bp := range bps {
		if bp.ShouldBreak(node, vars) {
			session.Paused.Store(true)
			d.stats.Breaks.Add(1)
			// In a full debugger this would block; here we resume at once.
			session.Paused.Store(false)
			d.stats.Continues.Add(1)
			break
		}
	}
	return true
}

// SetVars records variables for inspection.
func (d *Debugger) SetVars(vars map[string]interface{}) {
	d.mu.Lock()
	defer d.mu.Unlock()
	if d.session != nil {
		for k, v := range vars {
			d.session.Vars[k] = v
		}
	}
}

// Vars returns the inspected variables.
func (d *Debugger) Vars() map[string]interface{} {
	d.mu.RLock()
	defer d.mu.RUnlock()
	if d.session == nil {
		return nil
	}
	out := make(map[string]interface{}, len(d.session.Vars))
	for k, v := range d.session.Vars {
		out[k] = v
	}
	return out
}

// Record appends a trace entry.
func (d *Debugger) Record(e TraceEntry) {
	d.mu.Lock()
	defer d.mu.Unlock()
	if e.Seq == 0 {
		e.Seq = int64(len(d.trace) + 1)
	}
	e.StartedAt = time.Now()
	d.trace = append(d.trace, e)
	if len(d.trace) > d.maxTrace {
		d.trace = d.trace[len(d.trace)-d.maxTrace:]
	}
	d.stats.TraceLen.Store(int64(len(d.trace)))
}

// Trace returns the recorded trace.
func (d *Debugger) Trace() []TraceEntry {
	d.mu.RLock()
	defer d.mu.RUnlock()
	return append([]TraceEntry(nil), d.trace...)
}

// TraceForNode filters the trace by node name.
func (d *Debugger) TraceForNode(node string) []TraceEntry {
	d.mu.RLock()
	defer d.mu.RUnlock()
	var out []TraceEntry
	for _, e := range d.trace {
		if e.Node == node {
			out = append(out, e)
		}
	}
	return out
}

// Slowest returns the slowest trace entries.
func (d *Debugger) Slowest(k int) []TraceEntry {
	entries := d.Trace()
	sort.Slice(entries, func(i, j int) bool { return entries[i].DurUs > entries[j].DurUs })
	if k > 0 && len(entries) > k {
		entries = entries[:k]
	}
	return entries
}

// SetStepMode sets the step granularity.
func (d *Debugger) SetStepMode(k StepKind) { d.stepMode = k }

// StepMode returns the step granularity.
func (d *Debugger) StepMode() StepKind { return d.stepMode }

// Stats returns debugger statistics.
func (d *Debugger) Stats() *Stats { return &d.stats }

// Step executes one step under the debugger.
func (d *Debugger) Step(node string, fn func() (map[string]interface{}, error)) error {
	d.mu.RLock()
	sess := d.session
	d.mu.RUnlock()
	if sess == nil {
		return ErrNoSession
	}
	start := time.Now()
	vars, err := fn()
	el := time.Since(start).Microseconds()
	d.OnNode(sess, node, vars)
	if err != nil {
		return err
	}
	if vars != nil {
		d.SetVars(vars)
	}
	d.Record(TraceEntry{Node: node, Kind: d.stepMode, DurUs: el, Vars: vars})
	return nil
}
