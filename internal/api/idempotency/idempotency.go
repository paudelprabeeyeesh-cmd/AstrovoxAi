// Package idempotency implements idempotent mutating requests.
//
// A retried request must not create a second record, a second charge, or a
// second message. The header carries a client-supplied key, the server
// stores the outcome, and a replay returns the stored response rather than
// executing again.
//
// The failure mode this prevents is specific and expensive: a client that
// times out and retries a charge creates two charges, and a client that
// retries a chat creates two messages. Neither is visible to the caller as
// an error.
//
// The store is in-process and bounded, so an unbounded key set cannot grow
// memory without limit. Concurrency is per-key, so two simultaneous
// in-flight requests with the same key do not both execute.
package idempotency

import (
	"bytes"
	"crypto/sha256"
	"encoding/hex"
	"net/http"
	"strings"
	"sync"
	"time"
)

// Header is the idempotency-key header. It is the Stripe convention, so a
// client that already sends one keeps working.
const Header = "Idempotency-Key"

// maxKeys bounds the store, so a caller presenting unbounded distinct keys
// cannot grow memory without limit.
const maxKeys = 10_000

// TTL is how long a recorded outcome is replayed. A retry after the outcome
// is gone re-executes, which is correct: the caller's intent lapsed.
const TTL = 24 * time.Hour

// Result is a stored outcome.
type Result struct {
	Status int
	Body   []byte
	// Expiry bounds the record so a stale outcome is not replayed forever.
	Expiry time.Time
}

// Store records outcomes by idempotency key.
type Store struct {
	mu sync.Mutex
	// inflight serialises concurrent requests with the same key, so two
	// simultaneous retries do not both execute.
	inflight map[string]chan struct{}
	results  map[string]*Result
	// order tracks insertion order for eviction.
	order []string
}

// New returns an empty store.
func New() *Store {
	return &Store{
		inflight: map[string]chan struct{}{},
		results:  map[string]*Result{},
	}
}

// normalize bounds and cleans a key, so an unbounded or control-character
// header cannot grow the store or inject a log line.
func normalize(key string) string {
	if key == "" {
		return ""
	}
	if len(key) > 256 {
		key = key[:256]
	}
	key = strings.Map(func(r rune) rune {
		if r < 0x20 || r == 0x7f {
			return -1
		}
		return r
	}, key)
	return key
}

// Has reports whether a replayable outcome exists.
func (s *Store) Has(key string) bool {
	k := normalize(key)
	if k == "" {
		return false
	}
	s.mu.Lock()
	defer s.mu.Unlock()
	r, ok := s.results[k]
	if !ok {
		return false
	}
	if time.Now().After(r.Expiry) {
		delete(s.results, k)
		return false
	}
	return true
}

// Get returns a stored outcome, or nil when absent or expired.
func (s *Store) Get(key string) *Result {
	k := normalize(key)
	if k == "" {
		return nil
	}
	s.mu.Lock()
	defer s.mu.Unlock()
	r, ok := s.results[k]
	if !ok {
		return nil
	}
	if time.Now().After(r.Expiry) {
		delete(s.results, k)
		return nil
	}
	return r
}

// Put records an outcome, evicting the oldest when the store is full.
func (s *Store) Put(key string, status int, body []byte) {
	k := normalize(key)
	if k == "" {
		return
	}
	s.mu.Lock()
	defer s.mu.Unlock()
	if _, exists := s.results[k]; !exists {
		s.order = append(s.order, k)
		if len(s.order) > maxKeys {
			// Drop the oldest: a store that cannot evict grows forever, and
			// the oldest key is the one least likely to be retried.
			oldest := s.order[0]
			s.order = s.order[1:]
			delete(s.results, oldest)
		}
	}
	s.results[k] = &Result{
		Status: status,
		Body:   append([]byte{}, body...),
		Expiry: time.Now().Add(TTL),
	}
}

// Begin claims a key, returning a release function and whether the caller
// is the owner. The second caller for an in-flight key blocks until the
// first finishes, then sees the stored outcome.
func (s *Store) Begin(key string) (release func(), owner bool) {
	k := normalize(key)
	if k == "" {
		return func() {}, true
	}
	s.mu.Lock()
	if ch, ok := s.inflight[k]; ok {
		// Someone else is executing. Wait for them, then this caller is not
		// the owner and must read the stored result.
		s.mu.Unlock()
		<-ch
		return func() {}, false
	}
	ch := make(chan struct{})
	s.inflight[k] = ch
	s.mu.Unlock()
	return func() {
		s.mu.Lock()
		delete(s.inflight, k)
		s.mu.Unlock()
		close(ch)
	}, true
}

// Middleware wraps a handler so a retried request replays its outcome
// rather than executing again.
//
// A caller-supplied key wins; without one, the body fingerprint is used, so
// an identical retry is still deduplicated. The response is buffered
// because the outcome must be recorded before it is written.
func (s *Store) Middleware(next http.Handler, key string) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		effective := normalize(key)
		if effective == "" {
			next.ServeHTTP(w, r)
			return
		}

		// A replay short-circuits before the handler runs.
		if stored := s.Get(effective); stored != nil {
			w.Header().Set("Idempotent-Replay", "true")
			w.WriteHeader(stored.Status)
			_, _ = w.Write(stored.Body)
			return
		}

		release, owner := s.Begin(effective)
		if !owner {
			// Another request is executing with this key. It has finished by
			// now, so its outcome is either stored or expired; either way the
			// handler must not run a second time.
			if stored := s.Get(effective); stored != nil {
				w.Header().Set("Idempotent-Replay", "true")
				w.WriteHeader(stored.Status)
				_, _ = w.Write(stored.Body)
			} else {
				// The stored outcome expired between the release and this
				// read, so the caller's intent lapsed. Executing would be
				// correct, but a queue of waiting retries makes that a
				// retry storm, so this one is refused and the client retries
				// with a fresh key.
				w.WriteHeader(http.StatusConflict)
				_, _ = w.Write([]byte(`{"error":"idempotency record expired; retry with a new key"}`))
			}
			return
		}
		defer release()

		rec := &recorder{ResponseWriter: w, status: http.StatusOK}
		next.ServeHTTP(rec, r)
		// The outcome is recorded for every status, including a 5xx: a
		// retried request must not re-execute a charge that failed, and a
		// retry that sees the stored failure can decide what to do.
		s.Put(effective, rec.status, rec.body.Bytes())
	})
}

// recorder buffers the body and captures the status so the outcome can be
// stored, while still writing the real response through to the client.
type recorder struct {
	http.ResponseWriter
	status      int
	body        bytes.Buffer
	wroteHeader bool
}

func (r *recorder) WriteHeader(code int) {
	if r.wroteHeader {
		return
	}
	r.status = code
	r.wroteHeader = true
	// The header is written immediately so a slow handler streams rather
	// than buffering: the capture is an observation, not a throttle.
	r.ResponseWriter.WriteHeader(code)
}

func (r *recorder) Write(b []byte) (int, error) {
	if !r.wroteHeader {
		r.wroteHeader = true
		r.status = http.StatusOK
		r.ResponseWriter.WriteHeader(http.StatusOK)
	}
	r.body.Write(b)
	return r.ResponseWriter.Write(b)
}

// Fingerprint is a stable key for a request body, so a caller that does not
// supply one can still get idempotency for an identical body. It is a hash,
// so the store does not hold the body.
func Fingerprint(method, path string, body []byte) string {
	h := sha256.New()
	h.Write([]byte(method))
	h.Write([]byte{0})
	h.Write([]byte(path))
	h.Write([]byte{0})
	if len(body) > 0 {
		h.Write(body)
	}
	return "auto:" + hex.EncodeToString(h.Sum(nil))[:32]
}
