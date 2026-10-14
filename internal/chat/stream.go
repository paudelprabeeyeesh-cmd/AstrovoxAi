package chat

import (
	"context"
	"strings"
	"sync"
)

// ---------------------------------------------------------------------------
// Resumable streaming
// ---------------------------------------------------------------------------

// A stream that can only be consumed once is unusable over a network: a client
// whose connection drops has already lost the tokens it paid for, and the only
// options are to restart the completion or to show a truncated answer as if it
// were complete. Neither is acceptable, so a session keeps what it has emitted
// and hands it back.
//
// The sequence number is what makes this possible. Without it, a client that
// reconnects can say "I missed something" but not what, and the server cannot
// tell whether the client already saw a chunk or is asking for a repeat.
//
// This is not a general message bus. It exists for one stream per request, held
// exactly as long as the request, and discarded afterwards.

// subscriber is a registered reader and the sequence it has already seen.
//
// The afterSeq marker is what keeps a late joiner correct: registration and the
// snapshot of what it missed happen under the same lock, so no chunk can be
// delivered twice or skipped between "decide what to replay" and "join the
// fan-out". Splitting those two steps is the race, and it is the whole reason
// this is a struct rather than a bare channel.
type subscriber struct {
	ch       chan Chunk
	afterSeq int
}

// StreamSession carries one completion's chunks with the bookkeeping a client
// needs to resume.
type StreamSession struct {
	id string
	// buf holds every chunk in sequence order, for replay.
	mu   sync.Mutex
	buf  []Chunk
	done bool
	// err is the terminal failure, replayed after the buffered chunks so a
	// reconnecting client sees the same ending a live client would have.
	err error

	// subscribers are the live readers. Each gets every chunk as it arrives.
	subscribers map[chan Chunk]*subscriber
	// closed stops the fan-out goroutine.
	closed chan struct{}
	once   sync.Once
}

// NewStreamSession returns a session that is ready to emit.
func NewStreamSession(id string) *StreamSession {
	return &StreamSession{
		id:          id,
		subscribers: map[chan Chunk]*subscriber{},
		closed:      make(chan struct{}),
	}
}

// ID returns the session identifier a client reconnects with.
func (s *StreamSession) ID() string { return s.id }

// Subscribe returns a channel of chunks from now on.
//
// A subscriber that joins after chunks were emitted is caught up first: the
// snapshot and the registration share one lock acquisition, so the join cannot
// race the emissions and no chunk is delivered twice or dropped. The channel is
// closed when the stream ends, and a final Chunk carrying Err is sent first if
// the stream failed.
func (s *StreamSession) Subscribe() <-chan Chunk {
	out := make(chan Chunk, 64)

	s.mu.Lock()
	missed := append([]Chunk{}, s.buf...)
	last := 0
	if len(missed) > 0 {
		last = missed[len(missed)-1].Seq
	}
	failed := s.err
	finished := s.done
	s.subscribers[out] = &subscriber{ch: out, afterSeq: last}
	s.mu.Unlock()

	go func() {
		defer close(out)
		for _, chunk := range missed {
			out <- chunk
		}
		if failed != nil {
			out <- Chunk{Err: failed}
			return
		}
		if finished {
			// The buffer already ends with the provider's done chunk when the
			// stream completed before this subscriber joined. Appending another
			// one would deliver the terminal marker twice, and a client that
			// stops at the first would never see the usage on the second.
			if len(missed) > 0 && missed[len(missed)-1].Done {
				return
			}
			out <- Chunk{Done: true}
			return
		}
		<-s.closed
		// The stream is still open. This goroutine owns the channel from here
		// on and must not return until the stream ends: returning early would
		// close the channel and make a live subscriber see a clean end to a
		// stream that never finished.
	}()
	return out
}

// Emit appends a chunk with the next sequence number and fans it out. It is the
// only way into the buffer, which is why the numbering cannot be skipped or
// duplicated by two concurrent callers.
func (s *StreamSession) Emit(chunk Chunk) {
	s.mu.Lock()
	chunk.Seq = len(s.buf) + 1
	s.buf = append(s.buf, chunk)
	if chunk.Done {
		s.done = true
	}
	targets := make([]*subscriber, 0, len(s.subscribers))
	for _, sub := range s.subscribers {
		// A late joiner already replayed up to afterSeq, and already-replayed
		// chunks stay in the buffer, so the fan-out skips anything at or below
		// that point instead of delivering it a second time.
		if chunk.Seq > sub.afterSeq {
			targets = append(targets, sub)
		}
	}
	s.mu.Unlock()

	for _, sub := range targets {
		select {
		case sub.ch <- chunk:
		default:
			// A subscriber that is not reading is dropped rather than allowed
			// to block every other one. Dropping is the only alternative to
			// one slow reader stalling the whole stream, and the dropped
			// client can resume from its last acknowledged sequence.
			s.drop(sub)
		}
	}
}

// drop unregisters a subscriber without locking, for the fan-out path.
func (s *StreamSession) drop(sub *subscriber) {
	s.mu.Lock()
	defer s.mu.Unlock()
	delete(s.subscribers, sub.ch)
}

// Fail records the terminal error and ends the stream.
func (s *StreamSession) Fail(err error) {
	s.mu.Lock()
	if s.done || s.err != nil {
		s.mu.Unlock()
		return
	}
	s.err = err
	targets := make([]*subscriber, 0, len(s.subscribers))
	for _, sub := range s.subscribers {
		targets = append(targets, sub)
	}
	s.mu.Unlock()

	for _, sub := range targets {
		select {
		case sub.ch <- Chunk{Err: err}:
		default:
			s.drop(sub)
		}
	}
	s.Close()
}

// Close ends the stream for every subscriber.
func (s *StreamSession) Close() {
	s.once.Do(func() {
		s.mu.Lock()
		s.done = true
		s.mu.Unlock()
		close(s.closed)
	})
}

// Replay returns every chunk after the given sequence number.
//
// This is what a client calls after reconnecting: it passes the last sequence
// it actually applied, and gets exactly the ones it missed, in order. A
// sequence number it never received is treated as "from the beginning" rather
// than an error, because a client that crashed cannot know how much it got.
func (s *StreamSession) Replay(afterSeq int) []Chunk {
	s.mu.Lock()
	defer s.mu.Unlock()
	out := make([]Chunk, 0, len(s.buf))
	for _, chunk := range s.buf {
		if chunk.Seq > afterSeq {
			out = append(out, chunk)
		}
	}
	return out
}

// LastSequence returns the highest sequence number emitted, or 0.
func (s *StreamSession) LastSequence() int {
	s.mu.Lock()
	defer s.mu.Unlock()
	if len(s.buf) == 0 {
		return 0
	}
	return s.buf[len(s.buf)-1].Seq
}

// Finished reports whether the stream has ended.
func (s *StreamSession) Finished() bool {
	s.mu.Lock()
	defer s.mu.Unlock()
	return s.done
}

// Error returns the terminal error, or nil.
func (s *StreamSession) Error() error {
	s.mu.Lock()
	defer s.mu.Unlock()
	return s.err
}

// RunStreamed drives a provider stream into a session.
//
// The context governs cancellation, so a client that goes away stops the
// provider call rather than leaving it to finish metering tokens nobody will
// read. The session is closed however the call ends, so a subscriber is never
// left waiting on a stream that already failed.
func (o *Orchestrator) RunStreamed(
	ctx context.Context,
	userID, tenantID string,
	req *Request,
	session *StreamSession,
) error {
	assembled := o.Assemble(req)

	if o.gate != nil {
		if err := o.gate.Authorise(
			userID, tenantID, req.Model,
			EstimateTokens(assembled), req.MaxTokens,
		); err != nil {
			session.Fail(err)
			return err
		}
	}

	stream, err := o.provider.Complete(ctx, assembled)
	if err != nil {
		wrapped := err
		session.Fail(wrapped)
		return wrapped
	}

	var b strings.Builder
	for chunk := range stream {
		if ctx.Err() != nil {
			// Cancellation is not a provider failure. Nothing further is
			// emitted and no usage is metered, because the answer was never
			// delivered.
			session.Fail(ctx.Err())
			return ctx.Err()
		}
		if chunk.Err != nil {
			session.Fail(chunk.Err)
			return chunk.Err
		}
		b.WriteString(chunk.Delta)
		// The provider's done chunk is emitted once, as it arrives. Emitting it
		// and then emitting a second done chunk of our own would give the
		// reader two "final" chunks, and a client that treats the first as
		// terminal would never see the usage recorded on the second.
		session.Emit(chunk)
		if chunk.Done {
			if o.gate != nil {
				o.gate.Record(userID, tenantID, req.Model, chunk.Usage)
			}
			session.Close()
			return nil
		}
	}

	// The provider closed without a done chunk. Treating that as success would
	// emit a success for a stream that never said it succeeded.
	session.Fail(errStreamTruncated)
	return errStreamTruncated
}

// errStreamTruncated is returned when a provider ends without a done chunk.
type streamTruncated struct{}

func (streamTruncated) Error() string { return "chat: stream ended without a done chunk" }

var errStreamTruncated error = streamTruncated{}
