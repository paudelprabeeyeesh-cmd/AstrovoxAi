// Package tools implements the tool registry, execution engine, and agent
// loop in Go.
//
// A tool is the path from model output to a real-world effect, so every one
// is an attack surface. Three rules this package enforces by construction
// rather than by convention:
//
//  1. Arguments are validated against a schema before any tool code runs, so
//     a malformed call never reaches an implementation that assumed a
//     correct one.
//  2. An irreversible action requires an approval that the registry decides,
//     not the tool. A tool cannot approve itself.
//  3. Every call is capped - steps, tokens, time, and repeated identical
//     calls - so a loop that calls the same tool forever stops rather than
//     burning the budget.
//
// The agent loop refuses to run a tool that is not in the registry, rather
// than passing an unknown name through to the executor.
package tools

import (
	"bytes"
	"errors"
	"fmt"
	"strings"
	"sync"
	"time"
)

// ErrToolUnknown is returned when a call names a tool that is not
// registered. It is a distinct error so a caller can tell "you asked for
// something that does not exist" from "the tool failed".
var ErrToolUnknown = errors.New("tools: unknown tool")

// ErrApprovalRequired is returned when a tool needs approval that has not
// been granted.
var ErrApprovalRequired = errors.New("tools: approval required")

// Risk classifies a tool's blast radius.
type Risk string

// Risk levels, lowest first.
const (
	// RiskRead has no side effect.
	RiskRead Risk = "read"
	// RiskWrite changes state but is reversible.
	RiskWrite Risk = "write"
	// RiskExtern sends something outside the process boundary.
	RiskExtern Risk = "external"
	// RiskIrreversible cannot be undone by this system.
	RiskIrreversible Risk = "irreversible"
)

// RequiresApproval reports whether a risk level may proceed unattended.
//
// Only reads are unattended. A write is also unattended because it is
// reversible by design, which is the property the RiskWrite contract
// asserts; an external or irreversible action does not.
func (r Risk) RequiresApproval() bool {
	return r == RiskExtern || r == RiskIrreversible
}

// Schema describes a tool's arguments.
type Schema struct {
	// Name of the tool, unique in the registry.
	Name string
	// Description is shown to the model so it can choose the tool.
	Description string
	// Risk decides whether the call needs approval.
	Risk Risk
	// Actions is what the tool actually does, finer-grained than Risk. A
	// terminal command and a purchase are both irreversible, but an audit that
	// records only "irreversible" cannot tell an operator which happened. Any
	// gated action makes the call gated, so declaring a benign risk alongside a
	// gated action does not bypass the gate.
	Actions []Action
	// Params maps argument name to a validator. A missing validator means
	// the argument is not accepted.
	Params map[string]Param
	// Timeout bounds one execution.
	Timeout time.Duration
}

// Param validates one argument.
type Param struct {
	// Kind is the value's type.
	Kind Kind
	// Required rejects a missing argument rather than defaulting it.
	Required bool
	// MinLength and MaxLength bound strings and slices.
	MinLength int
	MaxLength int
	// Enum restricts a string to these values.
	Enum []string
	// Default is applied when the argument is absent and not required.
	Default interface{}
}

// Kind is an argument's type.
type Kind string

// Supported kinds.
const (
	KindString = "string"
	KindInt    = "int"
	KindFloat  = "float"
	KindBool   = "bool"
	KindList   = "list"
)

// Validate checks arguments against a param spec.
func (p Param) Validate(value interface{}) error {
	switch p.Kind {
	case KindString:
		s, ok := value.(string)
		if !ok {
			return fmt.Errorf("expected a string, got %T", value)
		}
		if p.MinLength > 0 && len(s) < p.MinLength {
			return fmt.Errorf("string shorter than %d", p.MinLength)
		}
		if p.MaxLength > 0 && len(s) > p.MaxLength {
			return fmt.Errorf("string longer than %d", p.MaxLength)
		}
		if len(p.Enum) > 0 {
			for _, allowed := range p.Enum {
				if s == allowed {
					return nil
				}
			}
			return fmt.Errorf("%q is not one of %s", s, strings.Join(p.Enum, ", "))
		}
	case KindInt:
		n, ok := value.(int)
		if !ok {
			// A JSON round trip yields float64, so accept that too.
			f, isFloat := value.(float64)
			if !isFloat || f != float64(int(f)) {
				return fmt.Errorf("expected an integer, got %T", value)
			}
			n = int(f)
		}
		if p.MinLength > 0 && n < p.MinLength {
			return fmt.Errorf("integer below %d", p.MinLength)
		}
		if p.MaxLength > 0 && n > p.MaxLength {
			return fmt.Errorf("integer above %d", p.MaxLength)
		}
	case KindBool:
		if _, ok := value.(bool); !ok {
			return fmt.Errorf("expected a boolean, got %T", value)
		}
	case KindFloat:
		switch value.(type) {
		case float64, float32, int:
		default:
			return fmt.Errorf("expected a number, got %T", value)
		}
	case KindList:
		if _, ok := value.([]interface{}); !ok {
			return fmt.Errorf("expected a list, got %T", value)
		}
	default:
		return fmt.Errorf("unsupported kind %q", p.Kind)
	}
	return nil
}

// Call is a requested invocation.
type Call struct {
	Name string                 `json:"name"`
	Args map[string]interface{} `json:"args"`
}

// Tool is an executable.
type Tool interface {
	// Execute runs with already-validated arguments. It must not re-validate.
	Execute(args map[string]interface{}) (map[string]interface{}, error)
}

// Registry holds tools and validates calls against their schemas.
type Registry struct {
	mu      sync.RWMutex
	tools   map[string]Tool
	schemas map[string]Schema
	// counts is the tool-call budget, keyed by tool+argument fingerprint,
	// so a repeated identical call is detected.
	counts map[string]int
}

// New returns an empty registry.
func New() *Registry {
	return &Registry{
		tools:   map[string]Tool{},
		schemas: map[string]Schema{},
		counts:  map[string]int{},
	}
}

// Register adds a tool and its schema. Both are required: a tool with no
// schema cannot be validated, so it is refused rather than runnable.
func (r *Registry) Register(schema Schema, tool Tool) error {
	if schema.Name == "" {
		return errors.New("tools: a schema needs a name")
	}
	if tool == nil {
		return errors.New("tools: a tool is required with a schema")
	}
	if schema.Timeout <= 0 {
		schema.Timeout = 30 * time.Second
	}
	r.mu.Lock()
	defer r.mu.Unlock()
	if _, exists := r.tools[schema.Name]; exists {
		return fmt.Errorf("tools: %q is already registered", schema.Name)
	}
	r.tools[schema.Name] = tool
	r.schemas[schema.Name] = schema
	return nil
}

// Schema returns a registered tool's schema.
func (r *Registry) Schema(name string) (Schema, bool) {
	r.mu.RLock()
	defer r.mu.RUnlock()
	s, ok := r.schemas[name]
	return s, ok
}

// Names returns the registered tool names, for the model-facing catalogue.
func (r *Registry) Names() []string {
	r.mu.RLock()
	defer r.mu.RUnlock()
	out := make([]string, 0, len(r.tools))
	for n := range r.tools {
		out = append(out, n)
	}
	// Deterministic, so a prompt built from the catalogue is stable.
	for i := 1; i < len(out); i++ {
		for j := i; j > 0 && out[j] < out[j-1]; j-- {
			out[j], out[j-1] = out[j-1], out[j]
		}
	}
	return out
}

// Validate checks a call against its schema. Unknown names are refused here
// rather than by the executor, so an unknown tool is a validation error.
func (r *Registry) Validate(call Call) error {
	r.mu.RLock()
	schema, ok := r.schemas[call.Name]
	r.mu.RUnlock()
	if !ok {
		return fmt.Errorf("%w: %q", ErrToolUnknown, call.Name)
	}
	for name, param := range schema.Params {
		value, present := call.Args[name]
		if !present {
			if param.Required {
				return fmt.Errorf("missing required argument %q", name)
			}
			continue
		}
		if err := param.Validate(value); err != nil {
			return fmt.Errorf("argument %q: %w", name, err)
		}
	}
	for name := range call.Args {
		if _, known := schema.Params[name]; !known {
			// An unknown argument is refused rather than ignored: silently
			// dropping it turns "set the path to X" into a call without a
			// path.
			return fmt.Errorf("unknown argument %q", name)
		}
	}
	return nil
}

// RequiresApproval reports whether a call needs approval, and the tool is
// unknown, it returns false so the executor's own unknown-tool error wins.
func (r *Registry) RequiresApproval(call Call) bool {
	r.mu.RLock()
	defer r.mu.RUnlock()
	schema, ok := r.schemas[call.Name]
	if !ok {
		return false
	}
	return schema.Risk.RequiresApproval()
}

// Fingerprint is a stable key identifying an identical call, so a repeated
// identical invocation is detected rather than allowed to loop forever.
func Fingerprint(call Call) string {
	var b strings.Builder
	b.WriteString(call.Name)
	b.WriteString("|")
	for _, k := range sortedKeys(call.Args) {
		b.WriteString(k)
		b.WriteString("=")
		b.WriteString(fmt.Sprintf("%v", call.Args[k]))
		b.WriteString(";")
	}
	return b.String()
}

func sortedKeys(m map[string]interface{}) []string {
	out := make([]string, 0, len(m))
	for k := range m {
		out = append(out, k)
	}
	for i := 1; i < len(out); i++ {
		for j := i; j > 0 && out[j] < out[j-1]; j-- {
			out[j], out[j-1] = out[j-1], out[j]
		}
	}
	return out
}

// Budget caps identical calls.
type Budget struct {
	// MaxIdenticalCalls refuses after this many identical calls.
	MaxIdenticalCalls int
	// MaxCalls caps the total across every tool.
	MaxCalls int
	// MaxOutputBytes caps a single tool's serialized output. A tool that can
	// read a whole file must not be able to flood the caller's context, or a
	// read tool becomes a denial-of-service on the next request.
	MaxOutputBytes int
}

// DefaultBudget returns a workable cap.
func DefaultBudget() Budget {
	return Budget{MaxIdenticalCalls: 3, MaxCalls: 50, MaxOutputBytes: 65536}
}

// Result is one execution's outcome.
type Result struct {
	Name   string                 `json:"name"`
	Output map[string]interface{} `json:"output,omitempty"`
	Error  string                 `json:"error,omitempty"`
	// Skipped marks a call refused by a budget or approval rule.
	Skipped bool `json:"skipped,omitempty"`
	// Reason classifies a skip: "budget" or "approval". A caller can tell
	// a cap hit from a refusal without string-matching Error.
	Reason   string `json:"reason,omitempty"`
	Duration int64  `json:"duration_ms"`
}

// Approver decides whether a call that requires approval may proceed.
//
// An interface so the policy is replaceable: the default denies everything, a
// deployment plugs in a real approver, and a test grants specific calls. What a
// Tool must never be able to do is approve itself, which is why the approver is
// owned by the Executor and not passed into Execute.
type Approver interface {
	// Approve returns nil when the call may proceed.
	Approve(call Call, schema Schema) error
}

// ManualApprover grants exactly what it has been told to, keyed by call
// fingerprint.
//
// It models a human decision: a request is refused unless the caller has
// explicitly approved that exact call. Approving "send to alice" does not
// approve sending elsewhere, which is the property that makes an approval worth
// anything.
type ManualApprover struct {
	mu      sync.Mutex
	granted map[string]bool
}

// NewManualApprover returns an approver that grants nothing yet.
func NewManualApprover() *ManualApprover {
	return &ManualApprover{granted: map[string]bool{}}
}

// Grant approves an exact call.
func (m *ManualApprover) Grant(call Call) {
	m.mu.Lock()
	defer m.mu.Unlock()
	m.granted[Fingerprint(call)] = true
}

// Revoke withdraws a grant.
func (m *ManualApprover) Revoke(call Call) {
	m.mu.Lock()
	defer m.mu.Unlock()
	delete(m.granted, Fingerprint(call))
}

// Approve implements Approver.
func (m *ManualApprover) Approve(call Call, schema Schema) error {
	m.mu.Lock()
	defer m.mu.Unlock()
	if !m.granted[Fingerprint(call)] {
		return fmt.Errorf("%w: %q", ErrApprovalRequired, call.Name)
	}
	return nil
}

// Executor runs validated calls under a budget.
type Executor struct {
	registry  *Registry
	budget    Budget
	Approver  Approver
	mu        sync.Mutex
	total     int
	identical map[string]int
}

// NewExecutor returns an executor bound to a registry.
//
// The approver defaults to ManualApprover granting nothing: the fail-closed
// default. An executor that runs irreversible tools when nobody has configured
// an approver is how a purchase happens without a purchase.
func NewExecutor(r *Registry, b Budget) *Executor {
	if b.MaxCalls <= 0 {
		b = DefaultBudget()
	}
	if b.MaxIdenticalCalls <= 0 {
		b.MaxIdenticalCalls = DefaultBudget().MaxIdenticalCalls
	}
	if b.MaxOutputBytes <= 0 {
		b.MaxOutputBytes = DefaultBudget().MaxOutputBytes
	}
	return &Executor{
		registry:  r,
		budget:    b,
		Approver:  NewManualApprover(),
		identical: map[string]int{},
	}
}

// SetApprover replaces the approver, so a deployment installs a real one.
func (e *Executor) SetApprover(a Approver) {
	e.mu.Lock()
	defer e.mu.Unlock()
	e.Approver = a
}

// BudgetConfig returns the executor's budget configuration.
func (e *Executor) BudgetConfig() Budget {
	return e.budget
}

// GrantApproval approves an exact call on the current approver, when it is a
// ManualApprover. It is a convenience for tests and for an in-process human
// confirmation; a deployment should install its own approver.
func (e *Executor) GrantApproval(call Call) {
	e.mu.Lock()
	a := e.Approver
	e.mu.Unlock()
	if manual, ok := a.(*ManualApprover); ok {
		manual.Grant(call)
	}
}

// Run validates, checks the budget, then executes.
func (e *Executor) Run(call Call) *Result {
	// Validation first: an unknown or malformed call must not be charged
	// against the budget, because a model that repeats a bad call would
	// otherwise exhaust the whole run on validation errors.
	if err := e.registry.Validate(call); err != nil {
		return &Result{Name: call.Name, Error: err.Error()}
	}

	e.mu.Lock()
	e.total++
	if e.budget.MaxCalls > 0 && e.total > e.budget.MaxCalls {
		e.mu.Unlock()
		return &Result{
			Name:    call.Name,
			Skipped: true,
			Reason:  "budget",
			Error:   fmt.Sprintf("calling budget of %d exceeded", e.budget.MaxCalls),
		}
	}
	fp := Fingerprint(call)
	e.identical[fp]++
	if e.budget.MaxIdenticalCalls > 0 && e.identical[fp] > e.budget.MaxIdenticalCalls {
		e.mu.Unlock()
		return &Result{
			Name:    call.Name,
			Skipped: true,
			Reason:  "budget",
			Error:   fmt.Sprintf("identical call %q repeated beyond %d", fp, e.budget.MaxIdenticalCalls),
		}
	}
	schema, _ := e.registry.Schema(call.Name)
	tool, ok := e.registry.tool(call.Name)
	e.mu.Unlock()

	if !ok {
		// Defensive: Validate already refused an unknown tool.
		return &Result{Name: call.Name, Error: fmt.Sprintf("%v: %q", ErrToolUnknown, call.Name)}
	}

	// Approval is checked before the tool runs, not after. A refusal must be a
	// refusal, and a tool that may send, spend or delete has no way to approve
	// itself: the approver is owned by the Executor.
	//
	// The gate is the schema's, not the risk's alone: declaring a benign Risk
	// next to a gated Action does not bypass it, so the check asks the schema
	// rather than the caller.
	if schema.RequiresGate() {
		e.mu.Lock()
		approver := e.Approver
		e.mu.Unlock()
		if approver == nil {
			approver = NewManualApprover()
		}
		if err := approver.Approve(call, schema); err != nil {
			return &Result{Name: call.Name, Skipped: true, Reason: "approval", Error: err.Error()}
		}
	}

	done := make(chan *Result, 1)
	start := time.Now()
	go func() {
		out, err := tool.Execute(call.Args)
		res := &Result{Name: call.Name, Duration: time.Since(start).Milliseconds()}
		if err != nil {
			res.Error = err.Error()
		} else {
			res.Output = capOutput(out, e.budget.MaxOutputBytes)
		}
		done <- res
	}()

	select {
	case res := <-done:
		return res
	case <-time.After(schema.Timeout):
		// A timeout is returned as a result, not a panic: a slow tool must not
		// hang the caller or take the process with it. The goroutine is left
		// to finish into a buffered channel and is collected.
		return &Result{
			Name:     call.Name,
			Error:    fmt.Sprintf("timeout after %s", schema.Timeout),
			Duration: time.Since(start).Milliseconds(),
		}
	}
}

// capOutput shrinks a tool's output so a single call cannot flood the caller's
// context. Strings and byte slices are truncated; a map is capped field by
// field, so the fields a caller actually reads still survive. The marker says
// how much was dropped, because silently truncated output is indistinguishable
// from a short answer.
//
// The marker is charged against the cap: truncating to the cap and then
// appending the marker produced output larger than the cap, which is a cap that
// caps nothing.
func capOutput(out map[string]interface{}, maxBytes int) map[string]interface{} {
	const markerTemplate = "\n[truncated %d chars]"
	if maxBytes <= 0 || out == nil {
		return out
	}
	for k, v := range out {
		switch typed := v.(type) {
		case string:
			if truncated, changed := truncateWithMarker(typed, maxBytes, markerTemplate); changed {
				out[k] = truncated
			}
		case []byte:
			if truncated, changed := truncateWithMarker(string(typed), maxBytes, "\n[truncated %d bytes]"); changed {
				out[k] = truncated
			}
		}
	}
	return out
}

// truncateWithMarker shortens text to at most maxBytes including its marker.
func truncateWithMarker(text string, maxBytes int, template string) (string, bool) {
	if len(text) <= maxBytes {
		return text, false
	}
	// Reserve room for the marker by formatting it against the current length
	// first: the digit count is known at that point, so the final size is exact.
	// Without this the result is longer than the cap it is meant to enforce.
	dropped := len(text)
	probe := fmt.Sprintf(template, dropped)
	room := maxBytes - len(probe)
	if room < 0 {
		room = 0
	}
	return text[:room] + fmt.Sprintf(template, len(text)-room), true
}

// Calls returns the number of executions this executor has attempted.
func (e *Executor) Calls() int {
	e.mu.Lock()
	defer e.mu.Unlock()
	return e.total
}

// Counts returns the per-call fingerprint counts, for diagnostics.
func (e *Executor) Counts() map[string]int {
	e.mu.Lock()
	defer e.mu.Unlock()
	out := make(map[string]int, len(e.identical))
	for k, v := range e.identical {
		out[k] = v
	}
	return out
}

// tool looks up an implementation.
func (r *Registry) tool(name string) (Tool, bool) {
	r.mu.RLock()
	defer r.mu.RUnlock()
	t, ok := r.tools[name]
	return t, ok
}

type GraphViewer struct{}

// NewGraphViewer creates a new viewer.
func NewGraphViewer() *GraphViewer {
	return &GraphViewer{}
}

// RenderDOT renders a graph description to DOT.
func (v *GraphViewer) RenderDOT(nodes []string, edges [][2]string) string {
	var buf bytes.Buffer
	buf.WriteString("digraph astrovox {\n")
	buf.WriteString("  rankdir=TB;\n")
	for _, n := range nodes {
		buf.WriteString(fmt.Sprintf("  n%s [label=\"%s\"];\n", n, n))
	}
	for _, e := range edges {
		buf.WriteString(fmt.Sprintf("  n%s -> n%s;\n", e[0], e[1]))
	}
	buf.WriteString("}\n")
	return buf.String()
}

// TensorInspector inspects tensor properties.
type TensorInspector struct{}

// NewTensorInspector creates a new inspector.
func NewTensorInspector() *TensorInspector {
	return &TensorInspector{}
}

// Stats returns basic tensor statistics.
func (i *TensorInspector) Stats(data []float64) map[string]float64 {
	if len(data) == 0 {
		return map[string]float64{}
	}
	sum := 0.0
	min := data[0]
	max := data[0]
	for _, v := range data {
		sum += v
		if v < min {
			min = v
		}
		if v > max {
			max = v
		}
	}
	return map[string]float64{
		"count": float64(len(data)),
		"sum":   sum,
		"min":   min,
		"max":   max,
		"mean":  sum / float64(len(data)),
	}
}

// MemoryProfiler tracks allocation patterns.
type MemoryProfiler struct {
	allocations []int
}

// NewMemoryProfiler creates a new profiler.
func NewMemoryProfiler() *MemoryProfiler {
	return &MemoryProfiler{}
}

// RecordAllocation records a memory allocation.
func (p *MemoryProfiler) RecordAllocation(bytes int) {
	p.allocations = append(p.allocations, bytes)
}

// Peak returns the peak allocation observed.
func (p *MemoryProfiler) Peak() int {
	peak := 0
	current := 0
	for _, b := range p.allocations {
		current += b
		if current > peak {
			peak = current
		}
	}
	return peak
}

// BenchmarkDashboard summarizes benchmark results.
type BenchmarkDashboard struct {
	Results map[string]float64
}

// NewBenchmarkDashboard creates a new dashboard.
func NewBenchmarkDashboard() *BenchmarkDashboard {
	return &BenchmarkDashboard{Results: make(map[string]float64)}
}

// AddResult adds a benchmark result.
func (d *BenchmarkDashboard) AddResult(name string, nsPerOp float64) {
	d.Results[name] = nsPerOp
}

// Summary returns a summary string.
func (d *BenchmarkDashboard) Summary() string {
	var buf bytes.Buffer
	for name, ns := range d.Results {
		buf.WriteString(fmt.Sprintf("%s: %.2f ns/op\n", name, ns))
	}
	return buf.String()
}

// Debugger supports step execution tracing.
type Debugger struct {
	Breakpoints map[int]bool
	Steps       int
}

// NewDebugger creates a new debugger.
func NewDebugger() *Debugger {
	return &Debugger{Breakpoints: make(map[int]bool)}
}

// SetBreakpoint sets a breakpoint.
func (d *Debugger) SetBreakpoint(id int) {
	d.Breakpoints[id] = true
}

// Step advances one step.
func (d *Debugger) Step() {
	d.Steps++
}

// Tracer records execution spans.
type Tracer struct {
	Spans []Span
}

// Span represents a traced span.
type Span struct {
	Name  string
	Start int64
	End   int64
}

// NewTracer creates a new tracer.
func NewTracer() *Tracer {
	return &Tracer{}
}

// Start begins a span.
func (t *Tracer) Start(name string) *Span {
	span := &Span{Name: name, Start: 1}
	t.Spans = append(t.Spans, *span)
	return span
}

// Complete completes a span.
func (s *Span) Complete(end int64) {
	s.End = end
}

// Spans returns all recorded spans.
func (t *Tracer) SpansList() []Span {
	return append([]Span(nil), t.Spans...)
}
