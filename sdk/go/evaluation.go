package evaluation

type Client struct {
	apiKey string
}

func NewClient(apiKey string) *Client {
	return &Client{apiKey: apiKey}
}

func (c *Client) RunBenchmark(modelID, benchmarkName string) (map[string]interface{}, error) {
	return nil, nil
}
