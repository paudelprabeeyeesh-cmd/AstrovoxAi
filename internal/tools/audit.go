package tools

import (
	"errors"
	"regexp"
	"sync"
	"time"
)

// Run recording, replay, and the audit view.
//
// Three things an operator needs after the fact that a log line cannot give:
//
//   1. What the loop actually did, in enough detail to reconstruct it.
//   2. A way to re-run that without calling the model, because a recording
//      that can only be reviewed is a recording that cannot be debugged.
//   3. An audit someone other than the author can read.
//
// Redaction happens on write. A record containing a credential is a credential
// in the repo, and scrubbing at read time is scrubbing that depends on someone
// remembering to do it.

// Redactor scrubs credential-shaped text.
type Redactor struct {
	patterns []*regexp.Regexp
}

// DefaultRedactor matches the credential shapes that turn up in model output.
var DefaultRedactor = &Redactor{
	patterns: []*regexp.Regexp{
		regexp.MustCompile(`\bsk-[A-Za-z0-9_-]{12,}`),
		regexp.MustCompile(`\bAKIA[A-Z0-9]{12,}`),
		regexp.MustCompile(`\bghp_[A-Za-z0-9]{12,}`),
		regexp.MustCompile(`\bxox[baprs]-[A-Za-z0-9-]{10,}`),
		regexp.MustCompile(`\bglpat-[A-Za-z0-9_-]{12,}`),
		regexp.MustCompile(`(?i)\bbearer\s+[A-Za-z0-9._-]{16,}`),
		regexp.MustCompile(`-----BEGIN [A-Z ]*PRIVATE KEY-----[\s\S]*?-----END [A-Z ]*PRIVATE KEY-----`),
	},
}

// Redact replaces every credential-shaped run with a marker.
func (r *Redactor) Redact(text string) string {
	for _, pattern := range r.patterns {
		text = pattern.ReplaceAllString(text, "[REDACTED]")
	}
	return text
}

// ContainsSecret reports whether a text holds a credential shape.
func (r *Redactor) ContainsSecret(text string) bool {
	for _, pattern := range r.patterns {
		if pattern.MatchString(text) {
			return true
		}
	}
	return false
}

// ---------------------------------------------------------------------------
// Records
// ---------------------------------------------------------------------------

// RunRecord is one recorded run.
type RunRecord struct {
	RunID      string    `json:"run_id"`
	Task       string    `json:"task"`
	RecordedAt time.Time `json:"recorded_at"`
	// Redactions counts credentials removed, so a reviewer can tell a clean
	// record from one that had something scrubbed.
	Redactions  int     `json:"redactions"`
	Answer      string  `json:"answer,omitempty"`
	StopReason  string  `json:"stop_reason"`
	Explanation string  `json:"explanation,omitempty"`
	Steps       int     `json:"steps"`
	ToolCalls   int     `json:"tool_calls"`
	Cost        float64 `json:"cost"`
}

// TurnRecord is one recorded step, with its output redacted.
type TurnRecord struct {
	Tool       string                 `json:"tool,omitempty"`
	Arguments  map[string]interface{} `json:"arguments,omitempty"`
	Output     map[string]interface{} `json:"output,omitempty"`
	OutputText string                 `json:"output_text,omitempty"`
	Skipped    bool                   `json:"skipped,omitempty"`
	Error      string                 `json:"error,omitempty"`
	DurationMs int64                  `json:"duration_ms"`
	Redactions int                    `json:"redactions"`
}

// FullRecord is a run plus its per-turn detail.
type FullRecord struct {
	Run   RunRecord    `json:"run"`
	Turns []TurnRecord `json:"turns,omitempty"`
}

// RunRecorder stores records, redacting as they are written.
type RunRecorder struct {
	mu       sync.Mutex
	records  map[string]*FullRecord
	redactor *Redactor
}

// NewRunRecorder returns a recorder with the default redactor.
func NewRunRecorder() *RunRecorder {
	return &RunRecorder{records: map[string]*FullRecord{}, redactor: DefaultRedactor}
}

// Record stores a loop outcome, redacting every string it holds.
//
// Returns the redaction count so a caller can tell a clean run from one that
// carried a credential — a count of zero on a run whose tool read a config file
// is itself information.
func (r *RunRecorder) Record(outcome Outcome, task string) *RunRecord {
	r.mu.Lock()
	defer r.mu.Unlock()

	redactions := 0
	full := &FullRecord{}

	full.Run = RunRecord{
		RunID:       newID("run"),
		Task:        redactCount(r.redactor, task, &redactions),
		RecordedAt:  time.Now(),
		Answer:      redactCount(r.redactor, outcome.Answer, &redactions),
		StopReason:  outcome.StopReason,
		Explanation: redactCount(r.redactor, outcome.Explanation, &redactions),
		Steps:       outcome.Steps,
		ToolCalls:   outcome.ToolCalls,
		Cost:        outcome.Cost,
		// Redactions is deliberately left zero here: the per-turn pass below is
		// what increments the counter, and copying it into this struct before
		// that pass would record the pre-turn count instead of the real one.
	}

	for _, turn := range outcome.Turns {
		tr := TurnRecord{
			Error:      redactCount(r.redactor, turn.Error, &redactions),
			DurationMs: turn.DurationElapsed,
		}
		if turn.Action.Call != nil {
			tr.Tool = turn.Action.Call.Name
			tr.Arguments = turn.Action.Call.Args
		}
		if turn.Action.Reply != "" {
			tr.OutputText = redactCount(r.redactor, turn.Action.Reply, &redactions)
		}
		for _, res := range turn.Results {
			tr.Skipped = tr.Skipped || res.Skipped
			if res.Error != "" {
				tr.Error = redactCount(r.redactor, res.Error, &redactions)
			}
			if res.Output != nil {
				redacted := make(map[string]interface{}, len(res.Output))
				for k, v := range res.Output {
					if s, ok := v.(string); ok {
						redacted[k] = redactCount(r.redactor, s, &redactions)
					} else {
						redacted[k] = v
					}
				}
				tr.Output = redacted
			}
		}
		tr.Redactions = redactions
		full.Turns = append(full.Turns, tr)
	}

	// Assigned after the pass above, so the run-level count covers the turn
	// text as well as the summary fields.
	full.Run.Redactions = redactions

	r.records[full.Run.RunID] = full
	out := full.Run
	return &out
}

// Get returns a stored record.
func (r *RunRecorder) Get(runID string) (*FullRecord, bool) {
	r.mu.Lock()
	defer r.mu.Unlock()
	rec, ok := r.records[runID]
	return rec, ok
}

// List returns every record, newest first.
func (r *RunRecorder) List() []RunRecord {
	r.mu.Lock()
	defer r.mu.Unlock()

	out := make([]RunRecord, 0, len(r.records))
	for _, rec := range r.records {
		out = append(out, rec.Run)
	}
	for i, j := 0, len(out)-1; i < j; i, j = i+1, j-1 {
		out[i], out[j] = out[j], out[i]
	}
	return out
}

// Replay reconstructs an Outcome from a record without calling the model.
//
// That is the point: a recorded run can be inspected and re-fed through the
// loop's own history without spending anything, so a failure can be diagnosed
// from the record alone.
func (r *RunRecorder) Replay(runID string) (Outcome, error) {
	r.mu.Lock()
	defer r.mu.Unlock()

	rec, ok := r.records[runID]
	if !ok {
		return Outcome{}, ErrRunNotFound
	}

	outcome := Outcome{
		Answer:      rec.Run.Answer,
		StopReason:  rec.Run.StopReason,
		Explanation: rec.Run.Explanation,
		Steps:       rec.Run.Steps,
		ToolCalls:   rec.Run.ToolCalls,
		Cost:        rec.Run.Cost,
	}

	for _, tr := range rec.Turns {
		turn := Turn{}
		if tr.Tool != "" {
			turn.Action = StepAction{Call: &Call{Name: tr.Tool, Args: tr.Arguments}}
		}
		if tr.OutputText != "" {
			turn.Action.Reply = tr.OutputText
		}
		turn.DurationElapsed = tr.DurationMs
		if tr.Error != "" {
			turn.Error = tr.Error
		}
		if tr.Output != nil || tr.Skipped || tr.Error != "" {
			turn.Results = append(turn.Results, Result{
				Name:    tr.Tool,
				Output:  tr.Output,
				Skipped: tr.Skipped,
				Error:   tr.Error,
			})
		}
		outcome.Turns = append(outcome.Turns, turn)
	}
	return outcome, nil
}

// ErrRunNotFound is returned for an unknown run id.
var ErrRunNotFound = errors.New("tools: run not found")

// ---------------------------------------------------------------------------
// Audit view
// ---------------------------------------------------------------------------

// AuditEntry is one line of a human-readable audit.
type AuditEntry struct {
	When    time.Time `json:"when"`
	Actor   string    `json:"actor"`
	Action  string    `json:"action"`
	Target  string    `json:"target"`
	Outcome string    `json:"outcome"`
	Detail  string    `json:"detail,omitempty"`
}

// Audit is a combined view of approval decisions and recorded runs.
//
// Combined on purpose: an operator asking "why did this happen" needs the
// decision and the run together, and two logs that cannot be correlated are
// one log split in half.
type Audit struct {
	mu     sync.Mutex
	gate   *ApprovalGate
	record *RunRecorder
}

// NewAudit builds an audit view over a gate and a recorder.
func NewAudit(gate *ApprovalGate, record *RunRecorder) *Audit {
	return &Audit{gate: gate, record: record}
}

// Timeline renders decisions and runs together, newest first.
func (a *Audit) Timeline(limit int) []AuditEntry {
	a.mu.Lock()
	defer a.mu.Unlock()

	var entries []AuditEntry
	for _, d := range a.gate.Decisions("") {
		outcome := "denied"
		if d.Revoked {
			outcome = "revoked"
		} else if d.Granted {
			outcome = "granted"
		}
		entries = append(entries, AuditEntry{
			When:    d.DecidedAt,
			Actor:   d.Approver,
			Action:  "approval",
			Target:  d.Tool,
			Outcome: outcome,
			Detail:  d.Reason,
		})
	}
	for _, rec := range a.record.List() {
		entries = append(entries, AuditEntry{
			When:    rec.RecordedAt,
			Actor:   "loop",
			Action:  "run",
			Target:  rec.RunID,
			Outcome: rec.StopReason,
			Detail:  rec.Explanation,
		})
	}

	for i, j := 0, len(entries)-1; i < j; i, j = i+1, j-1 {
		entries[i], entries[j] = entries[j], entries[i]
	}
	if limit > 0 && len(entries) > limit {
		entries = entries[:limit]
	}
	return entries
}

// Summary renders counts, for a dashboard.
func (a *Audit) Summary() map[string]int {
	a.mu.Lock()
	defer a.mu.Unlock()

	counts := a.gate.Counts()
	counts["runs"] = len(a.record.records)
	return counts
}

// redactCount redacts text and increments a counter.
func redactCount(r *Redactor, text string, count *int) string {
	if text == "" {
		return ""
	}
	out := r.Redact(text)
	if out != text {
		*count++
	}
	return out
}
