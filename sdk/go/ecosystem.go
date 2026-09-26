package ecosystem

type Client struct {
	apiKey string
}

func NewClient(apiKey string) *Client {
	return &Client{apiKey: apiKey}
}

func (c *Client) ListPlugins(capability string) ([]map[string]interface{}, error) {
	return nil, nil
}
