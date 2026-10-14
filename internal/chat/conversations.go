package chat

import (
	"crypto/rand"
	"encoding/hex"
	"fmt"
	"regexp"
	"sort"
	"strings"
	"sync"
	"time"
)

// ---------------------------------------------------------------------------
// Conversations
// ---------------------------------------------------------------------------

// A conversation is a tree of turns with a head pointer per role, not a list.
//
// The shape is the design decision. If a turn were a slot in a list, editing it
// would overwrite the turn the user had, and going back to it would be
// impossible. Making a turn point at the turn it replaced means an edit creates
// a child and the old branch stays reachable, so the caller moves between edits
// by selecting a head rather than by hoping nothing was lost.
//
// Regeneration is the same operation with a provider in the loop: the new answer
// is a sibling branch rather than a replacement, so the previous one survives
// while a fresh one is fetched.

// Role is declared in chat.go as the four roles the protocol supports; a system
// message is built by the assembler and never accepted from a caller verbatim.
// A Turn reuses it rather than declaring a parallel type, because two Role
// definitions would let a conversation hold a role a request cannot carry.

// Turn is one message in a conversation.
type Turn struct {
	TurnID         string    `json:"turn_id"`
	ConversationID string    `json:"conversation_id"`
	Role           Role      `json:"role"`
	Content        string    `json:"content"`
	CreatedAt      time.Time `json:"created_at"`
	// ParentID is what makes branching possible: a turn points at the turn it
	// followed, so the alternative an edit replaced stays reachable.
	ParentID string `json:"parent_id,omitempty"`
	// BranchedFrom records which turn this was an edit of, so the chain of edits
	// is a chain rather than something reconstructed from ordering.
	BranchedFrom string `json:"branched_from,omitempty"`
	// BranchLabel names the branch, so a user with several can tell them apart
	// without opening each.
	BranchLabel string `json:"branch_label,omitempty"`
	// Model is what produced an assistant turn.
	Model string `json:"model,omitempty"`
	// Usage is what the provider reported, so a caller can meter a specific turn
	// rather than the conversation.
	Usage Usage `json:"usage,omitempty"`
	// Pinned turns survive a cleanup, because a user pinning a message is an
	// explicit instruction not to forget it.
	Pinned bool `json:"pinned"`
}

// Conversation is one conversation.
type Conversation struct {
	ConversationID string    `json:"conversation_id"`
	Owner          string    `json:"owner"`
	Title          string    `json:"title"`
	CreatedAt      time.Time `json:"created_at"`
	UpdatedAt      time.Time `json:"updated_at"`
	// Pinned conversations survive a cleanup.
	Pinned bool `json:"pinned"`
	// Project groups conversations, and is what shared instructions and files
	// attach to.
	Project string `json:"project,omitempty"`
	// HeadID is the caller's current position, which is what selects a branch.
	HeadID string `json:"head_id,omitempty"`
	// HeadRole lets a caller move the head without losing the assistant's own
	// position, so regenerating an answer does not hide the question.
	HeadRole Role `json:"head_role"`
	// RetentionSeconds, when set, is how long this conversation lives before an
	// automated cleanup. Zero means no policy.
	RetentionSeconds float64 `json:"retention_seconds,omitempty"`

	turns map[string]*Turn
	mu    sync.RWMutex
}

// IsExpired reports whether this conversation is past its retention window.
//
// A pinned conversation is never expired: pinning is an explicit instruction not
// to forget, so cleaning one up silently discards the one thing the user asked
// to keep.
func (c *Conversation) IsExpired(now time.Time) bool {
	if c.Pinned || c.RetentionSeconds <= 0 {
		return false
	}
	return now.Sub(c.UpdatedAt).Seconds() > c.RetentionSeconds
}

// ConversationNotFound is returned for an unknown conversation.
type ConversationNotFound struct{ ID string }

func (e ConversationNotFound) Error() string {
	return fmt.Sprintf("conversation %q not found", e.ID)
}

// TurnNotFound is returned for an unknown turn.
type TurnNotFound struct{ ID string }

func (e TurnNotFound) Error() string {
	return fmt.Sprintf("turn %q not found", e.ID)
}

// ---------------------------------------------------------------------------
// Store
// ---------------------------------------------------------------------------

// ConversationStore holds conversations, scoped to one owner each.
//
// Per owner rather than per tenant, because a conversation is the user's own and
// a workspace-wide store would show one member's history to another.
type ConversationStore struct {
	conversations map[string]*Conversation
	turnIndex     map[string]*Turn
	mu            sync.RWMutex
}

// NewConversationStore returns an empty store.
func NewConversationStore() *ConversationStore {
	return &ConversationStore{
		conversations: map[string]*Conversation{},
		turnIndex:     map[string]*Turn{},
	}
}

func newID(prefix string) string {
	buf := make([]byte, 12)
	if _, err := rand.Read(buf); err != nil {
		// A weak id is better than no id: the alternative is a panic in a
		// request handler, and a collision is caught by the duplicate check.
		return fmt.Sprintf("%s_%d", prefix, time.Now().UnixNano())
	}
	return prefix + "_" + hex.EncodeToString(buf)
}

// Create starts a conversation.
func (s *ConversationStore) Create(
	owner, title, project string,
	retentionSeconds float64,
) (*Conversation, error) {
	now := time.Now().UTC()
	conversation := &Conversation{
		ConversationID:   newID("conv"),
		Owner:            owner,
		Title:            title,
		CreatedAt:        now,
		UpdatedAt:        now,
		Project:          project,
		HeadRole:         RoleAssistant,
		RetentionSeconds: retentionSeconds,
		turns:            map[string]*Turn{},
	}

	s.mu.Lock()
	defer s.mu.Unlock()
	if _, exists := s.conversations[conversation.ConversationID]; exists {
		return nil, fmt.Errorf("conversation id collision: %s", conversation.ConversationID)
	}
	s.conversations[conversation.ConversationID] = conversation
	return conversation.cloneLocked(), nil
}

// Get returns a conversation, with its turns loaded.
func (s *ConversationStore) Get(conversationID string) (*Conversation, error) {
	s.mu.RLock()
	defer s.mu.RUnlock()
	conversation, ok := s.conversations[conversationID]
	if !ok {
		return nil, ConversationNotFound{ID: conversationID}
	}
	return conversation.cloneLocked(), nil
}

// AddTurn appends a turn and moves the head to it, so the caller's view follows
// the conversation without them having to ask.
func (s *ConversationStore) AddTurn(
	conversationID string,
	role Role,
	content string,
	model string,
	usage Usage,
) (*Turn, error) {
	s.mu.Lock()
	defer s.mu.Unlock()
	conversation, ok := s.conversations[conversationID]
	if !ok {
		return nil, ConversationNotFound{ID: conversationID}
	}

	now := time.Now().UTC()
	turn := &Turn{
		TurnID:         newID("turn"),
		ConversationID: conversationID,
		Role:           role,
		Content:        content,
		CreatedAt:      now,
		ParentID:       conversation.HeadID,
		Model:          model,
		Usage:          usage,
	}
	conversation.turns[turn.TurnID] = turn
	s.turnIndex[turn.TurnID] = turn
	conversation.HeadID = turn.TurnID
	conversation.HeadRole = role
	conversation.UpdatedAt = now

	copied := *turn
	return &copied, nil
}

// SelectHead moves the head to an existing turn, which is how a caller views a
// different branch without deleting anything.
func (s *ConversationStore) SelectHead(conversationID, turnID string) (*Turn, error) {
	s.mu.Lock()
	defer s.mu.Unlock()
	conversation, ok := s.conversations[conversationID]
	if !ok {
		return nil, ConversationNotFound{ID: conversationID}
	}
	turn, ok := conversation.turns[turnID]
	if !ok {
		return nil, TurnNotFound{ID: turnID}
	}
	conversation.HeadID = turn.TurnID
	conversation.HeadRole = turn.Role
	copied := *turn
	return &copied, nil
}

// EditTurn replaces a turn's content without losing the original.
//
// The replacement is built directly rather than through AddTurn, because AddTurn
// attaches under the current head - which would place an edit of the first turn
// underneath the reply that followed it rather than beside the turn it replaced.
func (s *ConversationStore) EditTurn(conversationID, turnID, content string) (*Turn, error) {
	s.mu.Lock()
	defer s.mu.Unlock()
	conversation, ok := s.conversations[conversationID]
	if !ok {
		return nil, ConversationNotFound{ID: conversationID}
	}
	original, ok := conversation.turns[turnID]
	if !ok {
		return nil, TurnNotFound{ID: turnID}
	}

	now := time.Now().UTC()
	replacement := &Turn{
		TurnID:         newID("turn"),
		ConversationID: conversationID,
		Role:           original.Role,
		Content:        content,
		CreatedAt:      now,
		// The original's parent, explicitly, including the empty string for a
		// root turn. Attaching under the head here is the bug this avoids.
		ParentID:     original.ParentID,
		BranchedFrom: original.TurnID,
		BranchLabel:  fmt.Sprintf("edit of %s", snippet(original.Content, 24)),
		Model:        original.Model,
		Usage:        original.Usage,
		Pinned:       original.Pinned,
	}
	if original.BranchLabel != "" {
		replacement.BranchLabel = original.BranchLabel
	}

	conversation.turns[replacement.TurnID] = replacement
	s.turnIndex[replacement.TurnID] = replacement
	conversation.HeadID = replacement.TurnID
	conversation.HeadRole = replacement.Role
	conversation.UpdatedAt = now

	copied := *replacement
	return &copied, nil
}

// Regenerate marks an assistant turn as needing regeneration.
//
// Same operation as an edit, with the provider in the loop: the new turn is a
// sibling branch rather than a replacement, so the previous answer stays
// available while a fresh one is fetched.
func (s *ConversationStore) Regenerate(conversationID, turnID string) (*Turn, error) {
	conversation, err := s.Get(conversationID)
	if err != nil {
		return nil, err
	}
	var original *Turn
	for _, turn := range conversation.turns {
		if turn.TurnID == turnID {
			original = turn
			break
		}
	}
	if original == nil {
		return nil, TurnNotFound{ID: turnID}
	}
	return s.EditTurn(conversationID, turnID, original.Content)
}

// Branches lists the branches that sit beside a turn.
//
// Siblings are the turns with the same parent, which is exactly the set the
// caller moves between when going back to a previous edit.
func (s *ConversationStore) Branches(conversationID, turnID string) ([]BranchSummary, error) {
	s.mu.RLock()
	defer s.mu.RUnlock()
	conversation, ok := s.conversations[conversationID]
	if !ok {
		return nil, ConversationNotFound{ID: conversationID}
	}
	target, ok := conversation.turns[turnID]
	if !ok {
		return nil, TurnNotFound{ID: turnID}
	}

	var siblings []*Turn
	for _, turn := range conversation.turns {
		if turn.ParentID == target.ParentID {
			siblings = append(siblings, turn)
		}
	}
	sort.Slice(siblings, func(i, j int) bool {
		return siblings[i].CreatedAt.Before(siblings[j].CreatedAt)
	})

	out := make([]BranchSummary, 0, len(siblings))
	for _, sibling := range siblings {
		out = append(out, BranchSummary{
			TurnID:       sibling.TurnID,
			Snippet:      snippet(sibling.Content, 80),
			CreatedAt:    sibling.CreatedAt,
			IsCurrent:    sibling.TurnID == turnID,
			SiblingCount: len(siblings) - 1,
			Label:        sibling.BranchLabel,
		})
	}
	return out, nil
}

// BranchCount reports how many alternatives have been branched, across the
// conversation. Zero means nothing has been edited.
func (s *ConversationStore) BranchCount(conversationID string) (int, error) {
	s.mu.RLock()
	defer s.mu.RUnlock()
	conversation, ok := s.conversations[conversationID]
	if !ok {
		return 0, ConversationNotFound{ID: conversationID}
	}
	count := 0
	for _, turn := range conversation.turns {
		if turn.BranchedFrom != "" {
			count++
		}
	}
	return count, nil
}

// HistoryForLLM returns the turns a model should see, in conversation order.
//
// Only the selected branch is included, ordered by creation time. A branch the
// caller did not select would otherwise appear as a parallel line in the prompt,
// so a model would see two versions of the same turn and no way to tell which
// is current.
func (s *ConversationStore) HistoryForLLM(conversationID string, maxTurns int) ([]Turn, error) {
	s.mu.RLock()
	defer s.mu.RUnlock()
	conversation, ok := s.conversations[conversationID]
	if !ok {
		return nil, ConversationNotFound{ID: conversationID}
	}
	if maxTurns <= 0 {
		return nil, nil
	}

	// Walk the parent chain from the head backwards, which is what selects one
	// branch rather than showing the whole tree.
	var chain []*Turn
	seen := map[string]bool{}
	current := conversation.turns[conversation.HeadID]
	for current != nil && !seen[current.TurnID] {
		seen[current.TurnID] = true
		chain = append(chain, current)
		if current.ParentID == "" {
			break
		}
		current = conversation.turns[current.ParentID]
	}
	// Reverse into conversation order.
	for i, j := 0, len(chain)-1; i < j; i, j = i+1, j-1 {
		chain[i], chain[j] = chain[j], chain[i]
	}
	if len(chain) > maxTurns {
		chain = chain[len(chain)-maxTurns:]
	}

	out := make([]Turn, 0, len(chain))
	for _, turn := range chain {
		out = append(out, *turn)
	}
	return out, nil
}

// ---------------------------------------------------------------------------
// Search
// ---------------------------------------------------------------------------

// SearchResult is one match, with enough context to be actionable.
type SearchResult struct {
	ConversationID    string `json:"conversation_id"`
	ConversationTitle string `json:"conversation_title"`
	TurnID            string `json:"turn_id"`
	Role              Role   `json:"role"`
	Snippet           string `json:"snippet"`
	Score             int    `json:"score"`
}

// Search does full-text search over one owner's conversations.
//
// Scoped by construction: the caller's owner is compared per conversation, so a
// cross-owner result would require a conversation to exist twice. A plain scan
// rather than a LIKE query, because a per-identity conversation set is small
// enough that an index is more machinery than the problem needs.
func (s *ConversationStore) Search(owner, query string, limit int) ([]SearchResult, error) {
	if limit <= 0 {
		return nil, nil
	}
	terms := tokenizeForSearch(query)
	if len(terms) == 0 {
		return nil, nil
	}

	s.mu.RLock()
	defer s.mu.RUnlock()

	var results []SearchResult
	for _, conversation := range s.conversations {
		if conversation.Owner != owner {
			continue
		}
		for _, turn := range conversation.turns {
			lowered := strings.ToLower(turn.Content)
			score := 0
			for _, term := range terms {
				if strings.Contains(lowered, term) {
					score++
				}
			}
			if score == 0 {
				continue
			}
			results = append(results, SearchResult{
				ConversationID:    conversation.ConversationID,
				ConversationTitle: conversation.Title,
				TurnID:            turn.TurnID,
				Role:              turn.Role,
				Snippet:           snippet(turn.Content, 80),
				Score:             score,
			})
		}
	}

	sort.Slice(results, func(i, j int) bool {
		if results[i].Score != results[j].Score {
			return results[i].Score > results[j].Score
		}
		return results[i].TurnID < results[j].TurnID
	})
	if len(results) > limit {
		results = results[:limit]
	}
	return results, nil
}

// ---------------------------------------------------------------------------
// Metadata, listing, and lifecycle
// ---------------------------------------------------------------------------

// Rename changes the title.
func (s *ConversationStore) Rename(conversationID, title string) (*Conversation, error) {
	return s.updateMeta(conversationID, func(c *Conversation) {
		c.Title = title
	})
}

// Pin toggles the pinned flag, which is what keeps a conversation out of a
// automated cleanup.
func (s *ConversationStore) Pin(conversationID string, pinned bool) (*Conversation, error) {
	return s.updateMeta(conversationID, func(c *Conversation) {
		c.Pinned = pinned
	})
}

// SetProject moves a conversation into a project.
func (s *ConversationStore) SetProject(conversationID, project string) (*Conversation, error) {
	return s.updateMeta(conversationID, func(c *Conversation) {
		c.Project = project
	})
}

func (s *ConversationStore) updateMeta(
	conversationID string,
	mutate func(*Conversation),
) (*Conversation, error) {
	s.mu.Lock()
	defer s.mu.Unlock()
	conversation, ok := s.conversations[conversationID]
	if !ok {
		return nil, ConversationNotFound{ID: conversationID}
	}
	mutate(conversation)
	conversation.UpdatedAt = time.Now().UTC()
	return conversation.cloneLocked(), nil
}

// List returns one owner's conversations, most recently updated first.
func (s *ConversationStore) List(
	owner string,
	project string,
	includeExpired bool,
) []*Conversation {
	s.mu.RLock()
	defer s.mu.RUnlock()

	now := time.Now().UTC()
	var out []*Conversation
	for _, conversation := range s.conversations {
		if conversation.Owner != owner {
			continue
		}
		if !includeExpired && conversation.IsExpired(now) {
			continue
		}
		if project != "" && conversation.Project != project {
			continue
		}
		out = append(out, conversation.cloneLocked())
	}
	sort.Slice(out, func(i, j int) bool {
		return out[i].UpdatedAt.After(out[j].UpdatedAt)
	})
	return out
}

// Projects returns the distinct project names this owner uses.
func (s *ConversationStore) Projects(owner string) []string {
	s.mu.RLock()
	defer s.mu.RUnlock()
	seen := map[string]bool{}
	for _, conversation := range s.conversations {
		if conversation.Owner == owner && conversation.Project != "" {
			seen[conversation.Project] = true
		}
	}
	out := make([]string, 0, len(seen))
	for project := range seen {
		out = append(out, project)
	}
	sort.Strings(out)
	return out
}

// Delete removes a conversation and every turn in it.
func (s *ConversationStore) Delete(conversationID string) error {
	s.mu.Lock()
	defer s.mu.Unlock()
	conversation, ok := s.conversations[conversationID]
	if !ok {
		return ConversationNotFound{ID: conversationID}
	}
	for turnID := range conversation.turns {
		delete(s.turnIndex, turnID)
	}
	delete(s.conversations, conversationID)
	return nil
}

// Cleanup removes conversations past their retention, skipping pinned ones.
//
// A pinned conversation is never cleaned up, because pinning is an explicit
// instruction not to forget.
func (s *ConversationStore) Cleanup(owner string, now time.Time) int {
	s.mu.Lock()
	defer s.mu.Unlock()
	removed := 0
	for id, conversation := range s.conversations {
		if owner != "" && conversation.Owner != owner {
			continue
		}
		if !conversation.IsExpired(now) {
			continue
		}
		for turnID := range conversation.turns {
			delete(s.turnIndex, turnID)
		}
		delete(s.conversations, id)
		removed++
	}
	return removed
}

// ---------------------------------------------------------------------------
// Export and import
// ---------------------------------------------------------------------------

// ExportedConversation is a conversation as plain data.
//
// Branches are exported rather than flattened, so a re-import restores the tree
// the caller left rather than a single line of it. Dropping them would make an
// export/import cycle a lossy one.
type ExportedConversation struct {
	ConversationID   string    `json:"conversation_id"`
	Owner            string    `json:"owner"`
	Title            string    `json:"title"`
	CreatedAt        time.Time `json:"created_at"`
	UpdatedAt        time.Time `json:"updated_at"`
	Pinned           bool      `json:"pinned"`
	Project          string    `json:"project,omitempty"`
	RetentionSeconds float64   `json:"retention_seconds,omitempty"`
	HeadID           string    `json:"head_id,omitempty"`
	HeadRole         Role      `json:"head_role"`
	Turns            []Turn    `json:"turns"`
}

// Export returns a conversation as plain data, including branched turns.
func (s *ConversationStore) Export(conversationID string) (*ExportedConversation, error) {
	s.mu.RLock()
	defer s.mu.RUnlock()
	conversation, ok := s.conversations[conversationID]
	if !ok {
		return nil, ConversationNotFound{ID: conversationID}
	}

	turns := make([]Turn, 0, len(conversation.turns))
	for _, turn := range conversation.turns {
		turns = append(turns, *turn)
	}
	sort.Slice(turns, func(i, j int) bool {
		return turns[i].CreatedAt.Before(turns[j].CreatedAt)
	})

	return &ExportedConversation{
		ConversationID:   conversation.ConversationID,
		Owner:            conversation.Owner,
		Title:            conversation.Title,
		CreatedAt:        conversation.CreatedAt,
		UpdatedAt:        conversation.UpdatedAt,
		Pinned:           conversation.Pinned,
		Project:          conversation.Project,
		RetentionSeconds: conversation.RetentionSeconds,
		HeadID:           conversation.HeadID,
		HeadRole:         conversation.HeadRole,
		Turns:            turns,
	}, nil
}

// Import restores an exported conversation, including its tree and head, so a
// re-imported conversation looks like the one that was exported rather than like
// a fresh one with the same messages.
func (s *ConversationStore) Import(payload *ExportedConversation) (*Conversation, error) {
	if payload.ConversationID == "" {
		return nil, fmt.Errorf("import: conversation_id is required")
	}
	s.mu.Lock()
	defer s.mu.Unlock()
	if _, exists := s.conversations[payload.ConversationID]; exists {
		// Re-importing over an existing id would merge two trees with the same
		// ids, so it is refused rather than attempted.
		return nil, fmt.Errorf("import: conversation %q already exists", payload.ConversationID)
	}

	now := time.Now().UTC()
	conversation := &Conversation{
		ConversationID:   payload.ConversationID,
		Owner:            payload.Owner,
		Title:            payload.Title,
		CreatedAt:        payload.CreatedAt,
		UpdatedAt:        payload.UpdatedAt,
		Pinned:           payload.Pinned,
		Project:          payload.Project,
		RetentionSeconds: payload.RetentionSeconds,
		HeadID:           payload.HeadID,
		HeadRole:         payload.HeadRole,
		turns:            make(map[string]*Turn, len(payload.Turns)),
	}
	if conversation.CreatedAt.IsZero() {
		conversation.CreatedAt = now
	}
	if conversation.UpdatedAt.IsZero() {
		conversation.UpdatedAt = now
	}
	if conversation.HeadRole == "" {
		conversation.HeadRole = RoleAssistant
	}

	for i := range payload.Turns {
		turn := payload.Turns[i]
		if turn.TurnID == "" {
			return nil, fmt.Errorf("import: turn %d has no turn_id", i)
		}
		turn.ConversationID = conversation.ConversationID
		conversation.turns[turn.TurnID] = &turn
		s.turnIndex[turn.TurnID] = &turn
	}
	s.conversations[conversation.ConversationID] = conversation
	return conversation.cloneLocked(), nil
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

// cloneLocked copies a conversation and its turns.
//
// Called with the store's lock held. The copy is a fresh struct with a fresh
// mutex, not `out := *c`: copying a struct with an embedded sync.RWMutex
// copies the lock, which `go vet` rejects and which would hand out a
// conversation whose lock is aliased to the store's. The turns are pointers to
// copies so a caller mutating one cannot reach into the store.
func (c *Conversation) cloneLocked() *Conversation {
	out := &Conversation{
		ConversationID:   c.ConversationID,
		Owner:            c.Owner,
		Title:            c.Title,
		CreatedAt:        c.CreatedAt,
		UpdatedAt:        c.UpdatedAt,
		Pinned:           c.Pinned,
		Project:          c.Project,
		HeadID:           c.HeadID,
		HeadRole:         c.HeadRole,
		RetentionSeconds: c.RetentionSeconds,
		turns:            make(map[string]*Turn, len(c.turns)),
	}
	for id, turn := range c.turns {
		copied := *turn
		out.turns[id] = &copied
	}
	return out
}

// snippet renders a turn's content on one line, truncated.
//
// Used for listings and search results, where a caller needs to tell one match
// from another without opening each.
func snippet(text string, width int) string {
	text = whitespace.ReplaceAllString(text, " ")
	text = strings.TrimSpace(text)
	if len(text) <= width {
		return text
	}
	return text[:width-1] + "…"
}

var whitespace = regexp.MustCompile(`\s+`)

// tokenizeForSearch splits a query into search terms.
//
// Terms shorter than two characters are dropped: they match nearly everything and
// so contribute no ranking signal, only noise.
func tokenizeForSearch(query string) []string {
	fields := whitespace.Split(strings.ToLower(query), -1)
	out := make([]string, 0, len(fields))
	for _, field := range fields {
		if len(field) >= 2 {
			out = append(out, field)
		}
	}
	return out
}

// BranchSummary is one branch, as shown to the caller.
type BranchSummary struct {
	TurnID       string    `json:"turn_id"`
	Snippet      string    `json:"snippet"`
	CreatedAt    time.Time `json:"created_at"`
	IsCurrent    bool      `json:"is_current"`
	SiblingCount int       `json:"sibling_count"`
	Label        string    `json:"label,omitempty"`
}
