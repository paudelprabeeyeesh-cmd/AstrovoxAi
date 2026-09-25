package astrovox

import (
    "bytes"
    "encoding/json"
    "fmt"
    "io"
    "net/http"
    "time"
)

type Message struct {
    Role      string    `json:"role"`
    Content   string    `json:"content"`
    Timestamp string    `json:"timestamp,omitempty"`
}

type Conversation struct {
    ID        string    `json:"id"`
    Title     string    `json:"title"`
    Messages  []Message `json:"messages,omitempty"`
    Model     string    `json:"model"`
    CreatedAt string    `json:"created_at,omitempty"`
}

type Client struct {
    APIKey    string
    BaseURL   string
    HTTPClient *http.Client
}

func NewClient(apiKey, baseURL string) *Client {
    if baseURL == "" {
        baseURL = "https://api.astrovox.ai/v1"
    }
    return &Client{
        APIKey:    apiKey,
        BaseURL:   baseURL,
        HTTPClient: &http.Client{Timeout: 30 * time.Second},
    }
}

func (c *Client) SendMessage(conversationID, message, model string) (map[string]interface{}, error) {
    payload := map[string]interface{}{
        "conversation_id": conversationID,
        "message":         message,
        "model":           model,
    }
    return c.post("/chat/message", payload)
}

func (c *Client) CreateConversation(title, model string) (*Conversation, error) {
    payload := map[string]interface{}{
        "title": title,
        "model": model,
    }
    result, err := c.post("/conversations", payload)
    if err != nil {
        return nil, err
    }
    return &Conversation{
        ID:    fmt.Sprintf("%v", result["id"]),
        Title: fmt.Sprintf("%v", result["title"]),
        Model: fmt.Sprintf("%v", result["model"]),
    }, nil
}

func (c *Client) ListConversations() ([]Conversation, error) {
    result, err := c.get("/conversations")
    if err != nil {
        return nil, err
    }
    items, ok := result.([]interface{})
    if !ok {
        return nil, fmt.Errorf("unexpected response format")
    }
    conversations := make([]Conversation, len(items))
    for i, item := range items {
        m := item.(map[string]interface{})
        conversations[i] = Conversation{
            ID:    fmt.Sprintf("%v", m["id"]),
            Title: fmt.Sprintf("%v", m["title"]),
            Model: fmt.Sprintf("%v", m["model"]),
        }
    }
    return conversations, nil
}

func (c *Client) DeleteConversation(conversationID string) error {
    req, _ := http.NewRequest("DELETE", c.BaseURL+"/conversations/"+conversationID, nil)
    req.Header.Set("Authorization", "Bearer "+c.APIKey)
    resp, err := c.HTTPClient.Do(req)
    if err != nil {
        return err
    }
    defer resp.Body.Close()
    return nil
}

func (c *Client) HealthCheck() (map[string]interface{}, error) {
    return c.get("/health")
}

func (c *Client) post(path string, payload interface{}) (map[string]interface{}, error) {
    body, _ := json.Marshal(payload)
    req, _ := http.NewRequest("POST", c.BaseURL+path, bytes.NewBuffer(body))
    req.Header.Set("Authorization", "Bearer "+c.APIKey)
    req.Header.Set("Content-Type", "application/json")
    resp, err := c.HTTPClient.Do(req)
    if err != nil {
        return nil, err
    }
    defer resp.Body.Close()
    result, _ := io.ReadAll(resp.Body)
    var data map[string]interface{}
    json.Unmarshal(result, &data)
    return data, nil
}

func (c *Client) get(path string) (map[string]interface{}, error) {
    req, _ := http.NewRequest("GET", c.BaseURL+path, nil)
    req.Header.Set("Authorization", "Bearer "+c.APIKey)
    resp, err := c.HTTPClient.Do(req)
    if err != nil {
        return nil, err
    }
    defer resp.Body.Close()
    result, _ := io.ReadAll(resp.Body)
    var data map[string]interface{}
    json.Unmarshal(result, &data)
    return data, nil
}
