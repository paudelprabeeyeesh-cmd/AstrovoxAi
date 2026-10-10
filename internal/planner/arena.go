package planner

import "errors"

var ErrArenaExhausted = errors.New("arena exhausted")

// Arena is a bump allocator for tensor memory.
type Arena struct {
	Size   int
	Offset int
	Blocks map[int][]byte
}

// NewArena creates a new arena of the given capacity.
func NewArena(size int) *Arena {
	return &Arena{
		Size:   size,
		Blocks: make(map[int][]byte),
	}
}

// Alloc reserves size bytes and returns the offset.
func (a *Arena) Alloc(size int) (int, error) {
	if a.Offset+size > a.Size {
		return 0, ErrArenaExhausted
	}
	off := a.Offset
	a.Offset += size
	return off, nil
}

// AllocBytes returns a byte slice from the arena (borrows underlying storage).
func (a *Arena) AllocBytes(size int) ([]byte, error) {
	off, err := a.Alloc(size)
	if err != nil {
		return nil, err
	}
	return a.Blocks[off], nil
}

// Reset resets the allocation pointer to zero.
func (a *Arena) Reset() {
	a.Offset = 0
}

// Remaining returns unallocated bytes.
func (a *Arena) Remaining() int {
	return a.Size - a.Offset
}

// Used returns allocated bytes.
func (a *Arena) Used() int {
	return a.Offset
}
