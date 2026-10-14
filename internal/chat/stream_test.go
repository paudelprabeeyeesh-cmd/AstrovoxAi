package chat

import (
	"context"
	"errors"
	"sync"
	"testing"
	"time"
)

// chunkingProvider emits a fixed script, so the session can be tested without a
// provider.
type chunkingProvider struct {
	chunks []Chunk
	// failAfter emits this many chunks and then sends Chunk.Err.
	failAfter int
	// noDone omits the done chunk, which is the truncated-stream case.
	noDone bool
	// slow makes the provider pause between chunks.
	slow time.Duration
	// sawCancel records that the provider's context was cancelled.
	sawCancel *boolFlag
}

type boolFlag struct {
	mu sync.Mutex
	v  bool
}

func (b *boolFlag) Store(v bool) {
	b.mu.Lock()
	b.v = v
	b.mu.Unlock()
}

func (b *boolFlag) Load() bool {
	b.mu.Lock()
	defer b.mu.Unlock()
	return b.v
}

func (p *chunkingProvider) Name() string { return "chunking" }

func (p *chunkingProvider) Complete(ctx context.Context, req *Request) (Stream, error) {
	out := make(chan Chunk, len(p.chunks)+2)
	go func() {
		defer close(out)
		for i, c := range p.chunks {
			if p.slow > 0 {
				select {
				case <-ctx.Done():
					return
				case <-time.After(p.slow):
				}
			} else {
				select {
				case <-ctx.Done():
					return
				default:
				}
			}
			if p.sawCancel != nil && ctx.Err() != nil {
				p.sawCancel.Store(true)
			}
			out <- c
			if p.failAfter > 0 && i+1 == p.failAfter {
				out <- Chunk{Err: errors.New("provider broke mid-stream")}
				return
			}
		}
		if p.noDone {
			return
		}
		out <- Chunk{Done: true, Usage: Usage{InputTokens: 5, OutputTokens: 5}}
	}()
	return out, nil
}

func scriptedProvider() *chunkingProvider {
	return &chunkingProvider{chunks: []Chunk{
		{Delta: "Hello"},
		{Delta: ", "},
		{Delta: "world"},
	}}
}

func drainStream(s *StreamSession) []Chunk {
	var out []Chunk
	for chunk := range s.Subscribe() {
		out = append(out, chunk)
	}
	return out
}

func TestSessionNumberingStartsAtOne(t *testing.T) {
	// Sequence numbers must start at 1 and never repeat. A zero-based numbering
	// makes "the first chunk" indistinguishable from "nothing yet", which is
	// exactly the ambiguity a resuming client has to resolve.
	s := NewStreamSession("s1")
	s.Emit(Chunk{Delta: "a"})
	s.Emit(Chunk{Delta: "b"})
	s.Emit(Chunk{Done: true})

	if got := s.LastSequence(); got != 3 {
		t.Fatalf("LastSequence = %d, want 3", got)
	}
	for i, seq := range []int{1, 2, 3} {
		if got := s.buf[i].Seq; got != seq {
			t.Fatalf("chunk %d has Seq %d, want %d", i, got, seq)
		}
	}
}

func TestReplayReturnsOnlyWhatWasMissed(t *testing.T) {
	s := NewStreamSession("s1")
	s.Emit(Chunk{Delta: "a"})
	s.Emit(Chunk{Delta: "b"})
	s.Emit(Chunk{Delta: "c"})

	replay := s.Replay(1)
	if len(replay) != 2 {
		t.Fatalf("Replay(1) returned %d chunks, want 2", len(replay))
	}
	if replay[0].Seq != 2 || replay[1].Seq != 3 {
		t.Fatalf("Replay(1) returned sequences %d,%d", replay[0].Seq, replay[1].Seq)
	}
}

func TestReplayFromZeroReturnsEverything(t *testing.T) {
	s := NewStreamSession("s1")
	s.Emit(Chunk{Delta: "a"})
	s.Emit(Chunk{Delta: "b"})

	if got := s.Replay(0); len(got) != 2 {
		t.Fatalf("Replay(0) returned %d, want everything", len(got))
	}
}

func TestReplayPastTheEndReturnsNothing(t *testing.T) {
	s := NewStreamSession("s1")
	s.Emit(Chunk{Delta: "a"})
	if got := s.Replay(99); len(got) != 0 {
		t.Fatalf("Replay(99) returned %d chunks", len(got))
	}
}

func TestASubscriberJoiningLateStillSeesTheStart(t *testing.T) {
	// The bug this prevents: the subscriber registers after the emit loop has
	// finished, so it sees an empty stream and reports success with no text.
	s := NewStreamSession("s1")
	s.Emit(Chunk{Delta: "a"})
	s.Emit(Chunk{Delta: "b"})
	s.Emit(Chunk{Done: true})
	s.Close()

	chunks := drainStream(s)
	joined := ""
	for _, c := range chunks {
		joined += c.Delta
	}
	if joined != "ab" {
		t.Fatalf("a late subscriber saw %q, want the whole stream", joined)
	}
}

func TestALiveSubscriberIsNotClosedEarly(t *testing.T) {
	// A subscriber that joins before the stream starts must have its channel
	// stay open until the stream ends. Closing it early makes a live reader
	// see a clean end to a stream that never finished - the failure mode looks
	// exactly like success, so it needs its own test.
	s := NewStreamSession("live")
	feed := s.Subscribe()

	// Give the catch-up goroutine a chance to (incorrectly) return early.
	time.Sleep(50 * time.Millisecond)

	select {
	case _, open := <-feed:
		if !open {
			t.Fatal("the channel closed before anything was emitted")
		}
	default:
		// Empty but open: the correct state.
	}
}

func TestALiveSubscriberSeesEverythingThenACleanClose(t *testing.T) {
	s := NewStreamSession("live-2")
	feed := s.Subscribe()
	time.Sleep(20 * time.Millisecond)

	s.Emit(Chunk{Delta: "a"})
	s.Emit(Chunk{Delta: "b"})
	s.Emit(Chunk{Done: true})
	s.Close()

	var text string
	open := true
	for open {
		chunk, ok := <-feed
		if !ok {
			break
		}
		text += chunk.Delta
	}
	if text != "ab" {
		t.Fatalf("a live subscriber received %q", text)
	}
}

func TestASubscriberSeesTheWholeStreamWhenLive(t *testing.T) {
	s := NewStreamSession("s1")
	received := make(chan string, 16)

	feed := s.Subscribe()
	go func() {
		var joined string
		for chunk := range feed {
			if chunk.Err != nil {
				continue
			}
			joined += chunk.Delta
		}
		received <- joined
	}()

	s.Emit(Chunk{Delta: "Hello"})
	s.Emit(Chunk{Delta: ", "})
	s.Emit(Chunk{Delta: "world"})
	s.Emit(Chunk{Done: true})
	s.Close()

	select {
	case got := <-received:
		if got != "Hello, world" {
			t.Fatalf("received %q", got)
		}
	case <-time.After(2 * time.Second):
		t.Fatal("the subscriber never finished")
	}
}

func TestAMidStreamFailureIsNotPresentedAsSuccess(t *testing.T) {
	// The partial text must not be emitted as a complete answer. The reader has
	// to see an error, because a truncated answer shown as finished is worse
	// than no answer.
	s := NewStreamSession("s1")
	s.Emit(Chunk{Delta: "partial"})
	s.Fail(errors.New("provider broke"))
	s.Close()

	chunks := drainStream(s)
	if len(chunks) == 0 {
		t.Fatal("no chunks were delivered")
	}
	last := chunks[len(chunks)-1]
	if last.Err == nil {
		t.Fatal("the stream ended without reporting the failure")
	}
	sawPartial := false
	for _, c := range chunks {
		if c.Delta == "partial" {
			sawPartial = true
		}
	}
	if !sawPartial {
		t.Fatal("the partial text was dropped instead of delivered before the error")
	}
}

func TestAFailureIsReplayedToALateSubscriber(t *testing.T) {
	s := NewStreamSession("s1")
	s.Emit(Chunk{Delta: "partial"})
	s.Fail(errors.New("broke"))
	s.Close()

	chunks := drainStream(s)
	if chunks[len(chunks)-1].Err == nil {
		t.Fatal("a late subscriber did not see the failure")
	}
}

func TestFailureIsRecordedOnlyOnce(t *testing.T) {
	s := NewStreamSession("s1")
	first := errors.New("first")
	second := errors.New("second")
	s.Fail(first)
	s.Fail(second)
	if got := s.Error(); got != first {
		t.Fatalf("Error = %v, want the first failure", got)
	}
}

func TestCloseIsIdempotent(t *testing.T) {
	// Close is called from several paths; a double close panics on a closed
	// channel, which would crash a request handler.
	s := NewStreamSession("s1")
	s.Emit(Chunk{Done: true})
	s.Close()
	s.Close()
	if !s.Finished() {
		t.Fatal("the session did not record that it finished")
	}
}

func TestRunStreamedEmitsTheWholeScript(t *testing.T) {
	orchestrator, _ := New(&chunkingProvider{chunks: []Chunk{
		{Delta: "Hello"}, {Delta: ", "}, {Delta: "world"},
	}}, NoSpend{})

	session := NewStreamSession("run-1")
	err := orchestrator.RunStreamed(
		context.Background(), "u1", "t1",
		&Request{Messages: []Message{{Role: "user", Content: "hi"}}}, session,
	)
	if err != nil {
		t.Fatalf("RunStreamed failed: %v", err)
	}

	chunks := drainStream(session)
	var text string
	var doneSeen int
	for _, c := range chunks {
		text += c.Delta
		if c.Done {
			doneSeen++
		}
	}
	if text != "Hello, world" {
		t.Fatalf("streamed %q", text)
	}
	if doneSeen != 1 {
		t.Fatalf("saw %d done chunks, want exactly 1", doneSeen)
	}
}

func TestRunStreamedFailsOnAMidStreamError(t *testing.T) {
	orchestrator, _ := New(&chunkingProvider{
		chunks:    []Chunk{{Delta: "a"}, {Delta: "b"}, {Delta: "c"}},
		failAfter: 2,
	}, NoSpend{})

	session := NewStreamSession("run-2")
	err := orchestrator.RunStreamed(
		context.Background(), "u1", "t1",
		&Request{Messages: []Message{{Role: "user", Content: "hi"}}}, session,
	)
	if err == nil {
		t.Fatal("a mid-stream provider failure returned success")
	}
	if session.Error() == nil {
		t.Fatal("the session recorded no failure")
	}
}

func TestRunStreamedRejectsATruncatedStream(t *testing.T) {
	// A provider that ends without a done chunk has not succeeded. Reporting
	// success here would hand out a truncated answer as complete.
	orchestrator, _ := New(&chunkingProvider{
		chunks: []Chunk{{Delta: "a"}, {Delta: "b"}},
		noDone: true,
	}, NoSpend{})

	session := NewStreamSession("run-3")
	err := orchestrator.RunStreamed(
		context.Background(), "u1", "t1",
		&Request{Messages: []Message{{Role: "user", Content: "hi"}}}, session,
	)
	if err == nil {
		t.Fatal("a stream with no done chunk was treated as success")
	}
}

func TestRunStreamedStopsOnCancellation(t *testing.T) {
	// Cancellation must stop the provider rather than let it finish metering
	// tokens for an answer nobody will read.
	sawCancel := &boolFlag{}
	ctx, cancel := context.WithCancel(context.Background())
	orchestrator, _ := New(&chunkingProvider{
		chunks:    []Chunk{{Delta: "a"}, {Delta: "b"}, {Delta: "c"}},
		slow:      50 * time.Millisecond,
		sawCancel: sawCancel,
	}, NoSpend{})

	session := NewStreamSession("run-4")
	done := make(chan error, 1)
	go func() {
		done <- orchestrator.RunStreamed(ctx, "u1", "t1",
			&Request{Messages: []Message{{Role: "user", Content: "hi"}}}, session)
	}()

	time.Sleep(60 * time.Millisecond)
	cancel()

	select {
	case err := <-done:
		if err == nil {
			t.Fatal("cancellation returned success")
		}
	case <-time.After(2 * time.Second):
		t.Fatal("cancellation did not stop the run")
	}
	if !session.Finished() {
		t.Fatal("the session was left open after cancellation")
	}
}

func TestASubscriberSurvivesAnotherDroppingOut(t *testing.T) {
	// One slow reader must not stall the stream for a reading one. The slow
	// reader is dropped and can resume from its last acknowledged sequence.
	s := NewStreamSession("s1")

	slow := make(chan Chunk, 1)
	fast := make(chan Chunk, 64)
	s.mu.Lock()
	s.subscribers[slow] = &subscriber{ch: slow, afterSeq: 0}
	s.subscribers[fast] = &subscriber{ch: fast, afterSeq: 0}
	s.mu.Unlock()

	// Fill the slow reader's buffer, then keep going: the emit must not block.
	for i := 0; i < 200; i++ {
		done := make(chan struct{})
		go func() {
			s.Emit(Chunk{Delta: "x"})
			close(done)
		}()
		select {
		case <-done:
		case <-time.After(time.Second):
			t.Fatal("Emit blocked on a subscriber that stopped reading")
		}
	}

	if got := s.LastSequence(); got != 200 {
		t.Fatalf("LastSequence = %d, want 200", got)
	}
}

func TestConcurrentEmitNumbersWithoutGaps(t *testing.T) {
	// Emit is the only way in, so concurrent callers still produce a contiguous
	// sequence. A duplicated number is unresolvable for a resuming client.
	s := NewStreamSession("s1")
	var wg sync.WaitGroup
	for i := 0; i < 100; i++ {
		wg.Add(1)
		go func() {
			defer wg.Done()
			s.Emit(Chunk{Delta: "x"})
		}()
	}
	wg.Wait()

	seen := map[int]bool{}
	for _, c := range s.Replay(0) {
		if seen[c.Seq] {
			t.Fatalf("duplicate sequence number %d", c.Seq)
		}
		seen[c.Seq] = true
	}
	if len(seen) != 100 {
		t.Fatalf("got %d distinct sequence numbers, want 100", len(seen))
	}
}
