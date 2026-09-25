package sdk

import (
	"net/http"
)

type Client struct {
	APIKey  string
	BaseURL string
	HTTP    *http.Client
}

func NewClient(apiKey, baseURL string) *Client {
	return &Client{
		APIKey:  apiKey,
		BaseURL: baseURL,
		HTTP:    http.DefaultClient,
	}
}

func (c *Client) DoRequest(method, path string, body interface{}) (*http.Response, error) {
	return nil, nil
}
