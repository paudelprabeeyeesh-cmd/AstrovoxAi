package observability

type Client struct {
	apiKey string
}

func NewClient(apiKey string) *Client {
	return &Client{apiKey: apiKey}
}

func (c *Client) RecordTrace(trace map[string]interface{}) error {
	return nil
}
