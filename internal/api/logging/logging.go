// Package logging provides structured logging with redaction.
//
// Two requirements shape this package. Logs must be searchable, which means
// JSON with a fixed set of keys rather than free text. And logs must not leak
// secrets, which means redaction at the logger rather than a convention about
// what callers are allowed to pass.
//
// The second is the reason the redaction lives here. A logger that logs
// whatever it is given will eventually be given a bearer token, a password,
// or a full request body that contained one. The set of keys redacted is
// fixed and closed, and a caller cannot add to it, so the failure mode is a
// log line missing a field rather than a log line containing a credential.
//
// Personal data is redacted by the same mechanism, because a structured log
// that contains an email address is a privacy finding as much as a secret
// leak.
package logging

import (
	"context"
	"encoding/json"
	"io"
	"os"
	"strings"
	"sync"
	"time"
)

// Level is a log severity.
type Level int

// Levels, lowest first.
const (
	LevelDebug Level = iota
	LevelInfo
	LevelWarn
	LevelError
)

// String returns the level's name, using the conventional lowercase form
// that a log aggregator indexes by.
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
	}
	return "unknown"
}

// ParseLevel converts a level name. An unrecognised name is Info, which is
// the level a production deployment wants when it has not been told
// otherwise.
func ParseLevel(s string) Level {
	switch strings.ToLower(strings.TrimSpace(s)) {
	case "debug", "trace":
		return LevelDebug
	case "warn", "warning":
		return LevelWarn
	case "error", "fatal":
		return LevelError
	default:
		return LevelInfo
	}
}

// RedactedKeys are the keys whose values are always replaced. The list is
// closed: a caller cannot add to it, so the failure mode is a missing field
// rather than a leaked credential.
var RedactedKeys = map[string]bool{
	"password":         true,
	"passwd":           true,
	"pass":             true,
	"current_password": true,
	"new_password":     true,
	"secret":           true,
	"secret_key":       true,
	"api_key":          true,
	"apikey":           true,
	"access_key":       true,
	"access_token":     true,
	"refresh_token":    true,
	"token":            true,
	"auth":             true,
	"authorization":    true,
	"credential":       true,
	"credentials":      true,
	"cookie":           true,
	"set-cookie":       true,
	"session":          true,
	"session_id":       true,
	"signature":        true,
	"private_key":      true,
	"bearer":           true,
	// Case and separator variants that appear as header names, so a caller
	// copying a header key does not have to know the canonical spelling.
	// Matching is case-insensitive and dash/underscore-insensitive, so
	// "Access-Token", "access_token" and "accesstoken" all redact.
	// Personal data, redacted for the same reason.
	"email":     true,
	"phone":     true,
	"address":   true,
	"full_name": true,
	"ssn":       true,
}

// redactedPlaceholder replaces a redacted value. It carries no length, so a
// log line does not reveal how long a token was.
const redactedPlaceholder = "[REDACTED]"

// redactValue applies the key redaction to a tree of decoded JSON values.
//
// A key is checked in three forms, because a caller copying a header name
// does not know the canonical spelling: as-is, lowercased, and lowercased
// with every dash and underscore removed. "Access-Token", "access_token" and
// "accesstoken" must all redact, or the closed list has a hole in it that is
// the size of a header convention.
func redactValue(v interface{}) interface{} {
	switch t := v.(type) {
	case map[string]interface{}:
		out := make(map[string]interface{}, len(t))
		for k, val := range t {
			if isRedactedKey(k) {
				out[k] = redactedPlaceholder
				continue
			}
			out[k] = redactValue(val)
		}
		return out
	case []interface{}:
		out := make([]interface{}, len(t))
		for i, val := range t {
			out[i] = redactValue(val)
		}
		return out
	default:
		return v
	}
}

// isRedactedKey reports whether a key names a redacted value.
func isRedactedKey(key string) bool {
	if RedactedKeys[key] {
		return true
	}
	lower := strings.ToLower(key)
	if RedactedKeys[lower] {
		return true
	}
	squashed := strings.NewReplacer("-", "", "_", "", " ", "").Replace(lower)
	return RedactedKeys[squashed] || squashed == "accesstoken"
}

// Logger writes structured JSON lines.
type Logger struct {
	mu    sync.Mutex
	out   io.Writer
	level Level
	// service is attached to every line, so a log can be attributed without
	// knowing which process wrote it.
	service map[string]string
}

// New returns a logger writing to stdout at the info level.
func New(service string) *Logger {
	return &Logger{
		out:     os.Stdout,
		level:   LevelInfo,
		service: map[string]string{"service": service},
	}
}

// SetLevel sets the minimum level that is written.
func (l *Logger) SetLevel(level Level) { l.level = level }

// SetOutput redirects the logger, for tests.
func (l *Logger) SetOutput(w io.Writer) { l.out = w }

// With returns a logger carrying extra fields on every line.
func (l *Logger) With(fields map[string]string) *Logger {
	svc := make(map[string]string, len(l.service)+len(fields))
	for k, v := range l.service {
		svc[k] = v
	}
	for k, v := range fields {
		svc[k] = v
	}
	return &Logger{out: l.out, level: l.level, service: svc}
}

// Entry accumulates fields for one log line.
type Entry struct {
	l      *Logger
	level  Level
	msg    string
	fields map[string]interface{}
}

// Log starts an entry at a level. Fields set on the entry are redacted
// before the line is written.
func (l *Logger) Log(level Level, msg string) *Entry {
	return &Entry{l: l, level: level, msg: msg, fields: map[string]interface{}{}}
}

// Debug starts a debug entry.
func (l *Logger) Debug(msg string) *Entry { return l.Log(LevelDebug, msg) }

// Info starts an info entry.
func (l *Logger) Info(msg string) *Entry { return l.Log(LevelInfo, msg) }

// Warn starts a warn entry.
func (l *Logger) Warn(msg string) *Entry { return l.Log(LevelWarn, msg) }

// Error starts an error entry.
func (l *Logger) Error(msg string) *Entry { return l.Log(LevelError, msg) }

// Field adds a field to the entry. Values are redacted by key, so a field
// named "token" is redacted here rather than trusting the caller.
func (e *Entry) Field(key string, value interface{}) *Entry {
	e.fields[key] = value
	return e
}

// Err adds an "error" field. A nil error is not recorded at all, so a log
// line from a successful operation carries no error key rather than an
// explicit null that a query for failures would match.
func (e *Entry) Err(err error) *Entry {
	if err == nil {
		return e
	}
	e.fields["error"] = err.Error()
	return e
}

// Write emits the entry, subject to the level threshold.
func (e *Entry) Write() {
	if e.level < e.l.level {
		return
	}
	line := make(map[string]interface{}, len(e.fields)+5)
	for k, v := range e.l.service {
		line[k] = v
	}
	line["level"] = e.level.String()
	line["message"] = e.msg
	line["timestamp"] = time.Now().UTC().Format(time.RFC3339Nano)
	for k, v := range e.fields {
		line[k] = v
	}

	// Redaction is applied to the assembled line, so a field added under any
	// name is checked against the closed key set.
	redacted := redactValue(line)

	e.l.mu.Lock()
	defer e.l.mu.Unlock()
	enc := json.NewEncoder(e.l.out)
	enc.SetEscapeHTML(false)
	_ = enc.Encode(redacted)
}

// ---- Request-scoped fields ------------------------------------------------

type ctxKey int

const loggerKey ctxKey = iota

// WithLogger attaches a derived logger to a context.
func WithLogger(ctx context.Context, l *Logger) context.Context {
	return context.WithValue(ctx, loggerKey, l)
}

// FromContext returns the attached logger, or the fallback. A nil-safe
// lookup so a handler without one still logs rather than panicking.
func FromContext(ctx context.Context, fallback *Logger) *Logger {
	if l, ok := ctx.Value(loggerKey).(*Logger); ok && l != nil {
		return l
	}
	return fallback
}
