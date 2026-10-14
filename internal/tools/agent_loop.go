package tools

import (
	"context"
	"fmt"
	"sync"
	"time"
)

// A bounded agent loop.
//
// The loop is bounded because an unbounded one is a billing incident. A model
// that repeats a tool, or never reaches an answer, would otherwise consume the
// whole provider budget, so every dimension is capped before the first call:
// steps, tokens, tool calls, duration, and cost. A cap that is checked after the
// fact has already spent the money.
//
// The model is injected as a Thinker rather than called directly. That is what
// makes the loop testable without a provider key, and it is also what makes the
// caps testable: a scripted thinker can return the same call forever, which is
// exactly the behaviour a real model produces when it is stuck.
//
// The loop refuses a tool the registry does not know rather than passing the
// name through to the executor. A name the loop did not fetch from the registry
// is a name the model invented, and inventing a tool name is the first half of
// tool injection.

// StepAction is what a model asked for on one step.
type StepAction struct {
	// Call is non-nil when the model asked to invoke a tool.
	Call *Call
	// Reply is non-empty when the model has finished and is answering.
	Reply string
}

// IsCall reports whether this step invokes a tool.
func (a StepAction) IsCall() bool { return a.Call != nil }

// ThinkFn is one model decision, given the history so far.
type ThinkFn func(ctx context.Context, h History) (StepAction, error)

// Turn records one iteration.
type Turn struct {
	// Action the model asked for.
	Action StepAction `json:"action"`
	// Results of any tool executions during this turn.
	Results []Result `json:"results,omitempty"`
	// Error is set when the step itself failed, e.g. the model errored.
	Error string `json:"error,omitempty"`
	// StartedAt and DurationElapsed bound the turn for a cost attribution.
	StartedAt       time.Time `json:"started_at"`
	DurationElapsed int64     `json:"duration_ms"`
}

// History is everything the loop has done so far. Passed to the Thinker so it
// can reason over prior results rather than being asked to remember them.
type History []Turn

// Outcome is a run's final state, including why it stopped.
type Outcome struct {
	// Answer is the model's reply, empty unless StopReason is "answer".
	Answer string `json:"answer,omitempty"`
	// StopReason is which limit fired, or "answer" if the model finished.
	StopReason string `json:"stop_reason"`
	// Explanation is human-readable, so a caller can see what happened without
	// reading the code. A run that stops with no explanation cannot be
	// diagnosed by anyone but its author.
	Explanation string `json:"explanation,omitempty"`

	Steps           int     `json:"steps"`
	ToolCalls       int     `json:"tool_calls"`
	Tokens          int     `json:"tokens"`
	Cost            float64 `json:"cost"`
	DurationElapsed int64   `json:"duration_ms"`

	Turns []Turn `json:"turns,omitempty"`
}

// Limits bounds a loop on every axis that costs money.
type Limits struct {
	// MaxSteps caps model decisions.
	MaxSteps int
	// MaxToolCalls caps tool executions.
	MaxToolCalls int
	// MaxIdenticalCalls caps repeats of one call fingerprint.
	MaxIdenticalCalls int
	// MaxDuration bounds the whole run.
	MaxDuration time.Duration
	// MaxCost bounds the modelled spend. A model's cost is modelled, not
	// measured by a provider, so it is the loop's own accounting rather than a
	// real bill - which is the honest way to bound a loop whose provider bill
	// is not yet known.
	MaxCost float64
	// CostPerStep is what one model decision is modelled to cost. Charged even
	// when the model fails, because a provider bills a failed request too.
	CostPerStep float64
	// Tokens cost as they are consumed.
	MaxTokens int
}

// DefaultLimits bounds a loop conservatively. A default must be bounded or the
// first misconfigured deployment runs without a ceiling.
func DefaultLimits() Limits {
	return Limits{
		MaxSteps:          12,
		MaxToolCalls:      40,
		MaxIdenticalCalls: 3,
		MaxDuration:       2 * time.Minute,
		MaxCost:           0.50,
		CostPerStep:       0.05,
		MaxTokens:         100_000,
	}
}

// Stop reasons. Exported so a caller can branch on them rather than matching
// strings that may change.
const (
	StopAnswer      = "answer"
	StopMaxSteps    = "max_steps"
	StopMaxToolCall = "max_tool_calls"
	StopRepeated    = "repeated_call"
	StopDuration    = "max_duration"
	StopCost        = "max_cost"
	StopTokens      = "max_tokens"
	StopCancelled   = "cancelled"
	StopThinkerErr  = "thinker_error"
)

// Loop is one bounded run.
type Loop struct {
	registry *Registry
	executor *Executor
	think    ThinkFn
	limits   Limits

	mu     sync.Mutex
	seen   map[string]int
	closed bool
}

// NewLoop builds a loop over a registry and executor.
func NewLoop(r *Registry, e *Executor, think ThinkFn, limits Limits) *Loop {
	if limits.MaxSteps <= 0 {
		limits.MaxSteps = DefaultLimits().MaxSteps
	}
	if limits.MaxToolCalls <= 0 {
		limits.MaxToolCalls = DefaultLimits().MaxToolCalls
	}
	if limits.MaxIdenticalCalls <= 0 {
		limits.MaxIdenticalCalls = DefaultLimits().MaxIdenticalCalls
	}
	// MaxDuration is deliberately NOT normalised. A zero or negative budget
	// means "already expired", which is the fail-closed reading; replacing it
	// with a default would let a caller who means "no time left" run anyway.
	// Callers wanting a ceiling take it from DefaultLimits.
	if limits.CostPerStep <= 0 {
		limits.CostPerStep = DefaultLimits().CostPerStep
	}
	return &Loop{
		registry: r,
		executor: e,
		think:    think,
		limits:   limits,
		seen:     map[string]int{},
	}
}

// Limits returns the loop's effective limits.
func (l *Loop) Limits() Limits { return l.limits }

// Run drives the loop until it stops. It always returns an Outcome; a panic
// inside a tool is not the loop's to propagate.
func (l *Loop) Run(ctx context.Context, task string) (outcome Outcome) {
	start := time.Now()
	l.mu.Lock()
	l.seen = map[string]int{}
	l.mu.Unlock()

	deadline := start.Add(l.limits.MaxDuration)
	var history History
	var cost float64
	var tokens int
	toolCalls := 0

	// spend charges a decision even when the model fails, because a provider
	// bills a failed request too. Checking the ceiling before the call rather
	// than after is the point of a budget.
	spend := func() (Outcome, bool) {
		cost += l.limits.CostPerStep
		if l.limits.MaxCost > 0 && cost > l.limits.MaxCost {
			return Outcome{
				StopReason:      StopCost,
				Explanation:     fmt.Sprintf("cost ceiling of %.2f exceeded (%.4f spent)", l.limits.MaxCost, cost),
				Steps:           len(history),
				ToolCalls:       toolCalls,
				Tokens:          tokens,
				Cost:            cost,
				DurationElapsed: time.Since(start).Milliseconds(),
			}, true
		}
		return Outcome{}, false
	}

	for step := 0; step < l.limits.MaxSteps; step++ {
		if err := ctx.Err(); err != nil {
			return Outcome{
				StopReason:      StopCancelled,
				Explanation:     fmt.Sprintf("cancelled after %d steps: %v", step, err),
				Steps:           step,
				ToolCalls:       toolCalls,
				Tokens:          tokens,
				Cost:            cost,
				DurationElapsed: time.Since(start).Milliseconds(),
			}
		}
		if now := time.Now(); now.After(deadline) {
			return Outcome{
				StopReason:      StopDuration,
				Explanation:     fmt.Sprintf("duration ceiling of %s exceeded after %d steps", l.limits.MaxDuration, step),
				Steps:           step,
				ToolCalls:       toolCalls,
				Tokens:          tokens,
				Cost:            cost,
				DurationElapsed: time.Since(start).Milliseconds(),
			}
		}

		turnStart := time.Now()
		action, err := l.think(ctx, history)
		if exceeded, stop := spend(); stop {
			exceeded.Turns = history
			return exceeded
		}
		if err != nil {
			return Outcome{
				StopReason:      StopThinkerErr,
				Explanation:     fmt.Sprintf("model call failed after %d steps: %v", step, err),
				Steps:           step,
				ToolCalls:       toolCalls,
				Tokens:          tokens,
				Cost:            cost,
				DurationElapsed: time.Since(start).Milliseconds(),
				Turns:           history,
			}
		}

		// The model is answering: record the turn, then stop cleanly.
		if !action.IsCall() {
			turn := Turn{Action: action, StartedAt: turnStart}
			turn.DurationElapsed = time.Since(turnStart).Milliseconds()
			return Outcome{
				Answer:          action.Reply,
				StopReason:      StopAnswer,
				Explanation:     fmt.Sprintf("answered after %d steps, %d tool calls", step+1, toolCalls),
				Steps:           step + 1,
				ToolCalls:       toolCalls,
				Tokens:          tokens,
				Cost:            cost,
				DurationElapsed: time.Since(start).Milliseconds(),
				// The history ships with the answer, including the final reply
				// turn. A caller needs to see which tools ran to trust the
				// answer, and an outcome without it cannot be reviewed by
				// anyone but its author.
				Turns: append(history, turn),
			}
		}

		call := *action.Call
		turn := Turn{Action: action, StartedAt: turnStart}

		// A tool the registry does not know is refused at the gate rather than
		// forwarded to the executor, so an invented name cannot reach an
		// implementation.
		if err := l.registry.Validate(call); err != nil {
			turn.Error = fmt.Sprintf("refused by the registry: %v", err)
			history = append(history, turn)
			continue
		}

		// A repeated identical call is a loop, not progress.
		fp := Fingerprint(call)
		l.mu.Lock()
		l.seen[fp]++
		count := l.seen[fp]
		l.mu.Unlock()
		if l.limits.MaxIdenticalCalls > 0 && count > l.limits.MaxIdenticalCalls {
			turn.Error = fmt.Sprintf("identical call refused after %d repeats", count)
			history = append(history, turn)
			return Outcome{
				StopReason:      StopRepeated,
				Explanation:     fmt.Sprintf("call %q repeated %d times, which is a loop rather than progress", call.Name, count),
				Steps:           step + 1,
				ToolCalls:       toolCalls,
				Tokens:          tokens,
				Cost:            cost,
				DurationElapsed: time.Since(start).Milliseconds(),
				Turns:           history,
			}
		}

		if toolCalls >= l.limits.MaxToolCalls {
			return Outcome{
				StopReason:      StopMaxToolCall,
				Explanation:     fmt.Sprintf("tool-call ceiling of %d reached after %d steps", l.limits.MaxToolCalls, step),
				Steps:           step + 1,
				ToolCalls:       toolCalls,
				Tokens:          tokens,
				Cost:            cost,
				DurationElapsed: time.Since(start).Milliseconds(),
				Turns:           history,
			}
		}

		result := l.executor.Run(call)
		toolCalls++
		turn.Results = append(turn.Results, *result)
		turn.DurationElapsed = time.Since(turnStart).Milliseconds()
		history = append(history, turn)

		// A skipped call is a refusal, not progress, and it is not a stop: the
		// model asked for something it may not have, and a loop that abandoned
		// on every refusal could not work around a gated tool at all. The
		// refusal is recorded so the model can see it and try something else,
		// and the step ceiling still bounds the run.
		if result.Skipped {
			continue
		}
	}

	// The step budget ran out. An unanswered run is refused rather than answered
	// with whatever the last partial text was.
	return Outcome{
		StopReason:      StopMaxSteps,
		Explanation:     fmt.Sprintf("step ceiling of %d reached without an answer", l.limits.MaxSteps),
		Steps:           len(history),
		ToolCalls:       toolCalls,
		Tokens:          tokens,
		Cost:            cost,
		DurationElapsed: time.Since(start).Milliseconds(),
		Turns:           history,
	}
}
