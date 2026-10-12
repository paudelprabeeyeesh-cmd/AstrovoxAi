// Package agent implements the agent loop: propose, validate, approve,
// execute, observe, repeat, under hard caps.
//
// The loop is the part of a tool-using system that goes wrong in public. A
// model that repeats a call, or calls a tool it was never offered, or
// escalates from reading to sending, is a real incident rather than a test
// failure. So the four caps are structural here rather than advisory:
//
//  1. MaxSteps bounds iterations. The loop stops with an explanation when
//     the cap is reached, rather than promising to continue.
//  2. MaxTokens bounds the prompt budget, checked before each step.
//  3. MaxWallTime bounds elapsed time, checked between steps.
//  4. Only registered tools are callable, and a tool needing approval does
//     not run without an explicit grant.
//
// The proposer is an interface, so the same loop runs against a real model,
// a recorded replay, and a test double with no special cases.
package agent

import (
	"context"
	"errors"
	"fmt"
	"sync"
	"time"

	"github.com/astrovox/astrovox/internal/tools"
)

// ErrStepCap is returned when the loop reaches its step limit.
var ErrStepCap = errors.New("agent: step cap reached")

// ErrTokenCap is returned when the loop reaches its token budget.
var ErrTokenCap = errors.New("agent: token budget exhausted")

// ErrTimeCap is returned when the loop reaches its wall-time limit.
var ErrTimeCap = errors.New("agent: wall-time cap reached")

// ErrApprovalRequired is returned when a proposal needs approval that was
// not granted.
var ErrApprovalRequired = errors.New("agent: approval required for this action")

// ErrToolUnknown is returned when a proposal names an unregistered tool.
var ErrToolUnknown = errors.New("agent: unregistered tool")

// Proposer decides the next action from the current trace. It is an
// interface so the loop is testable without a model, and so a recorded
// trajectory can be replayed with the same code path.
type Proposer interface {
	// Propose returns the tool call the model wants next, or nil when it
	// considers the task complete.
	Propose(ctx context.Context, step int, trace []tools.Result) (*tools.Call, error)
}

// Approver grants permission for a single call. It is consulted only for a
// call the registry marks as needing approval.
type Approver interface {
	// Approve returns nil to allow the call.
	Approve(call tools.Call, rationale string) error
}

// AutoApprover approves everything. It exists so a deployment can start
// without an approval UI, and it is explicit about what it disables: it
// lets external and irreversible actions through unattended, which is not
// the default the loop wants.
type AutoApprover struct{}

// Approve allows any call.
func (AutoApprover) Approve(_ tools.Call, _ string) error { return nil }

// DenyApprover refuses everything. It is the safe default when no approver
// is configured.
type DenyApprover struct{}

// Approve refuses any call.
func (DenyApprover) Approve(_ tools.Call, _ string) error { return ErrApprovalRequired }

// Limits is the hard cap set.
type Limits struct {
	MaxSteps    int
	MaxTokens   int
	MaxWallTime time.Duration
	// Budget caps identical and total tool calls.
	Budget tools.Budget
}

// DefaultLimits returns a conservative cap set.
func DefaultLimits() Limits {
	return Limits{
		MaxSteps:    8,
		MaxTokens:   8000,
		MaxWallTime: 120 * time.Second,
		Budget:      tools.DefaultBudget(),
	}
}

// Config configures an agent.
type Config struct {
	// Name identifies the agent in logs and the trace.
	Name string
	// Goal is the task, passed to the proposer so it can be included in the
	// prompt.
	Goal   string
	Limits Limits
	// Approver may be nil, which means DenyApprover.
	Approver Approver
}

// Agent runs one task to completion or to a cap.
type Agent struct {
	cfg   Config
	reg   *tools.Registry
	exec  *tools.Executor
	clock func() time.Time

	mu    sync.Mutex
	steps int
	spent int
}

// New returns an agent bound to a registry and its executor.
func New(cfg Config, reg *tools.Registry, exec *tools.Executor) (*Agent, error) {
	if reg == nil {
		return nil, errors.New("agent: a registry is required")
	}
	if exec == nil {
		return nil, errors.New("agent: an executor is required")
	}
	if cfg.Limits.MaxSteps <= 0 {
		cfg.Limits.MaxSteps = DefaultLimits().MaxSteps
	}
	if cfg.Limits.MaxTokens <= 0 {
		cfg.Limits.MaxTokens = DefaultLimits().MaxTokens
	}
	if cfg.Limits.MaxWallTime <= 0 {
		cfg.Limits.MaxWallTime = DefaultLimits().MaxWallTime
	}
	if cfg.Approver == nil {
		// The safe default: no approver means nothing needing approval runs.
		cfg.Approver = DenyApprover{}
	}
	return &Agent{cfg: cfg, reg: reg, exec: exec, clock: time.Now}, nil
}

// Result is the outcome of a run.
type Result struct {
	// Answer is the final message when the agent finished, empty when it
	// stopped at a cap.
	Answer string
	// Trace is every executed call, in order.
	Trace []tools.Result
	// StepsExecuted counts iterations.
	StepsExecuted int
	// StopReason explains why the run ended.
	StopReason string
	// TokensUsed is the prompt tokens consumed, tracked by ChargeTokens.
	TokensUsed int
}

// Run drives the loop.
func (a *Agent) Run(ctx context.Context, p Proposer) (*Result, error) {
	// The clock is read once here, before any step, so a caller that swaps
	// the clock mid-run does not produce a negative elapsed time.
	start := a.clock()
	res := &Result{}

	// A context already cancelled is refused rather than started.
	if err := ctx.Err(); err != nil {
		return nil, err
	}

	for step := 0; step < a.cfg.Limits.MaxSteps; step++ {
		// Caps are checked before the next inference, not only after it, so a
		// step is not paid for once the budget is already spent.
		if tokens := a.TokenUsage(); tokens > a.cfg.Limits.MaxTokens {
			res.StepsExecuted = step
			res.StopReason = "token cap"
			return res, fmt.Errorf("%w: %d > %d", ErrTokenCap, tokens, a.cfg.Limits.MaxTokens)
		}
		if elapsed := a.clock().Sub(start); elapsed > a.cfg.Limits.MaxWallTime {
			res.StepsExecuted = step
			res.StopReason = "wall-time cap"
			return res, fmt.Errorf("%w: %s > %s", ErrTimeCap, elapsed.Round(time.Millisecond), a.cfg.Limits.MaxWallTime)
		}

		res.StepsExecuted = step + 1

		call, err := p.Propose(ctx, step, res.Trace)
		if err != nil {
			res.StopReason = "proposer error"
			return res, fmt.Errorf("agent %q: propose failed at step %d: %w", a.cfg.Name, step, err)
		}
		if call == nil {
			res.StopReason = "completed"
			return res, nil
		}

		// Only registered tools are callable. The executor also validates,
		// but refusing here means an unregistered name is never charged
		// against the budget.
		if _, known := a.reg.Schema(call.Name); !known {
			res.Trace = append(res.Trace, tools.Result{
				Name:  call.Name,
				Error: fmt.Sprintf("%v: %q", ErrToolUnknown, call.Name),
			})
			res.StopReason = "unregistered tool"
			return res, fmt.Errorf("%w: %q", ErrToolUnknown, call.Name)
		}

		// Approval is consulted before execution and only for tools that need
		// it, so a read never waits on a human.
		if a.reg.RequiresApproval(*call) {
			if err := a.cfg.Approver.Approve(*call, a.cfg.Goal); err != nil {
				res.Trace = append(res.Trace, tools.Result{
					Name:    call.Name,
					Error:   err.Error(),
					Skipped: true,
				})
				res.StopReason = "approval refused"
				return res, fmt.Errorf("agent %q: %w", a.cfg.Name, err)
			}
		}

		outcome := a.exec.Run(*call)
		res.Trace = append(res.Trace, *outcome)
		if outcome.Skipped {
			// A skipped call is a cap hit, which is recorded and returned
			// rather than retried.
			res.StopReason = "budget cap"
			return res, nil
		}
		if outcome.Error != "" {
			// A tool failure is recorded and the loop stops rather than
			// retrying blindly: a repeated attempt after the same failure is
			// the loop that never ends.
			res.StopReason = "tool error"
			return res, nil
		}
	}

	res.StopReason = "step cap"
	return res, fmt.Errorf("%w after %d steps", ErrStepCap, a.cfg.Limits.MaxSteps)
}

// ChargeTokens records prompt tokens consumed by a step, so the token cap
// has something to measure. The proposer calls it after each inference.
func (a *Agent) ChargeTokens(n int) int {
	a.mu.Lock()
	defer a.mu.Unlock()
	a.spent += n
	return a.spent
}

// usage returns the step count and the tokens charged.
func (a *Agent) usage() (int, int) {
	a.mu.Lock()
	defer a.mu.Unlock()
	return a.steps, a.spent
}

// Steps returns the steps executed so far, for a concurrent observer.
func (a *Agent) Steps() int {
	a.mu.Lock()
	defer a.mu.Unlock()
	return a.steps
}

// TokenUsage returns the tokens charged so far.
func (a *Agent) TokenUsage() int {
	a.mu.Lock()
	defer a.mu.Unlock()
	return a.spent
}
