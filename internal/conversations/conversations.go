// Package conversations implements the conversation and message store in
// Go: chats, messages, branches, and the owner scope that keeps them
// separated.
//
// The store is owner-scoped at the API boundary rather than relying on a
// database policy. Every read and write takes the owner as its first
// argument, and a store method never accepts an owner from the caller's
// request body. This is the same rule the Supabase RLS policies enforce,
// expressed in Go because this server has no Postgres.
//
// Branching is first-class: a message can have a parent, and editing a
// prompt creates a sibling rather than overwriting. Superseded messages are
// marked rather than deleted, so the original of a branch remains readable.
package conversations

import (
	"sync"
	"time"
)

// Role identifies a message's speaker, matching chat.Role.
type Role string

// The four roles a message may carry.
const (
	RoleSystem    Role = "system"
	RoleUser      Role = "user"
	RoleAssistant Role = "assistant"
	RoleTool      Role = "tool"
)

// Message is one turn.
type Message struct {
	ID        string    `json:"id"`
	ParentID  string    `json:"parent_id,omitempty"`
	Role      Role      `json:"role"`
	Content   string    `json:"content"`
	Model     string    `json:"model,omitempty"`
	CreatedAt time.Time `json:"created_at"`
	// Superseded marks a message replaced by a newer sibling. Superseded
	// messages are hidden by default but not deleted, so the original of a
	// branch remains recoverable.
	Superseded bool `json:"superseded"`
}

// Conversation is a chat with an owner.
type Conversation struct {
	ID        string    `json:"id"`
	Owner     string    `json:"owner"`
	Title     string    `json:"title"`
	CreatedAt time.Time `json:"created_at"`
	UpdatedAt time.Time `json:"updated_at"`
}

// Store holds conversations and their messages in process, scoped by owner.
type Store struct {
	mu            sync.RWMutex
	conversations map[string]*Conversation
	// messages is keyed by conversation id and ordered by creation.
	messages map[string][]*Message
	nextID   int
	// limit bounds messages per conversation, so an unbounded chat cannot
	// grow memory without limit.
	limit int
}

// New returns a store. A non-positive limit becomes a default rather than a
// store that cannot hold anything.
func New(limit int) *Store {
	if limit <= 0 {
		limit = 10_000
	}
	return &Store{
		conversations: map[string]*Conversation{},
		messages:      map[string][]*Message{},
		limit:         limit,
	}
}

// Create makes a conversation owned by the caller.
func (s *Store) Create(owner, title string) *Conversation {
	s.mu.Lock()
	defer s.mu.Unlock()
	s.nextID++
	now := time.Now().UTC()
	c := &Conversation{
		ID:        s.id(),
		Owner:     owner,
		Title:     title,
		CreatedAt: now,
		UpdatedAt: now,
	}
	s.conversations[c.ID] = c
	s.messages[c.ID] = nil
	return c
}

// Get returns a conversation only when it is owned by the caller. A
// cross-owner read returns nil, not the other owner's row.
func (s *Store) Get(owner, id string) *Conversation {
	s.mu.RLock()
	defer s.mu.RUnlock()
	c := s.conversations[id]
	if c == nil || c.Owner != owner {
		return nil
	}
	// A copy, so a caller mutating the result cannot corrupt the store.
	out := *c
	return &out
}

// List returns the caller's conversations, most recently updated first.
func (s *Store) List(owner string) []*Conversation {
	s.mu.RLock()
	defer s.mu.RUnlock()
	var out []*Conversation
	for _, c := range s.conversations {
		if c.Owner == owner {
			out = append(out, c)
		}
	}
	// Insertion-ordered sort by UpdatedAt, newest first. Stable so a list
	// is reproducible between two identical calls.
	for i := 1; i < len(out); i++ {
		for j := i; j > 0 && out[j].UpdatedAt.After(out[j-1].UpdatedAt); j-- {
			out[j], out[j-1] = out[j-1], out[j]
		}
	}
	return out
}

// Rename updates a conversation's title, owner-scoped.
func (s *Store) Rename(owner, id, title string) bool {
	s.mu.Lock()
	defer s.mu.Unlock()
	c := s.conversations[id]
	if c == nil || c.Owner != owner {
		return false
	}
	c.Title = title
	c.UpdatedAt = time.Now().UTC()
	return true
}

// Delete removes a conversation and its messages, owner-scoped. A
// cross-owner delete returns false and leaves the row intact.
func (s *Store) Delete(owner, id string) bool {
	s.mu.Lock()
	defer s.mu.Unlock()
	c := s.conversations[id]
	if c == nil || c.Owner != owner {
		return false
	}
	delete(s.conversations, id)
	delete(s.messages, id)
	return true
}

// AddMessage appends a message to the caller's conversation. Superseding a
// message marks the older sibling rather than deleting it.
func (s *Store) AddMessage(owner, conversationID string, parentID string, role Role, content, model string) *Message {
	s.mu.Lock()
	defer s.mu.Unlock()
	c := s.conversations[conversationID]
	if c == nil || c.Owner != owner {
		return nil
	}
	if parentID != "" {
		for _, m := range s.messages[conversationID] {
			if m.ID == parentID {
				m.Superseded = true
			}
		}
	}
	s.nextID++
	now := time.Now().UTC()
	m := &Message{
		ID:        s.id(),
		ParentID:  parentID,
		Role:      role,
		Content:   content,
		Model:     model,
		CreatedAt: now,
	}
	items := append(s.messages[conversationID], m)
	// Bound the message list, evicting the oldest, so an unbounded
	// conversation cannot grow without limit.
	if len(items) > s.limit {
		items = items[len(items)-s.limit:]
	}
	s.messages[conversationID] = items
	c.UpdatedAt = now
	return m
}

// Messages returns a conversation's messages, owner-scoped. Superseded
// messages are hidden unless includeSuperseded is set.
func (s *Store) Messages(owner, conversationID string, includeSuperseded bool) []*Message {
	s.mu.RLock()
	defer s.mu.RUnlock()
	c := s.conversations[conversationID]
	if c == nil || c.Owner != owner {
		return nil
	}
	out := make([]*Message, 0, len(s.messages[conversationID]))
	for _, m := range s.messages[conversationID] {
		if m.Superseded && !includeSuperseded {
			continue
		}
		// A copy, so a caller mutating the result cannot corrupt the store.
		cp := *m
		out = append(out, &cp)
	}
	return out
}

// Stats reports the store's totals, for an operator-facing endpoint.
func (s *Store) Stats() map[string]int {
	s.mu.RLock()
	defer s.mu.RUnlock()
	messages := 0
	for _, v := range s.messages {
		messages += len(v)
	}
	return map[string]int{
		"conversations": len(s.conversations),
		"messages":      messages,
	}
}

// id returns a compact unique id. It is not a security token: it identifies
// a row, it does not authenticate one.
func (s *Store) id() string {
	const alphabet = "0123456789abcdefghijklmnopqrstuvwxyz"
	n := s.nextID
	b := make([]byte, 12)
	for i := range b {
		b[i] = alphabet[n%len(alphabet)]
		n /= len(alphabet)
	}
	return string(b)
}
