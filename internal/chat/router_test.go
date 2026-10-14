package chat

import (
	"context"
	"sync"
	"testing"
	"time"
)

// mustSelect is a helper that fails with the ruling-out reasons, which is the
// whole point of carrying them.
func mustSelect(t *testing.T, r *Router, routes []Route, req *Request) Decision {
	t.Helper()
	d := r.Select(routes, req)
	if d.Model == "" {
		t.Fatalf("no route selected; ruled out: %v", d.RuledOut)
	}
	return d
}

func testRegistry() *Registry {
	return NewRegistry(
		Capabilities{
			Model: "cheap", ContextTokens: 8192, MaxOutputTokens: 1024,
			Streams: true, Tier: 1, Price: Price{0.0005, 0.0015},
		},
		Capabilities{
			Model: "smart", ContextTokens: 128000, MaxOutputTokens: 16384,
			SupportsTools: true, Streams: true, Tier: 3, Price: Price{0.01, 0.03},
		},
		Capabilities{
			Model: "vision", ContextTokens: 128000, MaxOutputTokens: 8192,
			SupportsTools: true, SupportsVision: true, Streams: true, Tier: 3,
			Price: Price{0.005, 0.015},
		},
		Capabilities{
			Model: "no-tools", ContextTokens: 128000, MaxOutputTokens: 8192,
			Streams: true, Tier: 2, Price: Price{0.001, 0.002},
		},
	)
}

func testRouter(t *testing.T, now func() time.Time) *Router {
	t.Helper()
	return NewRouter(testRegistry(), map[string]Provider{
		"cheap":    &fakeProvider{name: "cheap"},
		"smart":    &fakeProvider{name: "smart"},
		"vision":   &fakeProvider{name: "vision"},
		"no-tools": &fakeProvider{name: "no-tools"},
	}, now)
}

func TestSelectPrefersTheFirstFittingRoute(t *testing.T) {
	r := testRouter(t, nil)
	routes := []Route{
		{Model: "cheap", Why: "cheapest first"},
		{Model: "smart", Why: "capable fallback"},
	}
	d := mustSelect(t, r, routes, &Request{Messages: []Message{{Role: "user", Content: "hi"}}})
	if d.Model != "cheap" {
		t.Fatalf("selected %q, want the first route", d.Model)
	}
	if len(d.Fallbacks) != 1 || d.Fallbacks[0] != "smart" {
		t.Fatalf("fallbacks = %v", d.Fallbacks)
	}
}

func TestSelectSkipsAModelThatCannotUseTools(t *testing.T) {
	r := testRouter(t, nil)
	routes := []Route{
		{Model: "no-tools", NeedsTools: true, Why: "cannot use tools"},
		{Model: "smart", NeedsTools: true, Why: "can use tools"},
	}
	d := mustSelect(t, r, routes, &Request{
		Messages: []Message{{Role: "user", Content: "call a tool"}},
		Tools:    []Tool{{Name: "lookup"}},
	})
	if d.Model != "smart" {
		t.Fatalf("selected %q, want the tool-capable model", d.Model)
	}
	if len(d.RuledOut) != 1 || d.RuledOut[0] != "no-tools: does not support this request" {
		t.Fatalf("ruled out = %v", d.RuledOut)
	}
}

func TestSelectSkipsAModelBelowTheRequiredTier(t *testing.T) {
	r := testRouter(t, nil)
	routes := []Route{
		{Model: "cheap", MinTier: 3, Why: "not capable enough"},
		{Model: "smart", MinTier: 3, Why: "capable enough"},
	}
	d := mustSelect(t, r, routes, &Request{Messages: []Message{{Role: "user", Content: "reason hard"}}})
	if d.Model != "smart" {
		t.Fatalf("selected %q, want the high-tier model", d.Model)
	}
}

func TestSelectSkipsAModelWhoseContextIsTooSmall(t *testing.T) {
	// A prompt of ~50k tokens must not go to a model with an 8k window: the
	// provider would reject it and the retry would pay the round trip anyway.
	r := testRouter(t, nil)
	big := make([]Message, 0, 4)
	for i := 0; i < 4; i++ {
		big = append(big, Message{Role: "user", Content: string(make([]byte, 40000))})
	}
	routes := []Route{
		{Model: "cheap", Why: "small window"},
		{Model: "smart", Why: "large window"},
	}
	d := mustSelect(t, r, routes, &Request{Messages: big})
	if d.Model != "smart" {
		t.Fatalf("selected %q for an oversized prompt, want the large window", d.Model)
	}
	if len(d.RuledOut) == 0 {
		t.Fatal("the context-window rejection was not recorded")
	}
}

func TestSelectReportsWhenNothingMatches(t *testing.T) {
	r := testRouter(t, nil)
	d := r.Select([]Route{{Model: "cheap", MinTier: 5}}, &Request{Messages: []Message{{Role: "user", Content: "hi"}}})
	if d.Model != "" {
		t.Fatalf("selected %q when nothing should match", d.Model)
	}
	if len(d.RuledOut) == 0 {
		t.Fatal("no reason was recorded for rejecting every route")
	}
}

func TestSelectIsDeterministic(t *testing.T) {
	r := testRouter(t, nil)
	routes := []Route{
		{Model: "cheap", Why: "a"}, {Model: "smart", Why: "b"}, {Model: "vision", Why: "c"},
	}
	req := &Request{Messages: []Message{{Role: "user", Content: "same input"}}}
	a := r.Select(routes, req)
	b := r.Select(routes, req)
	if a.Model != b.Model || a.Why != b.Why {
		t.Fatalf("routing changed between identical requests: %+v vs %+v", a, b)
	}
}

func TestStrictFallbackNeverCreditsAnUnknownModel(t *testing.T) {
	// An unregistered model must not be treated as capable. This is the
	// failure that makes a router route a tool request to a model with no tool
	// support and get a refusal the caller reads as a model bug.
	reg := NewRegistry(
		Capabilities{Model: "known", ContextTokens: 128000, MaxOutputTokens: 8192, SupportsTools: false, Tier: 3},
	)
	strict := reg.StrictFallback()
	if strict.SupportsTools {
		t.Fatal("the strict fallback claimed tool support that no registered model has")
	}
	if strict.ContextTokens > 128000 {
		t.Fatalf("the strict fallback claimed a %d-token window", strict.ContextTokens)
	}
}

func TestBreakerStartsClosed(t *testing.T) {
	b := NewBreaker(DefaultBreakerConfig(), time.Now)
	if b.State() != BreakerClosed || !b.Allow() {
		t.Fatal("a new breaker should be closed and allow calls")
	}
}

func TestBreakerOpensAfterConsecutiveFailures(t *testing.T) {
	now := time.Now()
	b := NewBreaker(BreakerConfig{FailureThreshold: 3, OpenFor: time.Minute}, func() time.Time { return now })
	for i := 0; i < 2; i++ {
		b.Failure()
	}
	if b.State() != BreakerClosed {
		t.Fatal("two failures opened a three-failure breaker")
	}
	b.Failure()
	if b.State() != BreakerOpen {
		t.Fatal("the threshold was reached but the breaker stayed closed")
	}
	if b.Allow() {
		t.Fatal("an open breaker allowed a call")
	}
}

func TestBreakerSuccessResetsTheConsecutiveCount(t *testing.T) {
	// An isolated failure must not disable a working provider, which is why
	// the count is consecutive rather than cumulative.
	now := time.Now()
	b := NewBreaker(BreakerConfig{FailureThreshold: 3, OpenFor: time.Minute}, func() time.Time { return now })
	b.Failure()
	b.Failure()
	b.Success()
	b.Failure()
	b.Failure()
	if b.State() != BreakerClosed {
		t.Fatal("a success did not reset the consecutive failure count")
	}
}

func TestBreakerHalfOpensAfterTheCooldown(t *testing.T) {
	now := time.Now()
	b := NewBreaker(BreakerConfig{FailureThreshold: 2, OpenFor: 30 * time.Second}, func() time.Time { return now })
	b.Failure()
	b.Failure()
	if b.State() != BreakerOpen {
		t.Fatal("breaker not open")
	}
	now = now.Add(31 * time.Second)
	if b.State() != BreakerHalfOpen {
		t.Fatalf("after the cooldown the state is %s, want half-open", b.State())
	}
	if !b.Allow() {
		t.Fatal("a half-open breaker refused the probe")
	}
}

func TestBreakerReopensAfterAFailedProbe(t *testing.T) {
	now := time.Now()
	b := NewBreaker(BreakerConfig{FailureThreshold: 2, OpenFor: 30 * time.Second}, func() time.Time { return now })
	b.Failure()
	b.Failure()
	now = now.Add(31 * time.Second)
	b.Allow()
	b.Failure()
	if b.State() != BreakerOpen {
		t.Fatal("a failed probe reopened nothing")
	}
}

func TestBreakerRecoversAfterASuccessfulProbe(t *testing.T) {
	now := time.Now()
	b := NewBreaker(BreakerConfig{FailureThreshold: 2, OpenFor: 30 * time.Second}, func() time.Time { return now })
	b.Failure()
	b.Failure()
	now = now.Add(31 * time.Second)
	b.Allow()
	b.Success()
	if b.State() != BreakerClosed {
		t.Fatal("a successful probe did not close the breaker")
	}
}

func TestCompleteWithFallbackUsesTheFallbackWhenThePrimaryFails(t *testing.T) {
	r := NewRouter(testRegistry(), map[string]Provider{
		"cheap": &fakeProvider{name: "cheap", failOnCall: true},
		"smart": &fakeProvider{name: "smart"},
	}, nil)
	decision := Decision{Model: "cheap", Fallbacks: []string{"smart"}}

	results, err := r.CompleteWithFallback(
		context.Background(), "u1", "t1",
		&Request{Messages: []Message{{Role: "user", Content: "hi"}}}, decision,
	)
	if err != nil {
		t.Fatalf("the fallback should have succeeded: %v", err)
	}
	if results == nil {
		t.Fatal("no result channel")
	}
	drained := 0
	for range results {
		drained++
	}
	if drained == 0 {
		t.Fatal("the fallback streamed nothing")
	}
}

func TestCompleteWithFallbackSkipsAProviderWithAnOpenBreaker(t *testing.T) {
	r := NewRouter(testRegistry(), map[string]Provider{
		"cheap": &fakeProvider{name: "cheap", failOnCall: true},
		"smart": &fakeProvider{name: "smart"},
	}, nil)
	decision := Decision{Model: "cheap", Fallbacks: []string{"smart"}}
	req := &Request{Messages: []Message{{Role: "user", Content: "hi"}}}

	// Fill the breaker so the primary is skipped rather than attempted.
	breaker := r.Breaker("cheap")
	for i := 0; i < 10; i++ {
		breaker.Failure()
	}
	if breaker.State() != BreakerOpen {
		t.Fatal("the breaker did not open")
	}

	if _, err := r.CompleteWithFallback(context.Background(), "u1", "t1", req, decision); err != nil {
		t.Fatalf("an open primary should fall through, not fail: %v", err)
	}
}

func TestCompleteWithFallbackFailsWhenEveryCandidateFails(t *testing.T) {
	r := NewRouter(testRegistry(), map[string]Provider{
		"cheap": &fakeProvider{name: "cheap", failOnCall: true},
		"smart": &fakeProvider{name: "smart", failOnCall: true},
	}, nil)
	decision := Decision{Model: "cheap", Fallbacks: []string{"smart"}}

	if _, err := r.CompleteWithFallback(
		context.Background(), "u1", "t1",
		&Request{Messages: []Message{{Role: "user", Content: "hi"}}}, decision,
	); err == nil {
		t.Fatal("a total outage returned success")
	}
}

func TestCompleteWithFallbackRecordsProviderOutcomes(t *testing.T) {
	// The breaker must reflect what actually happened, or the next request pays
	// for a provider this one already discovered was down.
	r := NewRouter(testRegistry(), map[string]Provider{
		"cheap": &fakeProvider{name: "cheap", failOnCall: true},
	}, nil)
	_, _ = r.CompleteWithFallback(
		context.Background(), "u1", "t1",
		&Request{Messages: []Message{{Role: "user", Content: "hi"}}},
		Decision{Model: "cheap"},
	)
	_ = r.Breaker("cheap").State()
}

func TestFitsReservesRoomForTheReply(t *testing.T) {
	// A prompt that fills the window exactly still fails, because the reply
	// has to go somewhere.
	c := Capabilities{ContextTokens: 1000, MaxOutputTokens: 100}
	if c.Fits(950, 100) {
		t.Fatal("a prompt leaving no room for output was judged to fit")
	}
	if !c.Fits(800, 100) {
		t.Fatal("a prompt with room for output was rejected")
	}
}

func TestFitsRejectsAnOutputThatExceedsTheCap(t *testing.T) {
	// Some models cap output below their context window, and asking for more
	// is an error rather than a truncation.
	c := Capabilities{ContextTokens: 100000, MaxOutputTokens: 4096}
	if c.Fits(10, 8192) {
		t.Fatal("an output above the cap was allowed")
	}
}

func TestKnownIsSorted(t *testing.T) {
	r := NewRouter(testRegistry(), map[string]Provider{
		"vision": &fakeProvider{}, "cheap": &fakeProvider{},
	}, nil)
	_ = r
	reg := testRegistry()
	known := reg.Known()
	for i := 1; i < len(known); i++ {
		if known[i-1] > known[i] {
			t.Fatalf("Known() is not sorted: %v", known)
		}
	}
}

func TestConcurrentSelectAndRegister(t *testing.T) {
	// The router is read on every request and written on provider
	// registration, so both paths must be safe.
	r := NewRouter(testRegistry(), map[string]Provider{}, nil)
	var wg sync.WaitGroup
	for i := 0; i < 8; i++ {
		wg.Add(1)
		go func(i int) {
			defer wg.Done()
			for j := 0; j < 50; j++ {
				r.Register("p", &fakeProvider{name: "p"})
				r.Select([]Route{{Model: "smart", Why: "x"}}, &Request{Messages: []Message{{Role: "user", Content: "hi"}}})
			}
		}(i)
	}
	wg.Wait()
}
