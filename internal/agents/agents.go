// Package agents provides an AI agent system with orchestration, tools,
// and memory.
package agents

import (
	"context"
	"errors"
	"fmt"
	"sort"
	"strings"
	"sync"
	"sync/atomic"
	"time"
)

// Tool is a callable tool for an agent.
type Tool interface {
	Name() string
	Description() string
	Schema() string
	Execute(ctx context.Context, args map[string]interface{}) (interface{}, error)
}

// ToolFunc adapts a function to the Tool interface.
type ToolFunc struct {
	name   string
	desc   string
	schema string
	fn     func(ctx context.Context, args map[string]interface{}) (interface{}, error)
}

// NewToolFunc creates a tool from a function.
func NewToolFunc(name, desc, schema string, fn func(ctx context.Context, args map[string]interface{}) (interface{}, error)) *ToolFunc {
	return &ToolFunc{name: name, desc: desc, schema: schema, fn: fn}
}

// Name returns the tool name.
func (t *ToolFunc) Name() string { return t.name }

// Description returns the tool description.
func (t *ToolFunc) Description() string { return t.desc }

// Schema returns the argument schema.
func (t *ToolFunc) Schema() string { return t.schema }

// Execute runs the tool.
func (t *ToolFunc) Execute(ctx context.Context, args map[string]interface{}) (interface{}, error) {
	return t.fn(ctx, args)
}

// ToolRegistry holds available tools.
type ToolRegistry struct {
	mu    sync.RWMutex
	tools map[string]Tool
}

// NewToolRegistry creates a registry.
func NewToolRegistry() *ToolRegistry {
	return &ToolRegistry{tools: make(map[string]Tool)}
}

// Register adds a tool to the registry.
func (r *ToolRegistry) Register(t Tool) error {
	if t == nil || t.Name() == "" {
		return errors.New("invalid tool")
	}
	r.mu.Lock()
	defer r.mu.Unlock()
	r.tools[t.Name()] = t
	return nil
}

// Get returns a tool by name.
func (r *ToolRegistry) Get(name string) (Tool, bool) {
	r.mu.RLock()
	defer r.mu.RUnlock()
	t, ok := r.tools[name]
	return t, ok
}

// List returns all registered tool names.
func (r *ToolRegistry) List() []string {
	r.mu.RLock()
	defer r.mu.RUnlock()
	names := make([]string, 0, len(r.tools))
	for n := range r.tools {
		names = append(names, n)
	}
	sort.Strings(names)
	return names
}

// MemoryEntry is one item in an agent's memory.
type MemoryEntry struct {
	Content   string
	Kind      string // "observation", "thought", "action", "result", "system"
	Timestamp time.Time
	Score     float64
}

// AgentMemory is a bounded, recency+importance ordered memory.
type AgentMemory struct {
	mu      sync.RWMutex
	entries []MemoryEntry
	maxSize int
}

// NewAgentMemory creates a memory buffer.
func NewAgentMemory(maxSize int) *AgentMemory {
	if maxSize <= 0 {
		maxSize = 100
	}
	return &AgentMemory{maxSize: maxSize}
}

// Add appends an entry, evicting the least important when full.
func (m *AgentMemory) Add(e MemoryEntry) {
	if e.Timestamp.IsZero() {
		e.Timestamp = time.Now()
	}
	m.mu.Lock()
	defer m.mu.Unlock()
	m.entries = append(m.entries, e)
	if len(m.entries) > m.maxSize {
		// evict lowest score (ties: oldest)
		worst := 0
		for i := 1; i < len(m.entries); i++ {
			if m.entries[i].Score < m.entries[worst].Score {
				worst = i
			}
		}
		m.entries = append(m.entries[:worst], m.entries[worst+1:]...)
	}
}

// Recall returns the most relevant entries for a query.
func (m *AgentMemory) Recall(query string, k int) []MemoryEntry {
	m.mu.RLock()
	defer m.mu.RUnlock()
	terms := strings.Fields(strings.ToLower(query))
	scored := make([]MemoryEntry, len(m.entries))
	copy(scored, m.entries)
	for i := range scored {
		hits := 0
		lc := strings.ToLower(scored[i].Content)
		for _, t := range terms {
			if strings.Contains(lc, t) {
				hits++
			}
		}
		if len(terms) > 0 {
			scored[i].Score = scored[i].Score + float64(hits)/float64(len(terms))
		}
	}
	sort.Slice(scored, func(i, j int) bool {
		if scored[i].Score == scored[j].Score {
			return scored[i].Timestamp.After(scored[j].Timestamp)
		}
		return scored[i].Score > scored[j].Score
	})
	if k > 0 && len(scored) > k {
		scored = scored[:k]
	}
	return scored
}

// Size returns the number of entries.
func (m *AgentMemory) Size() int {
	m.mu.RLock()
	defer m.mu.RUnlock()
	return len(m.entries)
}

// Clear empties the memory.
func (m *AgentMemory) Clear() {
	m.mu.Lock()
	m.entries = nil
	m.mu.Unlock()
}

// AgentRole identifies an agent's role.
type AgentRole int

const (
	RolePlanner AgentRole = iota
	RoleExecutor
	RoleCritic
	RoleResearcher
	RoleGeneric
)

func (r AgentRole) String() string {
	switch r {
	case RolePlanner:
		return "planner"
	case RoleExecutor:
		return "executor"
	case RoleCritic:
		return "critic"
	case RoleResearcher:
		return "researcher"
	default:
		return "generic"
	}
}

// LLM is the interface an agent uses to reason.
type LLM interface {
	Complete(ctx context.Context, prompt string) (string, error)
}

// Agent is a single reasoning agent.
type Agent struct {
	Name     string
	Role     AgentRole
	Goal     string
	System   string
	llm      LLM
	tools    *ToolRegistry
	memory   *AgentMemory
	maxSteps int
	stats    AgentStats
}

// AgentStats tracks agent execution statistics.
type AgentStats struct {
	Steps       atomic.Int64
	ToolCalls   atomic.Int64
	Errors      atomic.Int64
	TotalTimeNs atomic.Int64
}

// NewAgent creates an agent.
func NewAgent(name string, role AgentRole, goal, system string, llm LLM, tools *ToolRegistry, maxSteps int) *Agent {
	if tools == nil {
		tools = NewToolRegistry()
	}
	if maxSteps <= 0 {
		maxSteps = 10
	}
	return &Agent{
		Name:     name,
		Role:     role,
		Goal:     goal,
		System:   system,
		llm:      llm,
		tools:    tools,
		memory:   NewAgentMemory(100),
		maxSteps: maxSteps,
	}
}

// AddTool registers a tool for this agent.
func (a *Agent) AddTool(t Tool) { a.tools.Register(t) }

// Memory returns the agent memory.
func (a *Agent) Memory() *AgentMemory { return a.memory }

// Stats returns agent statistics.
func (a *Agent) Stats() *AgentStats { return &a.stats }

// Step executes one reasoning step, returning the action.
func (a *Agent) Step(ctx context.Context, observation string) (string, error) {
	start := time.Now()
	defer func() { a.stats.TotalTimeNs.Add(time.Since(start).Nanoseconds()) }()

	if a.llm == nil {
		return "", fmt.Errorf("agent %s has no LLM", a.Name)
	}

	prompt := a.buildPrompt(observation)
	resp, err := a.llm.Complete(ctx, prompt)
	if err != nil {
		a.stats.Errors.Add(1)
		return "", err
	}

	a.stats.Steps.Add(1)
	a.memory.Add(MemoryEntry{Content: observation, Kind: "observation", Score: 1.0})
	a.memory.Add(MemoryEntry{Content: resp, Kind: "thought", Score: 1.0})
	return resp, nil
}

func (a *Agent) buildPrompt(observation string) string {
	var sb strings.Builder
	if a.System != "" {
		sb.WriteString(a.System)
		sb.WriteString("\n\n")
	}
	sb.WriteString("Role: " + a.Role.String() + "\n")
	if a.Goal != "" {
		sb.WriteString("Goal: " + a.Goal + "\n")
	}
	recent := a.memory.Recall(observation, 5)
	if len(recent) > 0 {
		sb.WriteString("\nRelevant memory:\n")
		for _, e := range recent {
			sb.WriteString("- [" + e.Kind + "] " + e.Content + "\n")
		}
	}
	sb.WriteString("\nObservation: " + observation + "\n")
	sb.WriteString("Next action:")
	return sb.String()
}

// RunTool executes a tool by name.
func (a *Agent) RunTool(ctx context.Context, name string, args map[string]interface{}) (interface{}, error) {
	t, ok := a.tools.Get(name)
	if !ok {
		a.stats.Errors.Add(1)
		return nil, fmt.Errorf("tool %q not found", name)
	}
	a.stats.ToolCalls.Add(1)
	res, err := t.Execute(ctx, args)
	if err != nil {
		a.stats.Errors.Add(1)
		return nil, err
	}
	a.memory.Add(MemoryEntry{
		Content: fmt.Sprintf("%s -> %v", name, res),
		Kind:    "result",
		Score:   0.8,
	})
	return res, nil
}

// Orchestrator coordinates multiple agents to solve a task.
type Orchestrator struct {
	agents    map[string]*Agent
	tools     *ToolRegistry
	workflow  []WorkflowStep
	maxRounds int
	mu        sync.RWMutex
	stats     OrchestratorStats
}

// OrchestratorStats tracks orchestration statistics.
type OrchestratorStats struct {
	Rounds     atomic.Int64
	AgentCalls atomic.Int64
	Failures   atomic.Int64
}

// WorkflowStep defines an ordered pipeline step.
type WorkflowStep struct {
	AgentName string
	Action    string
}

// NewOrchestrator creates an orchestrator.
func NewOrchestrator(maxRounds int) *Orchestrator {
	if maxRounds <= 0 {
		maxRounds = 5
	}
	return &Orchestrator{
		agents:    make(map[string]*Agent),
		tools:     NewToolRegistry(),
		maxRounds: maxRounds,
	}
}

// RegisterAgent adds an agent.
func (o *Orchestrator) RegisterAgent(a *Agent) error {
	if a == nil || a.Name == "" {
		return errors.New("invalid agent")
	}
	o.mu.Lock()
	defer o.mu.Unlock()
	o.agents[a.Name] = nil
	o.agents[a.Name] = a
	return nil
}

// GetAgent returns an agent by name.
func (o *Orchestrator) GetAgent(name string) (*Agent, bool) {
	o.mu.RLock()
	defer o.mu.RUnlock()
	a, ok := o.agents[name]
	return a, ok
}

// Agents returns registered agent names.
func (o *Orchestrator) Agents() []string {
	o.mu.RLock()
	defer o.mu.RUnlock()
	names := make([]string, 0, len(o.agents))
	for n := range o.agents {
		names = append(names, n)
	}
	sort.Strings(names)
	return names
}

// AddTool registers a global tool.
func (o *Orchestrator) AddTool(t Tool) { o.tools.Register(t) }

// SetWorkflow sets the pipeline of steps.
func (o *Orchestrator) SetWorkflow(steps []WorkflowStep) {
	o.mu.Lock()
	defer o.mu.Unlock()
	o.workflow = steps
}

// Run executes the workflow for a task.
func (o *Orchestrator) Run(ctx context.Context, task string) (string, error) {
	o.mu.RLock()
	steps := append([]WorkflowStep(nil), o.workflow...)
	o.mu.RUnlock()

	if len(steps) == 0 {
		return "", errors.New("no workflow defined")
	}

	current := task
	for round := 0; round < o.maxRounds; round++ {
		o.stats.Rounds.Add(1)
		for _, step := range steps {
			o.mu.RLock()
			agent, ok := o.agents[step.AgentName]
			o.mu.RUnlock()
			if !ok {
				o.stats.Failures.Add(1)
				return "", fmt.Errorf("agent %q not registered", step.AgentName)
			}
			o.stats.AgentCalls.Add(1)
			obs := current
			if step.Action != "" {
				obs = step.Action + ": " + current
			}
			out, err := agent.Step(ctx, obs)
			if err != nil {
				o.stats.Failures.Add(1)
				return "", err
			}
			current = out
		}
		// Stop when the critic agent (if any) approves. We treat the
		// presence of a "PLAN APPROVED" marker as approval.
		if strings.Contains(strings.ToUpper(current), "APPROVED") {
			return current, nil
		}
	}
	return current, nil
}

// RunParallel runs the same task on all agents concurrently.
func (o *Orchestrator) RunParallel(ctx context.Context, task string) (map[string]string, error) {
	o.mu.RLock()
	agents := make(map[string]*Agent, len(o.agents))
	for n, a := range o.agents {
		agents[n] = a
	}
	o.mu.RUnlock()

	var mu sync.Mutex
	var wg sync.WaitGroup
	results := make(map[string]string)
	errs := make(map[string]error)

	for name, agent := range agents {
		wg.Add(1)
		go func(n string, a *Agent) {
			defer wg.Done()
			out, err := a.Step(ctx, task)
			mu.Lock()
			defer mu.Unlock()
			if err != nil {
				errs[n] = err
				return
			}
			results[n] = out
			o.stats.AgentCalls.Add(1)
		}(name, agent)
	}
	wg.Wait()

	if len(errs) > 0 {
		for n, err := range errs {
			o.stats.Failures.Add(1)
			return results, fmt.Errorf("agent %s: %w", n, err)
		}
	}
	return results, nil
}
