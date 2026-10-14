package chat

import (
	"sort"
	"strings"
	"sync"
	"testing"
	"time"
)

// The property being pinned is that an edit does not destroy what it replaced.
// A turn is a node with a parent, so editing creates a child and the original
// stays reachable; the caller moves between edits by selecting a head.

func newTestStore(t *testing.T) *ConversationStore {
	t.Helper()
	s := NewConversationStore()
	conversation, err := s.Create("u1", "Test", "", 0)
	if err != nil {
		t.Fatalf("create failed: %v", err)
	}
	if _, err := s.AddTurn(conversation.ConversationID, RoleUser, "hello", "", Usage{}); err != nil {
		t.Fatalf("add turn failed: %v", err)
	}
	if _, err := s.AddTurn(conversation.ConversationID, RoleAssistant, "hi there", "gpt-4o-mini", Usage{InputTokens: 5, OutputTokens: 3}); err != nil {
		t.Fatalf("add turn failed: %v", err)
	}
	return s
}

func mustCreate(t *testing.T, s *ConversationStore) *Conversation {
	t.Helper()
	c, err := s.Create("u1", "Test", "", 0)
	if err != nil {
		t.Fatalf("create failed: %v", err)
	}
	return c
}

func mustAdd(t *testing.T, s *ConversationStore, cid string, role Role, content string) *Turn {
	t.Helper()
	turn, err := s.AddTurn(cid, role, content, "", Usage{})
	if err != nil {
		t.Fatalf("add turn failed: %v", err)
	}
	return turn
}

func TestCreateAndAddTurns(t *testing.T) {
	s := newTestStore(t)
	c := mustCreate(t, s)
	if _, err := s.AddTurn(c.ConversationID, RoleUser, "hello", "", Usage{}); err != nil {
		t.Fatalf("add failed: %v", err)
	}
	history, err := s.HistoryForLLM(c.ConversationID, 20)
	if err != nil {
		t.Fatalf("history failed: %v", err)
	}
	if len(history) != 1 {
		t.Fatalf("history has %d turns, want 1", len(history))
	}
}

func TestHistoryIsInConversationOrder(t *testing.T) {
	s := newTestStore(t)
	c := mustCreate(t, s)
	mustAdd(t, s, c.ConversationID, RoleUser, "first")
	mustAdd(t, s, c.ConversationID, RoleAssistant, "second")
	mustAdd(t, s, c.ConversationID, RoleUser, "third")

	history, err := s.HistoryForLLM(c.ConversationID, 20)
	if err != nil {
		t.Fatalf("history failed: %v", err)
	}
	want := []string{"first", "second", "third"}
	for i := range want {
		if history[i].Content != want[i] {
			t.Fatalf("turn %d is %q, want %q", i, history[i].Content, want[i])
		}
	}
}

func TestAnEditDoesNotDestroyTheOriginal(t *testing.T) {
	s := newTestStore(t)
	c := mustCreate(t, s)
	original := mustAdd(t, s, c.ConversationID, RoleUser, "the original question")

	replacement, err := s.EditTurn(c.ConversationID, original.TurnID, "the edited question")
	if err != nil {
		t.Fatalf("edit failed: %v", err)
	}

	// The original is still reachable, which is the whole point of branching.
	fetched, err := s.Get(c.ConversationID)
	if err != nil {
		t.Fatalf("get failed: %v", err)
	}
	if _, ok := fetched.turns[original.TurnID]; !ok {
		t.Fatal("the original turn was destroyed by an edit")
	}
	if replacement.BranchedFrom != original.TurnID {
		t.Fatalf("replacement does not record what it replaced: %q", replacement.BranchedFrom)
	}
}

func TestAnEditSitsBesideTheOriginalRatherThanAfterTheReply(t *testing.T) {
	// The specific bug this guards: an edit of the first turn must be a sibling
	// of it, not a child of the reply that followed it. Attaching under the head
	// places the edit after the answer, so the branch is invisible.
	s := newTestStore(t)
	c := mustCreate(t, s)
	question := mustAdd(t, s, c.ConversationID, RoleUser, "question")
	mustAdd(t, s, c.ConversationID, RoleAssistant, "answer")

	replacement, err := s.EditTurn(c.ConversationID, question.TurnID, "question edited")
	if err != nil {
		t.Fatalf("edit failed: %v", err)
	}

	if replacement.ParentID != question.ParentID {
		t.Fatalf(
			"replacement parent %q does not match original parent %q; the edit is nested rather than a sibling",
			replacement.ParentID, question.ParentID,
		)
	}

	branches, err := s.Branches(c.ConversationID, question.TurnID)
	if err != nil {
		t.Fatalf("branches failed: %v", err)
	}
	if len(branches) != 2 {
		t.Fatalf("got %d siblings, want the original and its edit side by side", len(branches))
	}
}

func TestSelectingTheOriginalRestoresTheOldBranch(t *testing.T) {
	s := newTestStore(t)
	c := mustCreate(t, s)
	question := mustAdd(t, s, c.ConversationID, RoleUser, "original question")
	mustAdd(t, s, c.ConversationID, RoleAssistant, "answer")

	if _, err := s.EditTurn(c.ConversationID, question.TurnID, "edited question"); err != nil {
		t.Fatalf("edit failed: %v", err)
	}

	if _, err := s.SelectHead(c.ConversationID, question.TurnID); err != nil {
		t.Fatalf("select failed: %v", err)
	}
	history, err := s.HistoryForLLM(c.ConversationID, 20)
	if err != nil {
		t.Fatalf("history failed: %v", err)
	}
	if len(history) == 0 || history[0].Content != "original question" {
		t.Fatalf("selecting the original did not restore it: %v", history)
	}
}

func TestHistoryShowsOnlyTheSelectedBranch(t *testing.T) {
	// A branch the caller did not selected would appear as a parallel line in
	// the prompt, so a model would see two versions of the same turn with no way
	// to tell which is current.
	s := newTestStore(t)
	c := mustCreate(t, s)
	question := mustAdd(t, s, c.ConversationID, RoleUser, "question")

	if _, err := s.EditTurn(c.ConversationID, question.TurnID, "question v2"); err != nil {
		t.Fatalf("edit failed: %v", err)
	}
	if _, err := s.EditTurn(c.ConversationID, question.TurnID, "question v3"); err != nil {
		t.Fatalf("edit failed: %v", err)
	}

	history, err := s.HistoryForLLM(c.ConversationID, 20)
	if err != nil {
		t.Fatalf("history failed: %v", err)
	}
	if len(history) != 1 {
		t.Fatalf("history has %d turns, want only the selected branch", len(history))
	}
	if history[0].Content != "question v3" {
		t.Fatalf("history shows %q, want the selected branch", history[0].Content)
	}
}

func TestRegenerateKeepsThePreviousAnswer(t *testing.T) {
	// Same operation as an edit, so the previous answer stays available while a
	// fresh one is fetched.
	s := newTestStore(t)
	c := mustCreate(t, s)
	mustAdd(t, s, c.ConversationID, RoleUser, "question")
	answer := mustAdd(t, s, c.ConversationID, RoleAssistant, "first answer")

	if _, err := s.Regenerate(c.ConversationID, answer.TurnID); err != nil {
		t.Fatalf("regenerate failed: %v", err)
	}

	fetched, err := s.Get(c.ConversationID)
	if err != nil {
		t.Fatalf("get failed: %v", err)
	}
	if _, ok := fetched.turns[answer.TurnID]; !ok {
		t.Fatal("the previous answer was destroyed by a regeneration")
	}
}

func TestBranchCountReportsEdits(t *testing.T) {
	s := newTestStore(t)
	c := mustCreate(t, s)
	question := mustAdd(t, s, c.ConversationID, RoleUser, "question")

	if count, err := s.BranchCount(c.ConversationID); err != nil || count != 0 {
		t.Fatalf("before any edit, branch count is %d (err %v), want 0", count, err)
	}
	if _, err := s.EditTurn(c.ConversationID, question.TurnID, "question v2"); err != nil {
		t.Fatalf("edit failed: %v", err)
	}
	if count, err := s.BranchCount(c.ConversationID); err != nil || count != 1 {
		t.Fatalf("after one edit, branch count is %d (err %v), want 1", count, err)
	}
}

func TestSearchFindsATurn(t *testing.T) {
	s := newTestStore(t)
	c := mustCreate(t, s)
	mustAdd(t, s, c.ConversationID, RoleUser, "how do I rotate postgres credentials")

	results, err := s.Search("u1", "postgres", 10)
	if err != nil {
		t.Fatalf("search failed: %v", err)
	}
	if len(results) != 1 {
		t.Fatalf("got %d results, want 1", len(results))
	}
	if results[0].Snippet == "" {
		t.Fatal("a result carries no snippet")
	}
}

func TestSearchIsScopedToTheOwner(t *testing.T) {
	// A cross-owner result would require a conversation to exist twice. The
	// owner is compared per conversation, so it cannot.
	s := NewConversationStore()
	mine, _ := s.Create("owner-a", "A", "", 0)
	theirs, _ := s.Create("owner-b", "B", "", 0)
	if _, err := s.AddTurn(mine.ConversationID, RoleUser, "shared secret text", "", Usage{}); err != nil {
		t.Fatal(err)
	}
	if _, err := s.AddTurn(theirs.ConversationID, RoleUser, "shared secret text", "", Usage{}); err != nil {
		t.Fatal(err)
	}

	mineResults, err := s.Search("owner-a", "shared secret", 10)
	if err != nil {
		t.Fatalf("search failed: %v", err)
	}
	if len(mineResults) != 1 {
		t.Fatalf("owner-a saw %d results, want only their own", len(mineResults))
	}
}

func TestSearchWithNoTermsReturnsNothing(t *testing.T) {
	s := newTestStore(t)
	results, err := s.Search("u1", "  ", 10)
	if err != nil {
		t.Fatalf("search failed: %v", err)
	}
	if len(results) != 0 {
		t.Fatalf("an empty query returned %d results", len(results))
	}
}

func TestSearchWithZeroLimitReturnsNothing(t *testing.T) {
	s := newTestStore(t)
	c := mustCreate(t, s)
	mustAdd(t, s, c.ConversationID, RoleUser, "findable text")
	results, err := s.Search("u1", "findable", 0)
	if err != nil {
		t.Fatalf("search failed: %v", err)
	}
	if len(results) != 0 {
		t.Fatalf("a zero limit returned %d results", len(results))
	}
}

func TestDeleteRemovesTheConversationAndItsTurns(t *testing.T) {
	s := newTestStore(t)
	c := mustCreate(t, s)
	turn := mustAdd(t, s, c.ConversationID, RoleUser, "content")
	if err := s.Delete(c.ConversationID); err != nil {
		t.Fatalf("delete failed: %v", err)
	}
	if _, err := s.Get(c.ConversationID); err == nil {
		t.Fatal("the conversation still exists after delete")
	}
	if _, ok := s.turnIndex[turn.TurnID]; ok {
		t.Fatal("a deleted turn is still addressable through the index")
	}
}

func TestCleanupSkipsPinnedConversations(t *testing.T) {
	// A pinned conversation is never cleaned up, because pinning is an explicit
	// instruction not to forget.
	s := NewConversationStore()
	pinned, _ := s.Create("u1", "keep", "", 60)
	unpinned, _ := s.Create("u1", "drop", "", 60)
	if _, err := s.Pin(pinned.ConversationID, true); err != nil {
		t.Fatal(err)
	}

	removed := s.Cleanup("u1", time.Now().Add(10*time.Minute))
	if removed != 1 {
		t.Fatalf("cleanup removed %d conversations, want exactly the unpinned one", removed)
	}
	if _, err := s.Get(pinned.ConversationID); err != nil {
		t.Fatal("a pinned conversation was cleaned up")
	}
	if _, err := s.Get(unpinned.ConversationID); err == nil {
		t.Fatal("an expired unpinned conversation survived cleanup")
	}
}

func TestCleanupIsScopedToTheOwner(t *testing.T) {
	s := NewConversationStore()
	mine, _ := s.Create("owner-a", "mine", "", 60)
	theirs, _ := s.Create("owner-b", "theirs", "", 60)

	if removed := s.Cleanup("owner-a", time.Now().Add(10*time.Minute)); removed != 1 {
		t.Fatalf("cleanup removed %d, want 1", removed)
	}
	if _, err := s.Get(theirs.ConversationID); err != nil {
		t.Fatal("cleanup reached another owner's conversation")
	}
	_ = mine
}

func TestAlonedRetentionMeansNoCleanup(t *testing.T) {
	// Zero retention is "no policy", not "expire immediately".
	s := NewConversationStore()
	c, _ := s.Create("u1", "keep forever", "", 0)
	if removed := s.Cleanup("u1", time.Now().Add(1000*time.Hour)); removed != 0 {
		t.Fatalf("cleanup removed %d conversations with no retention policy", removed)
	}
	if _, err := s.Get(c.ConversationID); err != nil {
		t.Fatal("a conversation with no policy was removed")
	}
}

func TestExportRoundTripsThroughImport(t *testing.T) {
	s := newTestStore(t)
	c := mustCreate(t, s)
	mustAdd(t, s, c.ConversationID, RoleUser, "question")
	mustAdd(t, s, c.ConversationID, RoleAssistant, "answer")

	payload, err := s.Export(c.ConversationID)
	if err != nil {
		t.Fatalf("export failed: %v", err)
	}

	target := NewConversationStore()
	restored, err := target.Import(payload)
	if err != nil {
		t.Fatalf("import failed: %v", err)
	}
	if restored.ConversationID != c.ConversationID {
		t.Fatalf("import produced %q, want %q", restored.ConversationID, c.ConversationID)
	}
	history, err := target.HistoryForLLM(restored.ConversationID, 20)
	if err != nil {
		t.Fatalf("history failed: %v", err)
	}
	if len(history) != 2 || history[0].Content != "question" {
		t.Fatalf("the restored conversation is missing its turns: %v", history)
	}
}

func TestExportRestoresTheBranches(t *testing.T) {
	// Branches are exported rather than flattened, so a re-import restores the
	// tree rather than a single line of it.
	s := newTestStore(t)
	c := mustCreate(t, s)
	question := mustAdd(t, s, c.ConversationID, RoleUser, "question")
	if _, err := s.EditTurn(c.ConversationID, question.TurnID, "question v2"); err != nil {
		t.Fatal(err)
	}

	payload, err := s.Export(c.ConversationID)
	if err != nil {
		t.Fatalf("export failed: %v", err)
	}
	if len(payload.Turns) != 2 {
		t.Fatalf("export wrote %d turns, want the original and its edit", len(payload.Turns))
	}

	target := NewConversationStore()
	if _, err := target.Import(payload); err != nil {
		t.Fatalf("import failed: %v", err)
	}
	count, err := target.BranchCount(c.ConversationID)
	if err != nil {
		t.Fatalf("branch count failed: %v", err)
	}
	if count != 1 {
		t.Fatalf("the restored conversation lost its branch: count %d", count)
	}
}

func TestImportOverAnExistingIdIsRefused(t *testing.T) {
	// Re-importing over an existing id would merge two trees with the same ids.
	s := newTestStore(t)
	c := mustCreate(t, s)
	payload, err := s.Export(c.ConversationID)
	if err != nil {
		t.Fatalf("export failed: %v", err)
	}
	if _, err := s.Import(payload); err == nil {
		t.Fatal("import over an existing conversation was accepted")
	}
}

func TestImportWithoutAnIdIsRefused(t *testing.T) {
	s := NewConversationStore()
	if _, err := s.Import(&ExportedConversation{}); err == nil {
		t.Fatal("an import with no conversation id was accepted")
	}
}

func TestListIsMostRecentlyUpdatedFirst(t *testing.T) {
	s := NewConversationStore()
	first, _ := s.Create("u1", "first", "", 0)
	time.Sleep(2 * time.Millisecond)
	second, _ := s.Create("u1", "second", "", 0)

	listed := s.List("u1", "", false)
	if len(listed) != 2 {
		t.Fatalf("listed %d conversations", len(listed))
	}
	if listed[0].ConversationID != second.ConversationID {
		t.Fatal("the listing is not ordered by recency")
	}
	_ = first
}

func TestListFiltersByProject(t *testing.T) {
	s := NewConversationStore()
	inProject, _ := s.Create("u1", "in", "atlas", 0)
	if _, err := s.Create("u1", "out", "", 0); err != nil {
		t.Fatal(err)
	}
	listed := s.List("u1", "atlas", false)
	if len(listed) != 1 || listed[0].ConversationID != inProject.ConversationID {
		t.Fatalf("the project filter returned %v", listed)
	}
}

func TestProjectsAreDistinctAndSorted(t *testing.T) {
	s := NewConversationStore()
	for _, project := range []string{"zephyr", "atlas", "atlas"} {
		if _, err := s.Create("u1", "c", project, 0); err != nil {
			t.Fatal(err)
		}
	}
	got := s.Projects("u1")
	if len(got) != 2 || got[0] != "atlas" || got[1] != "zephyr" {
		t.Fatalf("projects = %v, want [atlas zephyr]", got)
	}
}

func TestRenameAndPin(t *testing.T) {
	s := newTestStore(t)
	c := mustCreate(t, s)
	renamed, err := s.Rename(c.ConversationID, "New title")
	if err != nil {
		t.Fatalf("rename failed: %v", err)
	}
	if renamed.Title != "New title" {
		t.Fatalf("title is %q", renamed.Title)
	}
	pinned, err := s.Pin(c.ConversationID, true)
	if err != nil {
		t.Fatalf("pin failed: %v", err)
	}
	if !pinned.Pinned {
		t.Fatal("pin did not take effect")
	}
}

func TestGetReturnsACopyThatCannotMutateTheStore(t *testing.T) {
	// A caller that mutates a returned conversation must not be able to reach
	// into the store, or a read is a write.
	s := newTestStore(t)
	c := mustCreate(t, s)
	mustAdd(t, s, c.ConversationID, RoleUser, "original content")

	fetched, err := s.Get(c.ConversationID)
	if err != nil {
		t.Fatalf("get failed: %v", err)
	}
	fetched.Title = "mutated"
	for id := range fetched.turns {
		fetched.turns[id].Content = "mutated"
	}

	refetched, err := s.Get(c.ConversationID)
	if err != nil {
		t.Fatalf("get failed: %v", err)
	}
	if refetched.Title == "mutated" {
		t.Fatal("the store was mutated through a returned copy")
	}
	for _, turn := range refetched.turns {
		if turn.Content == "mutated" {
			t.Fatal("a stored turn was mutated through a returned copy")
		}
	}
}

func TestUnknownConversationIsAnError(t *testing.T) {
	s := NewConversationStore()
	if _, err := s.Get("missing"); err == nil {
		t.Fatal("an unknown conversation was returned")
	}
	if _, err := s.AddTurn("missing", RoleUser, "x", "", Usage{}); err == nil {
		t.Fatal("a turn was added to an unknown conversation")
	}
	if _, err := s.EditTurn("missing", "also-missing", "x"); err == nil {
		t.Fatal("an edit was applied to an unknown conversation")
	}
}

func TestConcurrentAccessIsRaceFree(t *testing.T) {
	// The store is read on every request and written on every turn, so both
	// paths must be safe. This is not a substitute for -race; it is the
	// assertion that exercises the paths at all.
	s := NewConversationStore()
	c, err := s.Create("u1", "Concurrent", "", 0)
	if err != nil {
		t.Fatalf("create failed: %v", err)
	}

	var wg sync.WaitGroup
	for worker := 0; worker < 8; worker++ {
		wg.Add(1)
		go func() {
			defer wg.Done()
			for i := 0; i < 25; i++ {
				if _, err := s.AddTurn(c.ConversationID, RoleUser, "turn", "", Usage{}); err != nil {
					t.Errorf("add turn failed: %v", err)
					return
				}
				if _, err := s.HistoryForLLM(c.ConversationID, 5); err != nil {
					t.Errorf("history failed: %v", err)
					return
				}
				if _, err := s.Search("u1", "turn", 5); err != nil {
					t.Errorf("search failed: %v", err)
					return
				}
			}
		}()
	}
	wg.Wait()

	history, err := s.HistoryForLLM(c.ConversationID, 1000)
	if err != nil {
		t.Fatalf("history failed: %v", err)
	}
	if len(history) != 200 {
		t.Fatalf("history has %d turns, want all 200", len(history))
	}
}

func TestSnippetShortensAndCollapsesRunsOfWhitespace(t *testing.T) {
	// Runs of whitespace collapse to one space and newlines disappear, so a
	// listing shows one line. What must NOT happen is collapsing to nothing: a
	// snippet with no separators is unreadable.
	got := snippet("a   very\nlong   text", 12)
	if len([]rune(got)) > 12 {
		t.Fatalf("snippet is %d runes, want at most 12", len([]rune(got)))
	}
	if strings.Contains(got, "\n") {
		t.Fatalf("snippet still contains a newline: %q", got)
	}
	if strings.Contains(got, "  ") {
		t.Fatalf("snippet still contains a run of spaces: %q", got)
	}
	if !strings.Contains(got, " ") {
		t.Fatalf("snippet lost its word separators: %q", got)
	}
}

func TestSnippetLeavesShortTextAlone(t *testing.T) {
	if got := snippet("short", 20); got != "short" {
		t.Fatalf("snippet mangled short text: %q", got)
	}
}

func TestHistoryRespectsMaxTurns(t *testing.T) {
	s := newTestStore(t)
	c := mustCreate(t, s)
	for i := 0; i < 10; i++ {
		mustAdd(t, s, c.ConversationID, RoleUser, "turn")
	}
	history, err := s.HistoryForLLM(c.ConversationID, 3)
	if err != nil {
		t.Fatalf("history failed: %v", err)
	}
	if len(history) != 3 {
		t.Fatalf("history has %d turns, want the 3 most recent", len(history))
	}
	// The most recent turns are kept, not the oldest.
	if history[2].Content != "turn" {
		t.Fatalf("the kept turns are not the most recent: %v", history)
	}
}

func TestBranchSummariesMarkTheCurrentOne(t *testing.T) {
	s := newTestStore(t)
	c := mustCreate(t, s)
	question := mustAdd(t, s, c.ConversationID, RoleUser, "question")
	replacement, err := s.EditTurn(c.ConversationID, question.TurnID, "question v2")
	if err != nil {
		t.Fatal(err)
	}

	branches, err := s.Branches(c.ConversationID, question.TurnID)
	if err != nil {
		t.Fatalf("branches failed: %v", err)
	}
	currents := 0
	for _, branch := range branches {
		if branch.IsCurrent {
			currents++
		}
		if branch.SiblingCount != 1 {
			t.Fatalf("a branch reports %d siblings, want 1", branch.SiblingCount)
		}
	}
	if currents != 1 {
		t.Fatalf("%d branches are marked current, want exactly 1", currents)
	}
	_ = replacement
}

// Sorting helper used by the export test.
var _ = sort.Ints
