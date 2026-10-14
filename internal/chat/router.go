package chat

import (
	"context"
	"fmt"
	"sync"
	"time"
)

// ---------------------------------------------------------------------------
// Circuit breaker
// ---------------------------------------------------------------------------

// BreakerState is the state of a breaker.
type BreakerState int

const (
	// BreakerClosed lets calls through. This is the starting state.
	BreakerClosed BreakerState = iota
	// BreakerOpen rejects calls without calling the provider. A call rejected
	// here fails fast rather than waiting for a timeout.
	BreakerOpen
	// BreakerHalfOpen allows a single probe call through, to discover whether
	// the provider recovered.
	BreakerHalfOpen
)

func (s BreakerState) String() string {
	switch s {
	case BreakerOpen:
		return "open"
	case BreakerHalfOpen:
		return "half-open"
	default:
		return "closed"
	}
}

// BreakerConfig configures a breaker.
type BreakerConfig struct {
	// FailureThreshold is how many consecutive failures open the breaker.
	FailureThreshold int
	// OpenFor is how long the breaker stays open before allowing a probe.
	OpenFor time.Duration
	// ProbeTimeout bounds a half-open probe, so a hung provider cannot hold
	// the half-open state forever.
	ProbeTimeout time.Duration
}

// DefaultBreakerConfig opens after five consecutive failures and re-probes
// after thirty seconds.
func DefaultBreakerConfig() BreakerConfig {
	return BreakerConfig{
		FailureThreshold: 5,
		OpenFor:          30 * time.Second,
		ProbeTimeout:     10 * time.Second,
	}
}

// Breaker stops calling a provider that is failing.
//
// It exists to turn a hard failure into a fast one: without it, every request
// to a down provider pays the full timeout, so the caller's latency is
// multiplied by the provider's timeout and the work queue backs up behind
// requests that cannot succeed.
type Breaker struct {
	cfg    BreakerConfig
	mu     sync.Mutex
	state  BreakerState
	fails  int
	opened time.Time
	now    func() time.Time
}

// NewBreaker returns a closed breaker.
func NewBreaker(cfg BreakerConfig, now func() time.Time) *Breaker {
	if now == nil {
		now = time.Now
	}
	if cfg.FailureThreshold <= 0 {
		cfg.FailureThreshold = DefaultBreakerConfig().FailureThreshold
	}
	return &Breaker{cfg: cfg, state: BreakerClosed, now: now}
}

// State returns the current state, advancing an expired open breaker to
// half-open as a side effect of the read.
func (b *Breaker) State() BreakerState {
	b.mu.Lock()
	defer b.mu.Unlock()
	b.advanceLocked()
	return b.state
}

// Allow reports whether a call may proceed. It is the only method a caller
// needs before a call; Success and Failure report the outcome.
func (b *Breaker) Allow() bool {
	b.mu.Lock()
	defer b.mu.Unlock()
	b.advanceLocked()
	return b.state != BreakerOpen
}

func (b *Breaker) advanceLocked() {
	if b.state == BreakerOpen && b.now().Sub(b.opened) >= b.cfg.OpenFor {
		b.state = BreakerHalfOpen
	}
}

// Success records a successful call and closes the breaker.
func (b *Breaker) Success() {
	b.mu.Lock()
	defer b.mu.Unlock()
	b.fails = 0
	b.state = BreakerClosed
}

// Failure records a failed call and opens the breaker once the threshold is
// reached. Consecutive is the point: an isolated timeout must not disable a
// working provider.
func (b *Breaker) Failure() {
	b.mu.Lock()
	defer b.mu.Unlock()
	b.fails++
	if b.state == BreakerHalfOpen || b.fails >= b.cfg.FailureThreshold {
		b.state = BreakerOpen
		b.opened = b.now()
	}
}

// ---------------------------------------------------------------------------
// Router
// ---------------------------------------------------------------------------

// Route is one candidate in the decision order.
type Route struct {
	// Model is the model to use.
	Model string
	// Why is the human-readable reason. It is recorded in the decision so a
	// routing choice can be audited without re-deriving the rule.
	Why string
	// MinTier is the minimum capability tier this route serves. A route with
	// tier 3 is not a candidate for a request that needs tier 4.
	MinTier int
	// NeedsTools restricts this route to requests that can use tools.
	NeedsTools bool
	// NeedsVision restricts this route to requests with images.
	NeedsVision bool
	// MaxPromptTokens is the largest prompt this route accepts. Zero means
	// the model's own context window governs.
	MaxPromptTokens int
}

// Decision is the router's output, including why.
type Decision struct {
	Model string `json:"model"`
	Why   string `json:"why"`
	// RuledOut lists the routes that were considered and why each was
	// rejected. A routing decision that cannot explain itself is a decision
	// nobody can review.
	RuledOut []string `json:"ruled_out,omitempty"`
	// Fallbacks are the remaining candidates in order.
	Fallbacks []string `json:"fallbacks,omitempty"`
}

// Router selects a model for a request and walks a fallback chain when a
// provider fails.
//
// Selection and execution are split deliberately. Selection is pure: the same
// request always yields the same decision, so a routing rule can be tested
// without a provider. Execution is where a fallback happens, because only
// execution knows a provider failed.
type Router struct {
	registry  *Registry
	providers map[string]Provider
	breakers  map[string]*Breaker
	now       func() time.Time

	mu sync.RWMutex
}

// NewRouter returns a router over the given providers.
func NewRouter(registry *Registry, providers map[string]Provider, now func() time.Time) *Router {
	if registry == nil {
		registry = DefaultRegistry()
	}
	if now == nil {
		now = time.Now
	}
	breakers := make(map[string]*Breaker, len(providers))
	for name := range providers {
		breakers[name] = NewBreaker(DefaultBreakerConfig(), now)
	}
	return &Router{
		registry:  registry,
		providers: providers,
		breakers:  breakers,
		now:       now,
	}
}

// Register adds a provider to the router.
func (r *Router) Register(name string, p Provider) {
	r.mu.Lock()
	defer r.mu.Unlock()
	r.providers[name] = p
	if r.breakers[name] == nil {
		r.breakers[name] = NewBreaker(DefaultBreakerConfig(), r.now)
	}
}

// Breaker returns the breaker for a model, or nil.
func (r *Router) Breaker(model string) *Breaker {
	r.mu.RLock()
	defer r.mu.RUnlock()
	return r.breakers[model]
}

// Select chooses a model for a request from the ordered routes.
//
// The first route whose model is known and whose capabilities fit wins. Every
// other route is recorded as ruled out with its reason, so the decision can be
// reviewed without re-deriving the rules.
func (r *Router) Select(routes []Route, req *Request) Decision {
	promptTokens := EstimateTokens(req)

	// This package's Message carries text only, so a router cannot tell a
	// request with images apart. The capability check therefore keys on what
	// is knowable here, and a vision-capable route is preferred by tier
	// rather than selected on evidence the request does not carry.
	wantsTools := req.Tools != nil
	_ = wantsTools

	decision := Decision{}
	for _, route := range routes {
		caps, known := r.registry.Get(route.Model)
		if !known {
			// An unregistered model is not silently assumed usable. The strict
			// fallback gives it the narrowest capability in the registry, so
			// it can still serve a request it genuinely fits, but it is never
			// credited with a capability nobody declared.
			caps = r.registry.StrictFallback()
			caps.Model = route.Model
		}
		if route.MinTier > 0 && caps.Tier < route.MinTier {
			decision.RuledOut = append(decision.RuledOut,
				route.Model+": tier below required capability")
			continue
		}
		if !caps.Supports(wantsTools, false) {
			decision.RuledOut = append(decision.RuledOut, route.Model+": does not support this request")
			continue
		}
		limit := caps.ContextTokens
		if route.MaxPromptTokens > 0 && route.MaxPromptTokens < limit {
			limit = route.MaxPromptTokens
		}
		if room := limit - caps.MaxOutputTokens; room > 0 && promptTokens > room {
			decision.RuledOut = append(decision.RuledOut, route.Model+": prompt exceeds context window")
			continue
		}
		if decision.Model == "" {
			decision.Model = route.Model
			decision.Why = route.Why
			continue
		}
		decision.Fallbacks = append(decision.Fallbacks, route.Model)
	}

	if decision.Model == "" {
		decision.Why = "no route matched"
		if len(decision.RuledOut) == 0 {
			decision.RuledOut = append(decision.RuledOut, "no routes configured")
		}
	}
	return decision
}

// CompleteWithFallback tries the decision's model, then each fallback, until
// a provider produces a stream.
//
// A provider whose breaker is open is skipped rather than attempted: the point
// of the breaker is to fail fast instead of paying the timeout on every
// request. Each attempt's outcome is recorded so the state is accurate for the
// next request.
func (r *Router) CompleteWithFallback(
	ctx context.Context,
	userID, tenantID string,
	req *Request,
	decision Decision,
) (<-chan Result, error) {
	candidates := append([]string{decision.Model}, decision.Fallbacks...)

	var lastErr error
	for _, model := range candidates {
		if model == "" {
			continue
		}
		r.mu.RLock()
		provider := r.providers[model]
		breaker := r.breakers[model]
		r.mu.RUnlock()
		if provider == nil {
			continue
		}
		if breaker != nil && !breaker.Allow() {
			lastErr = fmt.Errorf("chat: breaker open for model %q", model)
			continue
		}

		scoped := *req
		scoped.Model = model
		// NoSpend is used because metering belongs to the caller's spend gate,
		// not the router: the router decides which provider to call, the gate
		// decides whether it may be paid for.
		orchestrator, err := New(provider, NoSpend{})
		if err != nil {
			lastErr = err
			continue
		}
		results, err := orchestrator.Run(ctx, userID, tenantID, &scoped)
		if err != nil {
			if breaker != nil {
				breaker.Failure()
			}
			lastErr = err
			continue
		}
		if breaker != nil {
			breaker.Success()
		}
		return results, nil
	}

	if lastErr == nil {
		lastErr = fmt.Errorf("chat: no provider available for %q", decision.Model)
	}
	return nil, lastErr
}
