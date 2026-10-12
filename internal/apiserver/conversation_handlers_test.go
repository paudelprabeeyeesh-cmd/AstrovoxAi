package apiserver

import (
	"encoding/json"
	"fmt"
	"net/http"
	"strings"
	"testing"
)

// newConv creates a conversation and returns its id, decoded from the
// envelope.
func newConv(t *testing.T, s *Server, token, title string) string {
	t.Helper()
	rec := call(t, s, "POST", "/conversations", fmt.Sprintf(`{"title":%q}`, title), token)
	if rec.Code != http.StatusCreated {
		t.Fatalf("create status = %d, want 201: %s", rec.Code, rec.Body.String())
	}
	var body struct {
		Data struct {
			Conversation struct {
				ID string `json:"id"`
			} `json:"conversation"`
		} `json:"data"`
	}
	if err := json.Unmarshal(rec.Body.Bytes(), &body); err != nil {
		t.Fatalf("response is not JSON: %v", err)
	}
	if body.Data.Conversation.ID == "" {
		t.Fatal("no conversation id in the response")
	}
	return body.Data.Conversation.ID
}

// ---- Auth ----------------------------------------------------------------

func TestConversationsRequireAToken(t *testing.T) {
	s := newTestServer(t)
	if rec := call(t, s, "GET", "/conversations", "", ""); rec.Code != http.StatusForbidden {
		t.Fatalf("status = %d, want 403", rec.Code)
	}
	if rec := call(t, s, "POST", "/conversations", `{"title":"x"}`, ""); rec.Code != http.StatusForbidden {
		t.Fatalf("status = %d, want 403", rec.Code)
	}
}

func TestCreateRequiresATitle(t *testing.T) {
	s := newTestServer(t)
	token, _ := registerAndToken(t, s)
	if rec := call(t, s, "POST", "/conversations", `{"title":""}`, token); rec.Code != http.StatusBadRequest {
		t.Fatalf("status = %d, want 400 for an empty title", rec.Code)
	}
}

// ---- The core journey ----------------------------------------------------

func TestCreateListGetAndDelete(t *testing.T) {
	s := newTestServer(t)
	token, _ := registerAndToken(t, s)

	id := newConv(t, s, token, "First chat")

	// Get returns the conversation and its (empty) message list.
	rec := call(t, s, "GET", "/conversations/"+id, "", token)
	if rec.Code != http.StatusOK {
		t.Fatalf("get status = %d, want 200: %s", rec.Code, rec.Body.String())
	}

	// List returns exactly one conversation.
	rec = call(t, s, "GET", "/conversations", "", token)
	var list struct {
		Data struct {
			Conversations []struct {
				ID string `json:"id"`
			} `json:"conversations"`
		} `json:"data"`
	}
	if err := json.Unmarshal(rec.Body.Bytes(), &list); err != nil {
		t.Fatalf("list response is not JSON: %v", err)
	}
	if len(list.Data.Conversations) != 1 {
		t.Fatalf("list has %d conversations, want 1", len(list.Data.Conversations))
	}

	// Delete removes it.
	rec = call(t, s, "DELETE", "/conversations/"+id, "", token)
	if rec.Code != http.StatusOK {
		t.Fatalf("delete status = %d, want 200: %s", rec.Code, rec.Body.String())
	}
	if rec = call(t, s, "GET", "/conversations/"+id, "", token); rec.Code != http.StatusNotFound {
		t.Fatalf("after delete, get status = %d, want 404", rec.Code)
	}
}

func TestRename(t *testing.T) {
	s := newTestServer(t)
	token, _ := registerAndToken(t, s)
	id := newConv(t, s, token, "before")

	rec := call(t, s, "PATCH", "/conversations/"+id, `{"title":"after"}`, token)
	if rec.Code != http.StatusOK {
		t.Fatalf("rename status = %d, want 200: %s", rec.Code, rec.Body.String())
	}
	rec = call(t, s, "GET", "/conversations/"+id, "", token)
	var body struct {
		Data struct {
			Conversation struct {
				Title string `json:"title"`
			} `json:"conversation"`
		} `json:"data"`
	}
	_ = json.Unmarshal(rec.Body.Bytes(), &body)
	if body.Data.Conversation.Title != "after" {
		t.Fatalf("title = %q, want after", body.Data.Conversation.Title)
	}
}

func TestAddMessageWithAValidRole(t *testing.T) {
	s := newTestServer(t)
	token, _ := registerAndToken(t, s)
	id := newConv(t, s, token, "chat")

	rec := call(t, s, "POST", "/conversations/"+id+"/messages",
		`{"role":"user","content":"hello"}`, token)
	if rec.Code != http.StatusCreated {
		t.Fatalf("add message status = %d, want 201: %s", rec.Code, rec.Body.String())
	}
}

func TestAddMessageWithAnUnknownRoleIsRefused(t *testing.T) {
	// A coercable role would silently change the assembled prompt.
	s := newTestServer(t)
	token, _ := registerAndToken(t, s)
	id := newConv(t, s, token, "chat")
	rec := call(t, s, "POST", "/conversations/"+id+"/messages",
		`{"role":"overlord","content":"hello"}`, token)
	if rec.Code != http.StatusBadRequest {
		t.Fatalf("status = %d, want 400 for an unknown role", rec.Code)
	}
}

func TestAddMessageRequiresContent(t *testing.T) {
	s := newTestServer(t)
	token, _ := registerAndToken(t, s)
	id := newConv(t, s, token, "chat")
	rec := call(t, s, "POST", "/conversations/"+id+"/messages",
		`{"role":"user","content":""}`, token)
	if rec.Code != http.StatusBadRequest {
		t.Fatalf("status = %d, want 400 for empty content", rec.Code)
	}
}

// ---- Cross-tenant isolation ----------------------------------------------

func TestCrossTenantReadsAreInvisible(t *testing.T) {
	s := newTestServer(t)
	tokA, _ := registerAndToken(t, s)
	tokB, _ := registerAndToken(t, s)
	id := newConv(t, s, tokA, "A's private chat")

	for _, tc := range []struct {
		method, path string
		body         string
	}{
		{"GET", "/conversations/" + id, ""},
		{"PATCH", "/conversations/" + id, `{"title":"hijacked"}`},
		{"DELETE", "/conversations/" + id, ""},
		{"POST", "/conversations/" + id + "/messages", `{"role":"user","content":"injected"}`},
	} {
		rec := call(t, s, tc.method, tc.path, tc.body, tokB)
		// 404, never 403: a 403 would confirm the row exists.
		if rec.Code != http.StatusNotFound {
			t.Fatalf("%s %s as tenant B = %d, want 404 (must not disclose existence)",
				tc.method, tc.path, rec.Code)
		}
	}

	// And the conversation is still intact for its owner.
	if rec := call(t, s, "GET", "/conversations/"+id, "", tokA); rec.Code != http.StatusOK {
		t.Fatalf("after B's attempts, A's conversation reads %d, want 200", rec.Code)
	}
}

func TestCrossTenantMessagesAreInvisible(t *testing.T) {
	s := newTestServer(t)
	tokA, _ := registerAndToken(t, s)
	tokB, _ := registerAndToken(t, s)
	id := newConv(t, s, tokA, "chat")
	call(t, s, "POST", "/conversations/"+id+"/messages", `{"role":"user","content":"A's note"}`, tokA)

	rec := call(t, s, "GET", "/conversations/"+id, "", tokB)
	if strings.Contains(rec.Body.String(), "A's note") {
		t.Fatal("tenant B can read tenant A's messages")
	}
}

func TestCrossTenantListIsEmpty(t *testing.T) {
	s := newTestServer(t)
	tokA, _ := registerAndToken(t, s)
	tokB, _ := registerAndToken(t, s)
	newConv(t, s, tokA, "A's chat")

	rec := call(t, s, "GET", "/conversations", "", tokB)
	var body struct {
		Data struct {
			Conversations []interface{} `json:"conversations"`
		} `json:"data"`
	}
	_ = json.Unmarshal(rec.Body.Bytes(), &body)
	if len(body.Data.Conversations) != 0 {
		t.Fatalf("tenant B's list has %d of A's conversations, want 0",
			len(body.Data.Conversations))
	}
}

// ---- Errors --------------------------------------------------------------

func TestGetOfAMissingConversationIs404(t *testing.T) {
	s := newTestServer(t)
	token, _ := registerAndToken(t, s)
	if rec := call(t, s, "GET", "/conversations/no-such-id", "", token); rec.Code != http.StatusNotFound {
		t.Fatalf("status = %d, want 404", rec.Code)
	}
}

func TestConversationErrorsCarryARequestID(t *testing.T) {
	s := newTestServer(t)
	token, _ := registerAndToken(t, s)
	rec := call(t, s, "GET", "/conversations/absent", "", token)
	if rec.Code != http.StatusNotFound {
		t.Fatalf("status = %d, want 404", rec.Code)
	}
	if rec.Header().Get("X-Request-ID") == "" {
		t.Fatal("no X-Request-ID on a conversation error")
	}
}
