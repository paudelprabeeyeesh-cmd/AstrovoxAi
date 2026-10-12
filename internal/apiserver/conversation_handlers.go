package apiserver

import (
	"net/http"
	"strings"

	apperrors "github.com/astrovox/astrovox/internal/errors"

	"github.com/astrovox/astrovox/internal/auth"
	"github.com/astrovox/astrovox/internal/conversations"
	"github.com/astrovox/astrovox/internal/httpapi"
)

// ---- Handlers -------------------------------------------------------------

func (s *Server) createConversation(c *httpapi.Context) error {
	sub := subject(c)
	if sub == "" {
		return apperrors.New(apperrors.CodePermissionDenied, "authentication required")
	}
	var in struct {
		Title string `json:"title"`
	}
	if err := c.Bind(&in); err != nil {
		return err
	}
	if strings.TrimSpace(in.Title) == "" {
		return apperrors.New(apperrors.CodeInvalidArgument, "title is required")
	}
	conv := s.chats.Create(sub, strings.TrimSpace(in.Title))
	return httpapi.Respond(c, http.StatusCreated, map[string]interface{}{"conversation": conv})
}

func (s *Server) listConversations(c *httpapi.Context) error {
	sub := subject(c)
	if sub == "" {
		return apperrors.New(apperrors.CodePermissionDenied, "authentication required")
	}
	return httpapi.Respond(c, http.StatusOK, map[string]interface{}{
		"conversations": s.chats.List(sub),
	})
}

func (s *Server) getConversation(c *httpapi.Context) error {
	sub := subject(c)
	if sub == "" {
		return apperrors.New(apperrors.CodePermissionDenied, "authentication required")
	}
	conv := s.chats.Get(sub, c.Params["id"])
	if conv == nil {
		// A missing conversation and someone else's conversation are the
		// same answer, so existence is not disclosed across tenants.
		return apperrors.New(apperrors.CodeNotFound, "conversation not found")
	}
	includeSuperseded := c.Query("include_superseded", "") == "true"
	messages := s.chats.Messages(sub, c.Params["id"], includeSuperseded)
	return httpapi.Respond(c, http.StatusOK, map[string]interface{}{
		"conversation": conv,
		"messages":     messages,
	})
}

func (s *Server) renameConversation(c *httpapi.Context) error {
	sub := subject(c)
	if sub == "" {
		return apperrors.New(apperrors.CodePermissionDenied, "authentication required")
	}
	var in struct {
		Title string `json:"title"`
	}
	if err := c.Bind(&in); err != nil {
		return err
	}
	if strings.TrimSpace(in.Title) == "" {
		return apperrors.New(apperrors.CodeInvalidArgument, "title is required")
	}
	if !s.chats.Rename(sub, c.Params["id"], strings.TrimSpace(in.Title)) {
		return apperrors.New(apperrors.CodeNotFound, "conversation not found")
	}
	return httpapi.Respond(c, http.StatusOK, map[string]interface{}{"renamed": c.Params["id"]})
}

func (s *Server) deleteConversation(c *httpapi.Context) error {
	sub := subject(c)
	if sub == "" {
		return apperrors.New(apperrors.CodePermissionDenied, "authentication required")
	}
	if !s.chats.Delete(sub, c.Params["id"]) {
		return apperrors.New(apperrors.CodeNotFound, "conversation not found")
	}
	return httpapi.Respond(c, http.StatusOK, map[string]interface{}{"deleted": c.Params["id"]})
}

func (s *Server) addMessage(c *httpapi.Context) error {
	sub := subject(c)
	if sub == "" {
		return apperrors.New(apperrors.CodePermissionDenied, "authentication required")
	}
	var in struct {
		ParentID string `json:"parent_id,omitempty"`
		Role     string `json:"role"`
		Content  string `json:"content"`
	}
	if err := c.Bind(&in); err != nil {
		return err
	}
	if strings.TrimSpace(in.Content) == "" {
		return apperrors.New(apperrors.CodeInvalidArgument, "content is required")
	}
	role := conversations.Role(in.Role)
	switch role {
	case conversations.RoleUser, conversations.RoleAssistant, conversations.RoleTool, conversations.RoleSystem:
	default:
		// An unknown role is refused rather than coerced: the role is part of
		// the assembled prompt, and a value the model did not expect produces
		// a silent quality failure.
		return apperrors.New(apperrors.CodeInvalidArgument, "unknown role")
	}
	m := s.chats.AddMessage(sub, c.Params["id"], in.ParentID, role, in.Content, "")
	if m == nil {
		return apperrors.New(apperrors.CodeNotFound, "conversation not found")
	}
	return httpapi.Respond(c, http.StatusCreated, map[string]interface{}{"message": m})
}

func (s *Server) chatStats(c *httpapi.Context) error {
	return httpapi.Respond(c, http.StatusOK, map[string]interface{}{"stats": s.chats.Stats()})
}

// ---- Wiring ---------------------------------------------------------------

// attachConversations registers the conversation routes. It takes the store
// as a parameter so a caller can supply a store it also inspects, which is
// what the tests do.
func (s *Server) attachConversations(store *conversations.Store) error {
	if store == nil {
		return apperrors.New(apperrors.CodeInvalidArgument, "a conversation store is required")
	}
	s.chats = store
	s.router.Handle(http.MethodPost, "/conversations", s.RequireAuth(s.createConversation))
	s.router.Handle(http.MethodGet, "/conversations", s.RequireAuth(s.listConversations))
	s.router.Handle(http.MethodGet, "/conversations/{id}", s.RequireAuth(s.getConversation))
	s.router.Handle(http.MethodPatch, "/conversations/{id}", s.RequireAuth(s.renameConversation))
	s.router.Handle(http.MethodDelete, "/conversations/{id}", s.RequireAuth(s.deleteConversation))
	s.router.Handle(http.MethodPost, "/conversations/{id}/messages", s.RequireAuth(s.addMessage))
	s.router.Handle(http.MethodGet, "/conversations/stats", s.chatStats)
	return nil
}

var _ = auth.Claims{}
