// Package logger provides a structured, leveled, asynchronous logging facade
// for the Astrovox engine. Records are produced into a bounded ring buffer and
// drained by a single background goroutine, keeping hot-path cost allocation-free.
package logger

import (
	"encoding/json"
	"fmt"
	"os"
	"sync"
	"sync/atomic"
	"time"
)

// Level defines log severity ordering.
type Level int

const (
	LevelDebug Level = iota
	LevelInfo
	LevelWarn
	LevelError
	LevelFatal
)

func (l Level) String() string {
	switch l {
	case LevelDebug:
		return "debug"
	case LevelInfo:
		return "info"
	case LevelWarn:
		return "warn"
	case LevelError:
		return "error"
	case LevelFatal:
		return "fatal"
	default:
		return "unknown"
	}
}

// Field is a structured key/value pair attached to a record.
type Field struct {
	Key   string
	Value any
}

// Fields builds a Field slice from alternating key/value arguments.
func Fields(kv ...any) []Field {
	if len(kv)%2 != 0 {
		kv = append(kv, "<odd-argument>")
	}
	out := make([]Field, 0, len(kv)/2)
	for i := 0; i < len(kv); i += 2 {
		out = append(out, Field{Key: fmt.Sprint(kv[i]), Value: kv[i+1]})
	}
	return out
}

const ringSize = 1 << 16

type record struct {
	Level   Level    `json:"level"`
	Time    string   `json:"time"`
	Message string   `json:"msg"`
	Module  string   `json:"module,omitempty"`
	Fields  []Field  `json:"fields,omitempty"`
}

type ringBuffer struct {
	mu      sync.Mutex
	buf     []*record
	head    int
	tail    int
	count   int
	dropped atomic.Uint64
}

func newRingBuffer() *ringBuffer { return &ringBuffer{buf: make([]*record, ringSize)} }

func (r *ringBuffer) push(rec *record) {
	r.mu.Lock()
	if r.count == ringSize {
		r.dropped.Add(1)
		r.buf[r.head] = rec
		r.head = (r.head + 1) % ringSize
		r.tail = r.head
	} else {
		r.buf[r.tail] = rec
		r.tail = (r.tail + 1) % ringSize
		r.count++
	}
	r.mu.Unlock()
}

func (r *ringBuffer) pop() *record {
	r.mu.Lock()
	defer r.mu.Unlock()
	if r.count == 0 {
		return nil
	}
	rec := r.buf[r.head]
	r.buf[r.head] = nil
	r.head = (r.head + 1) % ringSize
	r.count--
	return rec
}

func (r *ringBuffer) len() int {
	r.mu.Lock()
	defer r.mu.Unlock()
	return r.count
}

// Sink consumes serialized records.
type Sink interface {
	Write([]byte) (int, error)
}

// loggerCore holds the shared drain lifecycle.
// It is owned by the parent logger and shared
// with module-scoped child loggers by pointer,
// so constructing a child never copies locks.
type loggerCore struct {
	ring *ringBuffer
	sink Sink
	stop chan struct{}
	done chan struct{}
	once sync.Once
}

// Logger is the structured logger instance.
type Logger struct {
	level  atomic.Int64
	module string
	core   *loggerCore
}

var defaultLogger = New(os.Stderr)

// Default returns the process-wide logger.
func Default() *Logger { return defaultLogger }

// SetDefault replaces the process-wide logger and returns the previous one.
func SetDefault(l *Logger) *Logger {
	old := defaultLogger
	defaultLogger = l
	return old
}

// New creates a logger draining to the given sink with level Info.
func New(sink Sink) *Logger {
	core := &loggerCore{
		ring: newRingBuffer(),
		sink: sink,
		stop: make(chan struct{}),
		done: make(chan struct{}),
	}
	l := &Logger{core: core}
	l.level.Store(int64(LevelInfo))
	go l.drain()
	return l
}

// WithModule returns a child logger tagging records with the module name.
// The child shares the parent's ring buffer and drain goroutine; its
// level is copied from the parent at creation time.
func (l *Logger) WithModule(name string) *Logger {
	child := &Logger{core: l.core, module: name}
	child.level.Store(l.level.Load())
	return child
}

// SetLevel sets the minimum severity that is emitted.
func (l *Logger) SetLevel(level Level) { l.level.Store(int64(level)) }

// Level returns the current minimum severity.
func (l *Logger) Level() Level { return Level(l.level.Load()) }

// Dropped returns the number of records lost to ring-buffer overflow.
func (l *Logger) Dropped() uint64 { return l.core.ring.dropped.Load() }

// Pending returns the number of records awaiting drain.
func (l *Logger) Pending() int { return l.core.ring.len() }

func (l *Logger) emit(level Level, msg string, fields []Field) {
	if Level(l.level.Load()) > level {
		return
	}
	rec := &record{
		Level:   level,
		Time:    time.Now().UTC().Format(time.RFC3339Nano),
		Message: msg,
		Module:  l.module,
		Fields:  fields,
	}
	l.core.ring.push(rec)
}

// Debug logs at debug level.
func (l *Logger) Debug(msg string, fields ...Field) { l.emit(LevelDebug, msg, fields) }

// Info logs at info level.
func (l *Logger) Info(msg string, fields ...Field) { l.emit(LevelInfo, msg, fields) }

// Warn logs at warn level.
func (l *Logger) Warn(msg string, fields ...Field) { l.emit(LevelWarn, msg, fields) }

// Error logs at error level.
func (l *Logger) Error(msg string, fields ...Field) { l.emit(LevelError, msg, fields) }

// Fatal logs at fatal level, flushes, then exits the process with status 1.
func (l *Logger) Fatal(msg string, fields ...Field) {
	l.emit(LevelFatal, msg, fields)
	l.Sync()
	l.Close()
	os.Exit(1)
}

func (l *Logger) drain() {
	defer close(l.core.done)
	enc := json.NewEncoder(l.core.sink)
	for {
		select {
		case <-l.core.stop:
			for {
				rec := l.core.ring.pop()
				if rec == nil {
					return
				}
				_ = enc.Encode(rec)
			}
		default:
			rec := l.core.ring.pop()
			if rec == nil {
				time.Sleep(time.Millisecond)
				continue
			}
			_ = enc.Encode(rec)
		}
	}
}

// Sync flushes all pending records to the sink.
func (l *Logger) Sync() {
	for l.core.ring.len() > 0 {
		time.Sleep(time.Millisecond)
	}
}

// Close stops the drain goroutine after flushing remaining records.
func (l *Logger) Close() {
	l.core.once.Do(func() {
		close(l.core.stop)
		<-l.core.done
	})
}

// Logf is a package-level convenience for the default logger.
func Logf(level Level, format string, args ...any) {
	Default().emit(level, fmt.Sprintf(format, args...), nil)
}
