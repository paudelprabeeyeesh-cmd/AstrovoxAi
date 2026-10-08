// Package assert provides assertion helpers for hermetic unit tests.
// Every helper calls t.Helper() and fails the test on violation.
package assert

import (
	"reflect"
	"testing"
)

// Equal asserts got is deeply equal to want.
func Equal[T any](t *testing.T, got, want T) {
	t.Helper()
	if !reflect.DeepEqual(got, want) {
		t.Errorf("Equal: got %v, want %v", got, want)
	}
}

// NotEqual asserts got is not deeply equal to want.
func NotEqual[T any](t *testing.T, got, want T) {
	t.Helper()
	if reflect.DeepEqual(got, want) {
		t.Errorf("NotEqual: got %v, want different", got)
	}
}

// True asserts cond holds.
func True(t *testing.T, cond bool, msg string) {
	t.Helper()
	if !cond {
		t.Errorf("True: condition false: %s", msg)
	}
}

// False asserts cond does not hold.
func False(t *testing.T, cond bool, msg string) {
	t.Helper()
	if cond {
		t.Errorf("False: condition true: %s", msg)
	}
}

// NoError asserts err is nil.
func NoError(t *testing.T, err error) {
	t.Helper()
	if err != nil {
		t.Errorf("NoError: unexpected error: %v", err)
	}
}

// Error asserts err is non-nil.
func Error(t *testing.T, err error) {
	t.Helper()
	if err == nil {
		t.Error("Error: expected error, got nil")
	}
}

// ErrorIs asserts err matches target per errors.Is.
func ErrorIs(t *testing.T, err, target error) {
	t.Helper()
	if err == nil {
		t.Errorf("ErrorIs: expected error matching %v, got nil", target)
		return
	}
	if !reflect.DeepEqual(err, target) && err.Error() != target.Error() {
		t.Errorf("ErrorIs: got %v, want %v", err, target)
	}
}

// Nil asserts v is nil.
func Nil(t *testing.T, v any) {
	t.Helper()
	if v != nil {
		t.Errorf("Nil: got %v, want nil", v)
	}
}

// NotNil asserts v is non-nil.
func NotNil(t *testing.T, v any) {
	t.Helper()
	if v == nil {
		t.Error("NotNil: got nil")
	}
}

// Len asserts the length of v equals want.
func Len(t *testing.T, v any, want int) {
	t.Helper()
	rv := reflect.ValueOf(v)
	switch rv.Kind() {
	case reflect.Slice, reflect.Array, reflect.Map, reflect.String, reflect.Chan:
		if rv.Len() != want {
			t.Errorf("Len: got %d, want %d", rv.Len(), want)
		}
	default:
		t.Errorf("Len: unsupported kind %s", rv.Kind())
	}
}

// InDelta asserts |got-want| <= delta for floating-point comparison.
func InDelta(t *testing.T, got, want, delta float64) {
	t.Helper()
	d := got - want
	if d < 0 {
		d = -d
	}
	if d > delta {
		t.Errorf("InDelta: |%v - %v| = %v > %v", got, want, d, delta)
	}
}

// Panics asserts fn panics.
func Panics(t *testing.T, fn func()) {
	t.Helper()
	defer func() {
		t.Helper()
		if recover() == nil {
			t.Error("Panics: function did not panic")
		}
	}()
	fn()
}

// Contains asserts substr appears in s.
func Contains(t *testing.T, s, substr string) {
	t.Helper()
	if !stringsContains(s, substr) {
		t.Errorf("Contains: %q does not contain %q", s, substr)
	}
}

func stringsContains(s, substr string) bool {
	return len(substr) == 0 || indexOf(s, substr) >= 0
}

func indexOf(s, substr string) int {
	for i := 0; i+len(substr) <= len(s); i++ {
		if s[i:i+len(substr)] == substr {
			return i
		}
	}
	return -1
}
