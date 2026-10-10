// Package errors provides the engine-wide typed error system with stable
// integer error codes, structured context fields, and wrapping compatible
// with errors.Is and errors.As.
package errors

import (
	"errors"
	"fmt"
	"strings"
)

// Code is a stable integer error classification. Codes are never reused or
// renumbered once assigned; new codes are appended only.
type Code int

// Stable error codes. The numeric values are part of the public contract.
const (
	CodeUnknown Code = iota
	CodeInvalidArgument
	CodeOutOfRange
	CodeShapeMismatch
	CodeDTypeMismatch
	CodeDeviceUnavailable
	CodeOutOfMemory
	CodeTimeout
	CodeCancelled
	CodeNotFound
	CodeAlreadyExists
	CodePermissionDenied
	CodeUnimplemented
	CodeCorruptData
	CodeSingularMatrix
	CodeInternal
	CodeModuleUnavailable
	CodeQueueFull
	CodeFutureConsumed
	CodeDoubleFree
	CodeSingular
	CodeCycleDetected
	CodeUnsupportedOp
	CodeVersionMismatch
	CodeResourceExhausted
)

var codeNames = map[Code]string{
	CodeUnknown:           "UNKNOWN",
	CodeInvalidArgument:   "INVALID_ARGUMENT",
	CodeOutOfRange:        "OUT_OF_RANGE",
	CodeShapeMismatch:     "SHAPE_MISMATCH",
	CodeDTypeMismatch:     "DTYPE_MISMATCH",
	CodeDeviceUnavailable: "DEVICE_UNAVAILABLE",
	CodeOutOfMemory:       "OUT_OF_MEMORY",
	CodeTimeout:           "TIMEOUT",
	CodeCancelled:         "CANCELLED",
	CodeNotFound:          "NOT_FOUND",
	CodeAlreadyExists:     "ALREADY_EXISTS",
	CodePermissionDenied:  "PERMISSION_DENIED",
	CodeUnimplemented:     "UNIMPLEMENTED",
	CodeCorruptData:       "CORRUPT_DATA",
	CodeSingularMatrix:    "SINGULAR_MATRIX",
	CodeInternal:          "INTERNAL",
	CodeModuleUnavailable: "MODULE_UNAVAILABLE",
	CodeQueueFull:         "QUEUE_FULL",
	CodeFutureConsumed:    "FUTURE_CONSUMED",
	CodeDoubleFree:        "DOUBLE_FREE",
	CodeSingular:          "SINGULAR",
	CodeCycleDetected:     "CYCLE_DETECTED",
	CodeUnsupportedOp:     "UNSUPPORTED_OP",
	CodeVersionMismatch:   "VERSION_MISMATCH",
	CodeResourceExhausted: "RESOURCE_EXHAUSTED",
}

func (c Code) String() string {
	if name, ok := codeNames[c]; ok {
		return name
	}
	return fmt.Sprintf("CODE_%d", int(c))
}

// Sentinel errors for use with errors.Is.
var (
	ErrUnknown           = New(CodeUnknown, "unknown error")
	ErrInvalidArgument   = New(CodeInvalidArgument, "invalid argument")
	ErrOutOfRange        = New(CodeOutOfRange, "value out of range")
	ErrShapeMismatch     = New(CodeShapeMismatch, "shape mismatch")
	ErrDTypeMismatch     = New(CodeDTypeMismatch, "dtype mismatch")
	ErrDeviceUnavailable = New(CodeDeviceUnavailable, "device unavailable")
	ErrOutOfMemory       = New(CodeOutOfMemory, "out of memory")
	ErrTimeout           = New(CodeTimeout, "operation timed out")
	ErrCancelled         = New(CodeCancelled, "operation cancelled")
	ErrNotFound          = New(CodeNotFound, "not found")
	ErrAlreadyExists     = New(CodeAlreadyExists, "already exists")
	ErrPermissionDenied  = New(CodePermissionDenied, "permission denied")
	ErrUnimplemented     = New(CodeUnimplemented, "operation unimplemented")
	ErrCorruptData       = New(CodeCorruptData, "data corrupted")
	ErrSingularMatrix    = New(CodeSingularMatrix, "matrix is singular")
	ErrInternal          = New(CodeInternal, "internal error")
	ErrModuleUnavailable = New(CodeModuleUnavailable, "module unavailable")
	ErrQueueFull         = New(CodeQueueFull, "queue full")
	ErrFutureConsumed    = New(CodeFutureConsumed, "future already consumed")
	ErrDoubleFree        = New(CodeDoubleFree, "double free detected")
	ErrCycleDetected     = New(CodeCycleDetected, "cycle detected")
	ErrUnsupportedOp     = New(CodeUnsupportedOp, "unsupported operation")
	ErrVersionMismatch   = New(CodeVersionMismatch, "version mismatch")
)

// Error is the structured error type returned across the engine.
type Error struct {
	code    Code
	message string
	op      string
	fields  []Field
	cause   error
}

// Field attaches structured context to an error.
type Field struct {
	Key   string
	Value any
}

// New creates a typed error with the given code and message.
func New(code Code, message string) *Error {
	return &Error{code: code, message: message}
}

// Wrap attaches a cause to an error, preserving the original code.
func Wrap(err error, code Code, message string) *Error {
	e := New(code, message)
	var cause *Error
	if errors.As(err, &cause) {
		e.fields = append(e.fields, Field{Key: "cause_code", Value: cause.code.String()})
	}
	e.cause = err
	return e
}

// WithOp annotates the error with the operation that produced it.
func (e *Error) WithOp(op string) *Error {
	out := *e
	out.op = op
	return &out
}

// WithField attaches a structured context field.
func (e *Error) WithField(key string, value any) *Error {
	out := *e
	out.fields = append(append([]Field(nil), e.fields...), Field{Key: key, Value: value})
	return &out
}

// Code returns the error classification code.
func (e *Error) Code() Code { return e.code }

// Op returns the originating operation, if annotated.
func (e *Error) Op() string { return e.op }

// Fields returns the structured context fields.
func (e *Error) Fields() []Field { return e.fields }

// Unwrap exposes the cause for errors.Is/errors.As traversal.
func (e *Error) Unwrap() error { return e.cause }

// Error implements the error interface.
func (e *Error) Error() string {
	var b strings.Builder
	b.WriteString(e.code.String())
	b.WriteString(": ")
	b.WriteString(e.message)
	if e.op != "" {
		b.WriteString(" [op=")
		b.WriteString(e.op)
		b.WriteString("]")
	}
	for _, f := range e.fields {
		b.WriteString(" [")
		b.WriteString(f.Key)
		b.WriteString("=")
		b.WriteString(fmt.Sprint(f.Value))
		b.WriteString("]")
	}
	if e.cause != nil {
		b.WriteString(": ")
		b.WriteString(e.cause.Error())
	}
	return b.String()
}

// Is reports whether the error or any error in its chain matches target.
func (e *Error) Is(target error) bool {
	if t, ok := target.(*Error); ok {
		return e.code == t.code
	}
	return false
}

// CodeOf extracts the typed code from an error, returning CodeUnknown for
// untyped errors.
func CodeOf(err error) Code {
	var e *Error
	if errors.As(err, &e) {
		return e.code
	}
	return CodeUnknown
}

// IsCode reports whether err carries the given typed code.
func IsCode(err error, code Code) bool {
	var e *Error
	if errors.As(err, &e) {
		return e.code == code
	}
	return false
}
