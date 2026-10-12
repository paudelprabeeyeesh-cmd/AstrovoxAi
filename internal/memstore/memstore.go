// Package memstore implements the explicit memory store and its safety
// policy in Go (D08-03, D08-05).
//
// Two independent filters, both fail closed:
//
//  1. A deny list of sensitive categories. A candidate whose text matches a
//     category is refused before it can be stored.
//  2. An instruction-override filter. A stored memory is trusted context for
//     every future session, so a memory that reads as an instruction to the
//     model — rather than a fact about the user — is the persistent half of
//     prompt injection. One success is permanent.
//
// The port keeps the same categories and patterns as the Python policy that
// preceded it, so behaviour does not change with the language.
package memstore

import (
	"regexp"
	"sync"
	"time"
)

// Categories are the sensitive classes a memory may not belong to.
const (
	CategoryCredentials         = "credentials"
	CategoryGovernmentID        = "government_id"
	CategoryFinancial           = "financial"
	CategoryHealth              = "health"
	CategoryLocation            = "location"
	CategoryAuthentication      = "authentication"
	CategoryInstructionOverride = "instruction_override"
)

// Decision is the result of screening a candidate.
type Decision struct {
	Allowed  bool
	Category string
	Reason   string
}

// Entry is one stored memory.
type Entry struct {
	ID        string    `json:"id"`
	Owner     string    `json:"owner"`
	Text      string    `json:"text"`
	CreatedAt time.Time `json:"created_at"`
}

// categoryPatterns maps a category to the patterns that identify it. Patterns
// are case-insensitive.
var categoryPatterns = map[string][]*regexp.Regexp{
	CategoryCredentials: {
		regexp.MustCompile(`(?i)\bpassword\b`),
		regexp.MustCompile(`(?i)\bpasswd\b`),
		regexp.MustCompile(`(?i)\bapi[ _-]?key\b`),
		regexp.MustCompile(`(?i)\bsecret[ _-]?key\b`),
		regexp.MustCompile(`(?i)\baccess[ _-]?token\b`),
		regexp.MustCompile(`(?i)\bbearer\s+[A-Za-z0-9._-]{8,}`),
		regexp.MustCompile(`(?i)\bsk-[A-Za-z0-9]{16,}`),
	},
	CategoryGovernmentID: {
		regexp.MustCompile(`(?i)\bssn\b`),
		regexp.MustCompile(`(?i)\bsocial\s+security\b`),
		regexp.MustCompile(`(?i)\bpassport\s+(number|no\b)`),
		regexp.MustCompile(`(?i)\bdriver'?s?\s+licen[cs]e\s+(number|no\b)`),
		regexp.MustCompile(`(?i)\bnational\s+id\b`),
	},
	CategoryFinancial: {
		regexp.MustCompile(`(?i)\bcredit\s+card\s+(number|no\b)`),
		regexp.MustCompile(`\b\d{13,19}\b`),
		regexp.MustCompile(`(?i)\biban\b`),
		regexp.MustCompile(`(?i)\bbank\s+account\s+(number|no\b)`),
		regexp.MustCompile(`(?i)\bcvv\b`),
	},
	CategoryHealth: {
		regexp.MustCompile(`(?i)\bdiagnos(e|ed|is|is\s+with)\b`),
		regexp.MustCompile(`(?i)\bdiagnos(e|ed|is)\s+(with|of)\b`),
		regexp.MustCompile(`(?i)\bprescription\s+for\b`),
		regexp.MustCompile(`(?i)\bmedical\s+record\b`),
	},
	CategoryLocation: {
		regexp.MustCompile(`(?i)\bhome\s+address\b`),
		regexp.MustCompile(`(?i)\bmy\s+exact\s+location\b`),
	},
	CategoryAuthentication: {
		regexp.MustCompile(`(?i)\btotp\s+secret\b`),
		regexp.MustCompile(`(?i)\b2fa\s+seed\b`),
		regexp.MustCompile(`(?i)\brecovery\s+codes?\b`),
		regexp.MustCompile(`(?i)\bprivate\s+key\b`),
	},
	CategoryInstructionOverride: {
		regexp.MustCompile(`(?i)^\s*(ignore|disregard|forget)\s+(all\s+|the\s+|any\s+|your\s+)?(previous|prior|above|earlier)\s+(instructions?|prompts?|rules?|directives?)`),
		regexp.MustCompile(`(?i)^\s*(you\s+are\s+now|you\s+are)\s+(a\s+)?(dan|unfiltered|unrestricted|jailbroken)`),
		regexp.MustCompile(`(?i)^\s*(reveal|print|repeat|output|show)\s+(me\s+)?(the\s+)?(your\s+)?(system\s+)?(prompt|instructions?)`),
		regexp.MustCompile(`(?i)\bignore\s+(all\s+|the\s+|any\s+|your\s+)?(previous|prior|above|earlier)\s+(instructions?|prompts?|rules?)`),
	},
}

// MaxTextLen bounds a candidate's length. A longer candidate is refused
// rather than truncated, so the stored text is exactly what was screened.
const MaxTextLen = 20_000

// Store is an in-process, owner-scoped memory store with the policy
// enforced on write.
type Store struct {
	mu      sync.RWMutex
	limit   int
	entries map[string][]Entry
	nextID  int
	// rejected counts the refusals per category, exposed by RejectedStats.
	rejected map[string]int
}

// New returns a store bounded to limit entries per owner. A non-positive
// limit becomes 10_000 rather than a store that cannot hold anything.
func New(limit int) *Store {
	if limit <= 0 {
		limit = 10_000
	}
	return &Store{
		limit:    limit,
		entries:  map[string][]Entry{},
		rejected: map[string]int{},
	}
}

// Evaluate screens a candidate. It is exported so the same rules can be
// applied to text that is not destined for this store.
func Evaluate(text string) Decision {
	if len(text) == 0 {
		return Decision{Allowed: false, Category: "invalid", Reason: "empty candidate"}
	}
	if len(text) > MaxTextLen {
		return Decision{Allowed: false, Category: "invalid", Reason: "candidate too long"}
	}
	for category, patterns := range categoryPatterns {
		for _, re := range patterns {
			if re.MatchString(text) {
				return Decision{
					Allowed:  false,
					Category: category,
					Reason:   "matched sensitive category: " + category,
				}
			}
		}
	}
	return Decision{Allowed: true, Category: "allowed", Reason: "ok"}
}

// Add stores a screened memory. A refused candidate is counted and an error
// is returned; nothing is stored.
func (s *Store) Add(owner, text string) (*Entry, error) {
	d := Evaluate(text)
	if !d.Allowed {
		s.mu.Lock()
		s.rejected[d.Category]++
		s.mu.Unlock()
		return nil, &PolicyError{Category: d.Category, Reason: d.Reason}
	}
	s.mu.Lock()
	defer s.mu.Unlock()
	s.nextID++
	entry := Entry{
		ID:        ShortID(),
		Owner:     owner,
		Text:      text,
		CreatedAt: time.Now().UTC(),
	}
	// Bound the store per owner, evicting the oldest entry, so an unbounded
	// conversation cannot grow memory without limit.
	items := append(s.entries[owner], entry)
	if len(items) > s.limit {
		items = items[len(items)-s.limit:]
	}
	s.entries[owner] = items
	return &entry, nil
}

// List returns a copy of the caller's entries, so a caller mutating the
// result cannot corrupt the store.
func (s *Store) List(owner string) []Entry {
	s.mu.RLock()
	defer s.mu.RUnlock()
	src := s.entries[owner]
	out := make([]Entry, len(src))
	copy(out, src)
	return out
}

// Delete removes one entry by id, scoped to the owner. A cross-owner delete
// is a not-found rather than a silent success.
func (s *Store) Delete(owner, id string) bool {
	s.mu.Lock()
	defer s.mu.Unlock()
	items := s.entries[owner]
	for i, e := range items {
		if e.ID == id {
			s.entries[owner] = append(items[:i], items[i+1:]...)
			return true
		}
	}
	return false
}

// Len returns the total number of stored entries.
func (s *Store) Len() int {
	s.mu.RLock()
	defer s.mu.RUnlock()
	total := 0
	for _, v := range s.entries {
		total += len(v)
	}
	return total
}

// RejectedStats returns the refusal counts per category, so an operator can
// see what the policy is actually catching.
func (s *Store) RejectedStats() map[string]int {
	s.mu.RLock()
	defer s.mu.RUnlock()
	out := make(map[string]int, len(s.rejected))
	for k, v := range s.rejected {
		out[k] = v
	}
	return out
}

// Clear removes all of an owner's entries.
func (s *Store) Clear(owner string) {
	s.mu.Lock()
	defer s.mu.Unlock()
	delete(s.entries, owner)
}

// PolicyError reports a refused candidate. Its category is stable, so a
// caller can branch on it.
type PolicyError struct {
	Category string
	Reason   string
}

func (e *PolicyError) Error() string { return "memory rejected: " + e.Reason }

// shortID is a compact unique id. It is not a security token: it identifies
// a row, it does not authenticate one.
var idSeq uint64
var idMu sync.Mutex

func ShortID() string {
	idMu.Lock()
	idSeq++
	n := idSeq
	idMu.Unlock()
	const alphabet = "0123456789abcdefghijklmnopqrstuvwxyz"
	b := make([]byte, 10)
	for i := range b {
		b[i] = alphabet[n%uint64(len(alphabet))]
		n /= uint64(len(alphabet))
	}
	return string(b)
}
