package certification

type Client struct {
	apiKey string
}

func NewClient(apiKey string) *Client {
	return &Client{apiKey: apiKey}
}

func (c *Client) VerifyModel(modelID string) (map[string]interface{}, error) {
	return nil, nil
}
