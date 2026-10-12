package idempotency

import (
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"strings"
	"sync"
	"sync/atomic"
	"testing"
	"time"
)

func okHandler(calls *int32) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		atomic.AddInt32(calls, 1)
		w.WriteHeader(http.StatusCreated)
		_ = json.NewEncoder(w).Encode(map[string]string{"created": "yes"})
	})
}

func TestPutAndGetRoundTrips(t *testing.T) {
	s := New()
	s.Put("key-1", http.StatusCreated, []byte(`{"ok":true}`))
	got := s.Get("key-1")
	if got == nil {
		t.Fatal("no stored outcome")
	}
	if got.Status != http.StatusCreated {
		t.Fatalf("status = %d, want 201", got.Status)
	}
	if string(got.Body) != `{"ok":true}` {
		t.Fatalf("body = %q", got.Body)
	}
}

func TestMissingKeyReturnsNil(t *testing.T) {
	s := New()
	if got := s.Get("absent"); got != nil {
		t.Fatalf("got = %+v, want nil", got)
	}
	if s.Has("absent") {
		t.Fatal("Has reported true for an absent key")
	}
}

func TestAnExpiredOutcomeIsNotReplayed(t *testing.T) {
	// A retry after the outcome is gone re-executes, which is correct: the
	// caller's intent lapsed. This uses a short TTL by direct construction.
	s := New()
	s.Put("k", 200, []byte("body"))
	s.results["k"] = &Result{Status: 200, Body: []byte("body"), Expiry: time.Now().Add(-time.Second)}
	if s.Has("k") {
		t.Fatal("an expired outcome was still reported as replayable")
	}
	if s.Get("k") != nil {
		t.Fatal("an expired outcome was returned")
	}
}

func TestAKeyIsBounded(t *testing.T) {
	// An unbounded key set would grow memory without limit, which is a
	// memory-exhaustion DoS aimed at the component meant to prevent
	// duplicate work.
	s := New()
	for i := 0; i < maxKeys+200; i++ {
		s.Put(keyFor(i), 200, []byte("b"))
	}
	s.mu.Lock()
	n := len(s.results)
	s.mu.Unlock()
	if n > maxKeys {
		t.Fatalf("%d keys stored with a bound of %d", n, maxKeys)
	}
}

func TestNormalizeBoundsAndCleans(t *testing.T) {
	for _, raw := range []string{
		"key\ninjected",
		"key\tinjected",
		strings.Repeat("a", 1000),
	} {
		got := normalize(raw)
		if len(got) > 256 {
			t.Fatalf("key length = %d, want at most 256", len(got))
		}
		for _, r := range got {
			if r < 0x20 {
				t.Fatalf("a control character survived: %q", got)
			}
		}
	}
}

func TestAnEmptyKeyIsIgnored(t *testing.T) {
	s := New()
	s.Put("", 200, []byte("b"))
	if s.Get("") != nil {
		t.Fatal("an empty key was stored")
	}
	release, owner := s.Begin("")
	if !owner {
		t.Fatal("an empty key was serialised")
	}
	release()
}

func TestBeginSerialisesTheSameKey(t *testing.T) {
	// Two simultaneous requests with the same key must not both execute:
	// that is the duplicate-charge failure.
	s := New()
	var calls int32
	h := okHandler(&calls)
	handler := s.Middleware(h, "k")

	var wg sync.WaitGroup
	var mu sync.Mutex
	executed := 0
	for i := 0; i < 10; i++ {
		wg.Add(1)
		go func() {
			defer wg.Done()
			handler.ServeHTTP(httptest.NewRecorder(), httptest.NewRequest("POST", "/pay", nil))
			mu.Lock()
			executed++
			mu.Unlock()
		}()
	}
	wg.Wait()
	if n := atomic.LoadInt32(&calls); n != 1 {
		t.Fatalf("%d executions for 10 concurrent requests with one key", n)
	}
}

func TestDifferentKeysEachExecute(t *testing.T) {
	s := New()
	var calls int32
	h := okHandler(&calls)
	s.Middleware(h, "k1").ServeHTTP(httptest.NewRecorder(), httptest.NewRequest("POST", "/pay", nil))
	s.Middleware(h, "k2").ServeHTTP(httptest.NewRecorder(), httptest.NewRequest("POST", "/pay", nil))
	if n := atomic.LoadInt32(&calls); n != 2 {
		t.Fatalf("%d executions, want 2 for two distinct keys", n)
	}
}

func TestReplayReturnsTheStoredBody(t *testing.T) {
	s := New()
	var calls int32
	h := okHandler(&calls)
	mw := s.Middleware(h, "replay-key")

	rec1 := httptest.NewRecorder()
	mw.ServeHTTP(rec1, httptest.NewRequest("POST", "/pay", nil))
	rec2 := httptest.NewRecorder()
	mw.ServeHTTP(rec2, httptest.NewRequest("POST", "/pay", nil))

	if rec2.Code != http.StatusCreated {
		t.Fatalf("replay status = %d, want 201", rec2.Code)
	}
	if rec2.Body.String() != rec1.Body.String() {
		t.Fatalf("replay body = %q, want %q", rec2.Body.String(), rec1.Body.String())
	}
	if n := atomic.LoadInt32(&calls); n != 1 {
		t.Fatalf("%d executions, want 1 for a replayed key", n)
	}
}

func TestFingerprintIsStableAndDistinguishing(t *testing.T) {
	a := Fingerprint("POST", "/pay", []byte(`{"a":1}`))
	b := Fingerprint("POST", "/pay", []byte(`{"a":1}`))
	if a != b {
		t.Fatal("the fingerprint is not stable for an identical request")
	}
	c := Fingerprint("POST", "/pay", []byte(`{"a":2}`))
	if a == c {
		t.Fatal("different bodies produced the same fingerprint")
	}
	d := Fingerprint("POST", "/other", []byte(`{"a":1}`))
	if a == d {
		t.Fatal("different paths produced the same fingerprint")
	}
}

func TestFingerprintDoesNotStoreTheBody(t *testing.T) {
	// The fingerprint is a hash, so a store keyed by it does not hold the
	// request body, which may contain a credential.
	fp := Fingerprint("POST", "/pay", []byte(`{"password":"hunter2"}`))
	if contains(fp, "hunter2") {
		t.Fatal("the fingerprint contains the body")
	}
}

// helpers ---------------------------------------------------------------

func keyFor(i int) string {
	if i == 0 {
		return "k0"
	}
	var b [12]byte
	n := i
	for j := len(b) - 1; j >= 0; j-- {
		b[j] = byte('0' + n%10)
		n /= 10
	}
	return "k" + string(b[:])
}

func contains(hay, needle string) bool {
	if len(needle) > len(hay) {
		return false
	}
	for i := 0; i+len(needle) <= len(hay); i++ {
		if hay[i:i+len(needle)] == needle {
			return true
		}
	}
	return false
}
