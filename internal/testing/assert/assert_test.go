package assert

import (
	"errors"
	"testing"
)

func TestEqual(t *testing.T) {
	Equal(t, 1, 1)
	Equal(t, "a", "a")
	Equal(t, []int{1, 2}, []int{1, 2})
}

func TestNotEqual(t *testing.T) {
	NotEqual(t, 1, 2)
	NotEqual(t, "a", "b")
}

func TestTrueFalse(t *testing.T) {
	True(t, 1 == 1, "one is one")
	False(t, 1 == 2, "one is not two")
}

func TestNoError(t *testing.T) {
	NoError(t, nil)
}

func TestError(t *testing.T) {
	Error(t, errors.New("x"))
}

func TestErrorIs(t *testing.T) {
	target := errors.New("target")
	ErrorIs(t, target, target)
}

func TestNilNotNil(t *testing.T) {
	Nil(t, nil)
	NotNil(t, errors.New("x"))
}

func TestLen(t *testing.T) {
	Len(t, []int{1, 2, 3}, 3)
	Len(t, "abc", 3)
	Len(t, map[string]int{"a": 1}, 1)
}

func TestInDelta(t *testing.T) {
	InDelta(t, 1.0, 1.05, 0.1)
	InDelta(t, -1.0, -1.05, 0.1)
}

func TestPanics(t *testing.T) {
	Panics(t, func() { panic("boom") })
}

func TestContains(t *testing.T) {
	Contains(t, "hello world", "world")
	Contains(t, "abc", "")
}
