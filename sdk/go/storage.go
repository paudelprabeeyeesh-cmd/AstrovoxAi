package storage

type Client struct {
	apiKey string
}

func NewClient(apiKey string) *Client {
	return &Client{apiKey: apiKey}
}

func (c *Client) SaveCheckpoint(checkpoint map[string]interface{}) error {
	return nil
}
