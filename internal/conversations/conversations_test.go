package conversations

import (
	"testing"
)

func TestCreateReturnsAnOwnerScopedConversation(t *testing.T) {
	s := New(0)
	c := s.Create("u1", "First chat")
	if c.Owner != "u1" {
		t.Fatalf("owner = %q, want u1", c.Owner)
	}
	if got := s.Get("u1", c.ID); got == nil {
		t.Fatal("the owner cannot read their own conversation")
	}
}

func TestGetIsOwnerScoped(t *testing.T) {
	// The cross-read isolation property, the one that matters most.
	s := New(0)
	c := s.Create("u1", "private")
	if got := s.Get("u2", c.ID); got != nil {
		t.Fatal("tenant B read tenant A's conversation")
	}
}

func TestGetReturnsACopy(t *testing.T) {
	s := New(0)
	c := s.Create("u1", "original")
	got := s.Get("u1", c.ID)
	got.Title = "mutated"
	if s.Get("u1", c.ID).Title != "original" {
		t.Fatal("mutating the returned conversation corrupted the store")
	}
}

func TestGetOfAMissingIDIsNil(t *testing.T) {
	s := New(0)
	if s.Get("u1", "no-such-id") != nil {
		t.Fatal("a missing id returned a conversation")
	}
}

func TestListIsOwnerScoped(t *testing.T) {
	s := New(0)
	s.Create("u1", "a")
	s.Create("u1", "b")
	s.Create("u2", "c")
	if got := len(s.List("u2")); got != 1 {
		t.Fatalf("tenant B sees %d conversations, want 1", got)
	}
}

func TestListIsNewestFirst(t *testing.T) {
	s := New(0)
	s.Create("u1", "older")
	s.Create("u1", "newer")
	// Touch the first, so it becomes the most recently updated.
	s.Rename("u1", s.List("u1")[0].ID, "older")
	list := s.List("u1")
	if list[0].Title != "older" {
		t.Fatalf("newest-first order broken: %q is first", list[0].Title)
	}
}

func TestRenameIsOwnerScoped(t *testing.T) {
	s := New(0)
	c := s.Create("u1", "before")
	if s.Rename("u2", c.ID, "hijacked") {
		t.Fatal("tenant B renamed tenant A's conversation")
	}
	if !s.Rename("u1", c.ID, "after") {
		t.Fatal("the owner could not rename their own conversation")
	}
}

func TestDeleteIsOwnerScoped(t *testing.T) {
	s := New(0)
	c := s.Create("u1", "x")
	if s.Delete("u2", c.ID) {
		t.Fatal("tenant B deleted tenant A's conversation")
	}
	if !s.Delete("u1", c.ID) {
		t.Fatal("the owner could not delete their own conversation")
	}
	if s.Get("u1", c.ID) != nil {
		t.Fatal("the deleted conversation is still readable")
	}
}

func TestAddMessageIsOwnerScoped(t *testing.T) {
	s := New(0)
	c := s.Create("u1", "chat")
	if s.AddMessage("u2", c.ID, "", RoleUser, "injected", "") != nil {
		t.Fatal("tenant B added a message to tenant A's conversation")
	}
	if s.AddMessage("u1", c.ID, "", RoleUser, "hello", "") == nil {
		t.Fatal("the owner could not add their own message")
	}
}

func TestMessagesAreOwnerScoped(t *testing.T) {
	s := New(0)
	c := s.Create("u1", "chat")
	s.AddMessage("u1", c.ID, "", RoleUser, "private note", "")
	if got := s.Messages("u2", c.ID, false); got != nil {
		t.Fatalf("tenant B sees %d of tenant A's messages", len(got))
	}
}

func TestEditingCreatesASiblingAndSupersedes(t *testing.T) {
	// Editing a prompt must not destroy the original.
	s := New(0)
	c := s.Create("u1", "chat")
	first := s.AddMessage("u1", c.ID, "", RoleUser, "first version", "")
	second := s.AddMessage("u1", c.ID, first.ID, RoleUser, "edited version", "")
	if second.ParentID != first.ID {
		t.Fatal("the edit did not carry the original's id as its parent")
	}
	visible := s.Messages("u1", c.ID, false)
	if len(visible) != 1 || visible[0].Content != "edited version" {
		t.Fatalf("visible messages = %+v, want only the newest", visible)
	}
	all := s.Messages("u1", c.ID, true)
	if len(all) != 2 {
		t.Fatalf("all messages = %d, want 2: the original was deleted", len(all))
	}
}

func TestMessageListIsBounded(t *testing.T) {
	// An unbounded conversation must not grow without limit.
	s := New(3)
	c := s.Create("u1", "chat")
	for i := 0; i < 20; i++ {
		s.AddMessage("u1", c.ID, "", RoleUser, "msg", "")
	}
	if got := len(s.Messages("u1", c.ID, true)); got > 3 {
		t.Fatalf("message list grew to %d with a limit of 3", got)
	}
}

func TestStatsCountsEverything(t *testing.T) {
	s := New(0)
	s.Create("u1", "a")
	c := s.Create("u1", "b")
	s.AddMessage("u1", c.ID, "", RoleUser, "x", "")
	stats := s.Stats()
	if stats["conversations"] != 2 {
		t.Fatalf("conversations = %d, want 2", stats["conversations"])
	}
	if stats["messages"] != 1 {
		t.Fatalf("messages = %d, want 1", stats["messages"])
	}
}

func TestIDsAreUnique(t *testing.T) {
	s := New(0)
	seen := map[string]bool{}
	for i := 0; i < 200; i++ {
		c := s.Create("u1", "x")
		if seen[c.ID] {
			t.Fatalf("duplicate id generated: %q", c.ID)
		}
		seen[c.ID] = true
	}
}
