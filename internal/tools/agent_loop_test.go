package tools

import (
	"context"
	"errors"
	"strings"
	"testing"
	"time"
)

// A scripted "model": it returns the next planned action. This is how the loop
// is tested without a provider key, and it also makes the test deterministic.
type action func(call *Call) (StepAction, error)

type scriptedThinker struct {
	actions []action
	calls   int
}

func (s *scriptedThinker) Think(ctx context.Context, h History) (StepAction, error) {
	if s.calls >= len(s.actions) {
		return StepAction{Reply: "done: ran out of script"}, nil
	}
	a := s.actions[s.calls]
	s.calls++
	return a(nil)
}

// callNow is an action that invokes a tool with the given arguments.
func callNow(name string, args map[string]interface{}) action {
	return func(call *Call) (StepAction, error) {
		c := Call{Name: name, Args: args}
		return StepAction{Call: &c}, nil
	}
}

// replyNow finishes the loop with this answer.
func replyNow(text string) action {
	return func(call *Call) (StepAction, error) {
		return StepAction{Reply: text}, nil
	}
}

func newLoopFixture(t *testing.T) (*Registry, *Executor) {
	t.Helper()
	r := New()
	if err := r.Register(echoImplSchema(), &echoImpl{}); err != nil {
		t.Fatal(err)
	}
	return r, NewExecutor(r, DefaultBudget())
}

func TestLoopRunsUntilTheModelAnswers(t *testing.T) {
	r, executor := newLoopFixture(t)
	thinker := &scriptedThinker{actions: []action{
		callNow("echo", map[string]interface{}{"text": "one"}),
		callNow("echo", map[string]interface{}{"text": "two"}),
		replyNow("all done"),
	}}

	loop := NewLoop(r, executor, thinker.Think, DefaultLimits())
	outcome := loop.Run(context.Background(), "do the work")

	if outcome.Answer != "all done" {
		t.Fatalf("answer = %q, want the model's reply", outcome.Answer)
	}
	if outcome.StopReason != "answer" {
		t.Fatalf("stop reason = %q, want \"answer\"", outcome.StopReason)
	}
	if outcome.ToolCalls != 2 {
		t.Fatalf("tool calls = %d, want 2", outcome.ToolCalls)
	}
	if len(outcome.Turns) != 3 {
		t.Fatalf("turns = %d, want 3", len(outcome.Turns))
	}
}

func TestLoopStopsAtTheStepLimitAndExplainsItself(t *testing.T) {
	// A model that never answers must be stopped by the limit rather than
	// allowed to loop, and the stop must name which limit fired.
	r, executor := newLoopFixture(t)
	thinker := &scriptedThinker{actions: []action{
		callNow("echo", map[string]interface{}{"text": "one"}),
		callNow("echo", map[string]interface{}{"text": "two"}),
		callNow("echo", map[string]interface{}{"text": "three"}),
		callNow("echo", map[string]interface{}{"text": "four"}),
	}}

	limits := DefaultLimits()
	limits.MaxSteps = 3
	loop := NewLoop(r, executor, thinker.Think, limits)
	outcome := loop.Run(context.Background(), "work")

	if outcome.StopReason != "max_steps" {
		t.Fatalf("stop reason = %q, want \"max_steps\"", outcome.StopReason)
	}
	if outcome.Answer != "" {
		t.Fatalf("an over-budget run produced an answer %q; it should be refused, not answered", outcome.Answer)
	}
	if outcome.Explanation == "" {
		t.Fatal("a forced stop carries no explanation")
	}
	if !strings.Contains(outcome.Explanation, "step") {
		t.Fatalf("the explanation does not name the limit: %q", outcome.Explanation)
	}
}

func TestLoopStopsAtTheToolCallLimit(t *testing.T) {
	r, executor := newLoopFixture(t)
	thinker := &scriptedThinker{actions: []action{
		callNow("echo", map[string]interface{}{"text": "a"}),
		callNow("echo", map[string]interface{}{"text": "b"}),
		callNow("echo", map[string]interface{}{"text": "c"}),
		replyNow("never reached"),
	}}

	limits := DefaultLimits()
	limits.MaxToolCalls = 2
	loop := NewLoop(r, executor, thinker.Think, limits)
	outcome := loop.Run(context.Background(), "work")

	if outcome.StopReason != "max_tool_calls" {
		t.Fatalf("stop reason = %q, want \"max_tool_calls\"", outcome.StopReason)
	}
}

func TestLoopStopsWhenTheModelRepeatsATool(t *testing.T) {
	// A repeated identical call is a loop, not progress. The loop must stop
	// rather than keep asking a model that is clearly stuck.
	r, executor := newLoopFixture(t)
	thinker := &scriptedThinker{actions: []action{
		callNow("echo", map[string]interface{}{"text": "same"}),
		callNow("echo", map[string]interface{}{"text": "same"}),
		callNow("echo", map[string]interface{}{"text": "same"}),
		replyNow("escape"),
	}}

	limits := DefaultLimits()
	limits.MaxIdenticalCalls = 2
	loop := NewLoop(r, executor, thinker.Think, limits)
	outcome := loop.Run(context.Background(), "work")

	if outcome.StopReason != "repeated_call" {
		t.Fatalf("stop reason = %q, want \"repeated_call\"", outcome.StopReason)
	}
	if outcome.Answer != "" {
		t.Fatal("a stuck loop still produced an answer")
	}
}

func TestLoopStopsAtTheDurationLimit(t *testing.T) {
	r, executor := newLoopFixture(t)
	thinker := &scriptedThinker{actions: []action{
		replyNow("never reached"),
	}}

	limits := DefaultLimits()
	limits.MaxDuration = -1 // already expired
	loop := NewLoop(r, executor, thinker.Think, limits)
	outcome := loop.Run(context.Background(), "work")

	if outcome.StopReason != "max_duration" {
		t.Fatalf("stop reason = %q, want \"max_duration\"", outcome.StopReason)
	}
	if outcome.Steps != 0 {
		t.Fatalf("steps = %d, want 0: an expired budget must not run at all", outcome.Steps)
	}
}

func TestLoopStopsAtTheCostLimit(t *testing.T) {
	r, executor := newLoopFixture(t)
	thinker := &scriptedThinker{actions: []action{
		callNow("echo", map[string]interface{}{"text": "costly"}),
		replyNow("never reached"),
	}}

	limits := DefaultLimits()
	// Every think call costs 1.0, so a 0.5 budget refuses on the second step.
	limits.MaxCost = 0.5
	limits.CostPerStep = 1.0
	loop := NewLoop(r, executor, thinker.Think, limits)
	outcome := loop.Run(context.Background(), "work")

	if outcome.StopReason != "max_cost" {
		t.Fatalf("stop reason = %q, want \"max_cost\"", outcome.StopReason)
	}
}

func TestLoopRefusesAnUnknownTool(t *testing.T) {
	// The loop asks the registry, not the executor directly, so a model naming
	// a tool that does not exist is refused at the gate.
	r, executor := newLoopFixture(t)
	thinker := &scriptedThinker{actions: []action{
		callNow("no-such-tool", map[string]interface{}{}),
		replyNow("recovered"),
	}}

	loop := NewLoop(r, executor, thinker.Think, DefaultLimits())
	outcome := loop.Run(context.Background(), "work")

	if outcome.ToolCalls != 0 {
		t.Fatalf("an unknown tool was counted as called: %d", outcome.ToolCalls)
	}
	// The loop recovers and reaches the answer, which is the point of refusing
	// rather than aborting.
	if outcome.StopReason != "answer" {
		t.Fatalf("stop reason = %q, want \"answer\" after recovery", outcome.StopReason)
	}
}

func TestLoopRecordsToolResultsInHistory(t *testing.T) {
	r, executor := newLoopFixture(t)
	thinker := &scriptedThinker{actions: []action{
		callNow("echo", map[string]interface{}{"text": "noted"}),
		replyNow("done"),
	}}

	loop := NewLoop(r, executor, thinker.Think, DefaultLimits())
	outcome := loop.Run(context.Background(), "work")

	var sawResult bool
	for _, turn := range outcome.Turns {
		for _, res := range turn.Results {
			if res.Name == "echo" {
				sawResult = true
			}
		}
	}
	if !sawResult {
		t.Fatal("the loop's history does not contain the tool result, so the model cannot reason over it")
	}
}

func TestLoopStopsOnContextCancellation(t *testing.T) {
	r, executor := newLoopFixture(t)
	thinker := &scriptedThinker{actions: []action{
		callNow("echo", map[string]interface{}{"text": "x"}),
		callNow("echo", map[string]interface{}{"text": "y"}),
	}}

	ctx, cancel := context.WithCancel(context.Background())
	cancel()

	loop := NewLoop(r, executor, thinker.Think, DefaultLimits())
	outcome := loop.Run(ctx, "work")

	if outcome.StopReason != "cancelled" {
		t.Fatalf("stop reason = %q, want \"cancelled\"", outcome.StopReason)
	}
	if outcome.ToolCalls != 0 {
		t.Fatalf("a cancelled run made %d tool calls", outcome.ToolCalls)
	}
}

func TestLoopReportsTheCostItAccrued(t *testing.T) {
	r, executor := newLoopFixture(t)
	thinker := &scriptedThinker{actions: []action{
		replyNow("done"),
	}}
	limits := DefaultLimits()
	limits.CostPerStep = 0.25

	loop := NewLoop(r, executor, thinker.Think, limits)
	outcome := loop.Run(context.Background(), "work")

	if outcome.Cost != 0.25 {
		t.Fatalf("cost = %v, want 0.25 for one think call", outcome.Cost)
	}
}

func TestLoopLimitsDefaultToSaneValues(t *testing.T) {
	limits := DefaultLimits()
	if limits.MaxSteps <= 0 || limits.MaxToolCalls <= 0 || limits.MaxDuration <= 0 {
		t.Fatal("a default limit is unbounded; a default must be bounded")
	}
}

func TestLoopRefusesAGatedToolRatherThanRunningIt(t *testing.T) {
	r := New()
	ran := false
	err := r.Register(Schema{Name: "purchase", Description: "Buy.", Risk: RiskIrreversible, Timeout: time.Second},
		implTool(func(args map[string]interface{}) (map[string]interface{}, error) {
			ran = true
			return map[string]interface{}{}, nil
		}))
	if err != nil {
		t.Fatal(err)
	}
	executor := NewExecutor(r, DefaultBudget())

	thinker := &scriptedThinker{actions: []action{
		callNow("purchase", map[string]interface{}{}),
		replyNow("could not buy it"),
	}}

	loop := NewLoop(r, executor, thinker.Think, DefaultLimits())
	outcome := loop.Run(context.Background(), "work")

	if ran {
		t.Fatal("the loop executed an unapproved irreversible tool")
	}
	if outcome.StopReason != "answer" {
		t.Fatalf("the loop did not recover from a refused tool: %q", outcome.StopReason)
	}
}

func TestLoopHandlesAThinkerError(t *testing.T) {
	r, executor := newLoopFixture(t)
	boom := errors.New("model unavailable")
	thinker := func(ctx context.Context, h History) (StepAction, error) {
		return StepAction{}, boom
	}

	loop := NewLoop(r, executor, thinker, DefaultLimits())
	outcome := loop.Run(context.Background(), "work")

	if outcome.StopReason != "thinker_error" {
		t.Fatalf("stop reason = %q, want \"thinker_error\"", outcome.StopReason)
	}
	if !strings.Contains(outcome.Explanation, "model unavailable") {
		t.Fatalf("the error is not surfaced: %q", outcome.Explanation)
	}
}
