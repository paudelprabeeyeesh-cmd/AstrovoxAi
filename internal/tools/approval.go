package tools

import (
	"crypto/rand"
	"encoding/hex"
	"fmt"
	"sync"
	"time"
)

// newID returns a random identifier.
//
// Local to this package rather than shared: the tools package must not depend
// on chat for an identifier, and a shared helper would couple two packages for
// no benefit beyond a name.
func newID(prefix string) string {
	buf := make([]byte, 12)
	if _, err := rand.Read(buf); err != nil {
		return fmt.Sprintf("%s_%d", prefix, time.Now().UnixNano())
	}
	return prefix + hex.EncodeToString(buf)
}

// Human approval gates over the actions a tool can take.
//
// Risk already answers "may this run unattended". This adds the thing Risk
// cannot: a terminal command and a purchase are both irreversible, but an audit
// that records only "irreversible" cannot tell an operator what actually
// happened. Action is that finer grain, and it is what the recorded decision
// names.
//
// Every decision is recorded, append-only, including the ones that refuse. A
// gate that records only its grants cannot answer "who approved this" for the
// calls that were refused and why, which is the question an incident review
// actually asks.

// Action is what a tool does.
type Action string

// The action taxonomy. Reads and writes are unattended; everything after
// them requires a human decision before the call runs.
const (
	ActionRead         Action = "read"
	ActionWrite        Action = "write"
	ActionExternal     Action = "external_communication"
	ActionPurchase     Action = "purchase"
	ActionAccessChange Action = "access_change"
	ActionTerminal     Action = "terminal_command"
	ActionNetwork      Action = "network_access"
	ActionBroadEdit    Action = "broad_edit"
	ActionIrreversible Action = "irreversible"
)

// gatedActions are the actions a human must approve.
//
// A set rather than a default-deny check, so a new action that has not been
// classified is NOT gated. That is deliberate but asymmetric: an unclassified
// action falls through to the Risk check, which still gates external and
// irreversible. A new Action that means neither is unattended by design, and
// the fix is to classify it, not to gate everything.
var gatedActions = map[Action]bool{
	ActionExternal:     true,
	ActionPurchase:     true,
	ActionAccessChange: true,
	ActionTerminal:     true,
	ActionNetwork:      true,
	ActionBroadEdit:    true,
	ActionIrreversible: true,
}

// Gated reports whether an action requires a human decision.
func (a Action) Gated() bool { return gatedActions[a] }

// String renders an action for an audit line.
func (a Action) String() string { return string(a) }

// RequiresGate reports whether a schema's declaration needs approval. Either
// its risk is gated or any of its actions is, so a tool cannot escape by
// declaring a benign risk and an irreversible action.
func (s Schema) RequiresGate() bool {
	if s.Risk.RequiresApproval() {
		return true
	}
	for _, a := range s.Actions {
		if a.Gated() {
			return true
		}
	}
	return false
}

// ---------------------------------------------------------------------------
// Decisions
// ---------------------------------------------------------------------------

// Decision is one recorded human decision about one call.
//
// Granted false is a refusal and is recorded just as a grant is: the audit must
// show both, including the reason.
type Decision struct {
	DecisionID  string    `json:"decision_id"`
	Fingerprint string    `json:"fingerprint"`
	Tool        string    `json:"tool"`
	Actions     []Action  `json:"actions,omitempty"`
	Granted     bool      `json:"granted"`
	Approver    string    `json:"approver,omitempty"`
	Reason      string    `json:"reason,omitempty"`
	DecidedAt   time.Time `json:"decided_at"`
	ExpiresAt   time.Time `json:"expires_at,omitempty"`

	// Revoked records a withdrawal, which is a separate fact from a denial: a
	// grant that was withdrawn must not read as one that was never given.
	Revoked   bool      `json:"revoked,omitempty"`
	RevokedAt time.Time `json:"revoked_at,omitempty"`
}

// Effective reports whether this decision currently authorises the call.
//
// A revoked or expired grant authorises nothing, so both read as refused rather
// than as "approved once".
func (d Decision) Effective(now time.Time) bool {
	return d.Granted && !d.Revoked && (d.ExpiresAt.IsZero() || now.Before(d.ExpiresAt))
}

// ---------------------------------------------------------------------------
// The gate
// ---------------------------------------------------------------------------

// ApprovalGate records decisions and answers whether a call may run.
//
// It implements Approver, so it drops into the Executor unchanged. It owns its
// own decision log rather than asking a tool to record itself.
type ApprovalGate struct {
	mu        sync.Mutex
	ttl       time.Duration
	now       func() time.Time
	decisions []Decision
	byID      map[string]int // index into decisions
	byFP      map[string]int // index into decisions, latest effective winner
}

// NewApprovalGate returns a gate with no decisions.
//
// ttl bounds a grant: an approval with no expiry is how a one-off decision
// becomes permanent permission.
func NewApprovalGate(ttl time.Duration, now func() time.Time) *ApprovalGate {
	if ttl <= 0 {
		ttl = 15 * time.Minute
	}
	if now == nil {
		now = time.Now
	}
	return &ApprovalGate{
		ttl:  ttl,
		now:  now,
		byID: map[string]int{},
		byFP: map[string]int{},
	}
}

// Request opens a decision for a call. The call is refused until a decision is
// recorded against it, so a request that is never answered is a refusal.
func (g *ApprovalGate) Request(call Call, actions []Action) (Decision, error) {
	if !schemaRequiresGate(call, actions) {
		return Decision{}, fmt.Errorf("tools: call %q does not need approval", call.Name)
	}
	decision := Decision{
		Fingerprint: Fingerprint(call),
		Tool:        call.Name,
		Actions:     actions,
		Granted:     false,
	}
	return decision, nil
}

// schemaRequiresGate checks whether a call is gated, using the registry's
// declaration when the gate has one and the caller's list otherwise. The
// caller's list is authoritative when present: a gate that trusts a
// caller-supplied action list to *reduce* what is gated would let a model
// remove the requirement by misdescribing the call.
func schemaRequiresGate(call Call, actions []Action) bool {
	return actionsAreGated(actions)
}

// actionsAreGated reports whether any listed action needs approval.
func actionsAreGated(actions []Action) bool {
	for _, a := range actions {
		if a.Gated() {
			return true
		}
	}
	return false
}

// Grant approves a call and records it.
func (g *ApprovalGate) Grant(call Call, actions []Action, approver, reason string) (Decision, error) {
	return g.decide(call, actions, true, approver, reason)
}

// Deny refuses a call and records it, with the reason.
func (g *ApprovalGate) Deny(call Call, actions []Action, approver, reason string) (Decision, error) {
	return g.decide(call, actions, false, approver, reason)
}

func (g *ApprovalGate) decide(call Call, actions []Action, granted bool, approver, reason string) (Decision, error) {
	if approver == "" {
		// A decision with no actor cannot be reviewed. Refusing is the only
		// option that leaves an auditable trail.
		return Decision{}, fmt.Errorf("tools: a decision needs an approver")
	}
	g.mu.Lock()
	defer g.mu.Unlock()

	now := g.now()
	decision := Decision{
		DecisionID:  "appr_" + newID(""),
		Fingerprint: Fingerprint(call),
		Tool:        call.Name,
		Actions:     actions,
		Granted:     granted,
		Approver:    approver,
		Reason:      reason,
		DecidedAt:   now,
	}
	if granted {
		decision.ExpiresAt = now.Add(g.ttl)
	}
	g.appendLocked(decision)
	return decision, nil
}

// Revoke withdraws a grant, recording the withdrawal separately from the
// original grant: a revoked grant must not read as one that was never given.
func (g *ApprovalGate) Revoke(fingerprint, approver, reason string) error {
	g.mu.Lock()
	defer g.mu.Unlock()

	idx, ok := g.byFP[fingerprint]
	if !ok {
		return fmt.Errorf("tools: no decision recorded for %q", fingerprint)
	}
	now := g.now()
	existing := g.decisions[idx]
	revocation := existing
	revocation.DecisionID = "appr_" + newID("")
	revocation.Granted = false
	revocation.Revoked = true
	revocation.RevokedAt = now
	revocation.Approver = approver
	revocation.Reason = reason
	revocation.DecidedAt = now
	revocation.ExpiresAt = time.Time{}
	g.appendLocked(revocation)
	return nil
}

// Approve implements Approver: nil when the call may proceed.
//
// A call that was never decided is refused, so the default is a refusal rather
// than an allowance.
func (g *ApprovalGate) Approve(call Call, schema Schema) error {
	actions := schema.Actions
	if !actionsAreGated(actions) && !schema.Risk.RequiresApproval() {
		return nil
	}

	g.mu.Lock()
	defer g.mu.Unlock()

	now := g.now()
	idx, ok := g.byFP[Fingerprint(call)]
	if !ok {
		return fmt.Errorf("%w: %q (no decision recorded)", ErrApprovalRequired, call.Name)
	}
	decision := g.decisions[idx]
	if !decision.Effective(now) {
		if decision.Revoked {
			return fmt.Errorf("%w: %q (approval was revoked)", ErrApprovalRequired, call.Name)
		}
		if decision.ExpiresAt.IsZero() {
			return fmt.Errorf("%w: %q (never approved)", ErrApprovalRequired, call.Name)
		}
		return fmt.Errorf("%w: %q (approval expired at %s)", ErrApprovalRequired, call.Name, decision.ExpiresAt.Format(time.RFC3339))
	}
	return nil
}

// Decisions returns the audit trail for an approver, newest first.
//
// Every approver's decisions are returned when approver is empty, because an
// audit that can only show one actor's decisions cannot show that anyone was
// refused.
func (g *ApprovalGate) Decisions(approver string) []Decision {
	g.mu.Lock()
	defer g.mu.Unlock()

	out := make([]Decision, 0, len(g.decisions))
	for _, d := range g.decisions {
		if approver != "" && d.Approver != approver {
			continue
		}
		out = append(out, d)
	}
	for i, j := 0, len(out)-1; i < j; i, j = i+1, j-1 {
		out[i], out[j] = out[j], out[i]
	}
	return out
}

// Counts summarises decisions by outcome, for a dashboard.
func (g *ApprovalGate) Counts() map[string]int {
	g.mu.Lock()
	defer g.mu.Unlock()

	counts := map[string]int{"granted": 0, "denied": 0, "revoked": 0, "total": 0}
	for _, d := range g.decisions {
		counts["total"]++
		if d.Revoked {
			counts["revoked"]++
		} else if d.Granted {
			counts["granted"]++
		} else {
			counts["denied"]++
		}
	}
	return counts
}

// appendLocked records a decision and makes it the latest for its fingerprint.
//
// The log is never shortened — a revocation is a new entry, not an edit — while
// byFP points at the latest, so a later decision supersedes an earlier one
// without erasing it.
func (g *ApprovalGate) appendLocked(d Decision) {
	g.decisions = append(g.decisions, d)
	idx := len(g.decisions) - 1
	g.byID[d.DecisionID] = idx
	g.byFP[d.Fingerprint] = idx
}
