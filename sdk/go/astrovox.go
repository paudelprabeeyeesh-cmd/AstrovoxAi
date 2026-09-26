package astrovox

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"time"
)

type Client struct {
	BaseURL    string
	APIKey     string
	HTTPClient *http.Client
}

type Message struct {
	Role      string `json:"role"`
	Content   string `json:"content"`
	Timestamp string `json:"timestamp,omitempty"`
}

type Conversation struct {
	ID        string     `json:"id"`
	Title     string     `json:"title"`
	Messages  []Message  `json:"messages,omitempty"`
	Model     string     `json:"model"`
	CreatedAt string     `json:"created_at,omitempty"`
}

type WebhookConfig struct {
	URL     string   `json:"url"`
	Secret  string   `json:"secret,omitempty"`
	Events  []string `json:"events"`
	Active  bool     `json:"active"`
}

type RetryPolicy struct {
	MaxRetries       int
	BackoffFactor    float64
	RetryableStatuses []int
}

func NewClient(apiKey string, baseURL string) *Client {
	if baseURL == "" {
		baseURL = "https://api.astrovox.ai/v1"
	}
	return &Client{
		BaseURL: baseURL,
		APIKey:  apiKey,
		HTTPClient: &http.Client{Timeout: 30 * time.Second},
	}
}

func (c *Client) doRequest(method, path string, body interface{}) (*http.Response, error) {
	url := fmt.Sprintf("%s%s", c.BaseURL, path)
	var payload io.Reader
	if body != nil {
		b, _ := json.Marshal(body)
		payload = bytes.NewReader(b)
	}
	req, err := http.NewRequest(method, url, payload)
	if err != nil {
		return nil, err
	}
	req.Header.Set("Authorization", fmt.Sprintf("Bearer %s", c.APIKey))
	req.Header.Set("Content-Type", "application/json")
	return c.HTTPClient.Do(req)
}

func (c *Client) SendMessage(conversationID, message, model string) (map[string]interface{}, error) {
	resp, err := c.doRequest("POST", "/chat/message", map[string]interface{}{
		"conversation_id": conversationID,
		"message":         message,
		"model":           model,
	})
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()
	var out map[string]interface{}
	json.NewDecoder(resp.Body).Decode(&out)
	return out, nil
}

func (c *Client) CreateConversation(title, model string) (Conversation, error) {
	resp, err := c.doRequest("POST", "/conversations", map[string]interface{}{
		"title": title,
		"model": model,
	})
	if err != nil {
		return Conversation{}, err
	}
	defer resp.Body.Close()
	var conv Conversation
	json.NewDecoder(resp.Body).Decode(&conv)
	return conv, nil
}

func (c *Client) ListConversations() ([]Conversation, error) {
	resp, err := c.doRequest("GET", "/conversations", nil)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()
	var convs []Conversation
	json.NewDecoder(resp.Body).Decode(&convs)
	return convs, nil
}

func (c *Client) CreateWebhook(config WebhookConfig) (map[string]interface{}, error) {
	resp, err := c.doRequest("POST", "/webhooks", config)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()
	var out map[string]interface{}
	json.NewDecoder(resp.Body).Decode(&out)
	return out, nil
}

func (c *Client) HealthCheck() (map[string]interface{}, error) {
	resp, err := c.doRequest("GET", "/health", nil)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()
	var out map[string]interface{}
	json.NewDecoder(resp.Body).Decode(&out)
	return out, nil
}
