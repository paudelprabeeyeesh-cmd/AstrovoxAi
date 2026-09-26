package sdk

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"time"
)

type RetryPolicy struct {
	MaxRetries      int
	BackoffFactor   float64
	RetryableStatus []int
}

type Client struct {
	APIKey       string
	BaseURL      string
	HTTP         *http.Client
	RetryPolicy  RetryPolicy
}

type Message struct {
	Role      string `json:"role"`
	Content   string `json:"content"`
	Timestamp string `json:"timestamp,omitempty"`
}

type Conversation struct {
	ID        string    `json:"id"`
	Title     string    `json:"title"`
	Messages  []Message `json:"messages,omitempty"`
	Model     string    `json:"model"`
	CreatedAt string    `json:"created_at,omitempty"`
}

func NewClient(apiKey, baseURL string) *Client {
	return &Client{
		APIKey:  apiKey,
		BaseURL: baseURL,
		HTTP:    &http.Client{Timeout: 30 * time.Second},
		RetryPolicy: RetryPolicy{
			MaxRetries:    3,
			BackoffFactor: 1.0,
			RetryableStatus: []int{429, 500, 502, 503, 504},
		},
	}
}

func (c *Client) DoRequest(method, path string, body interface{}) (*http.Response, error) {
	var payload io.Reader
	if body != nil {
		b, err := json.Marshal(body)
		if err != nil {
			return nil, err
		}
		payload = bytes.NewReader(b)
	}
	req, err := http.NewRequest(method, c.BaseURL+path, payload)
	if err != nil {
		return nil, err
	}
	req.Header.Set("Authorization", "Bearer "+c.APIKey)
	req.Header.Set("Content-Type", "application/json")
	resp, err := c.HTTP.Do(req)
	if err != nil {
		return nil, err
	}
	return resp, nil
}

func (c *Client) SendMessage(conversationID, message, model string) (map[string]interface{}, error) {
	resp, err := c.DoRequest("POST", "/chat/message", map[string]interface{}{
		"conversation_id": conversationID,
		"message":         message,
		"model":           model,
	})
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()
	var result map[string]interface{}
	if err := json.NewDecoder(resp.Body).Decode(&result); err != nil {
		return nil, err
	}
	return result, nil
}

func (c *Client) CreateConversation(title, model string) (*Conversation, error) {
	resp, err := c.DoRequest("POST", "/conversations", map[string]interface{}{
		"title": title,
		"model": model,
	})
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()
	var conv Conversation
	if err := json.NewDecoder(resp.Body).Decode(&conv); err != nil {
		return nil, err
	}
	return &conv, nil
}

func (c *Client) HealthCheck() (map[string]interface{}, error) {
	resp, err := c.DoRequest("GET", "/health", nil)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()
	var result map[string]interface{}
	if err := json.NewDecoder(resp.Body).Decode(&result); err != nil {
		return nil, err
	}
	return result, nil
}

func (c *Client) String() string {
	return fmt.Sprintf("AstrovoxClient(base_url=%s)", c.BaseURL)
}

