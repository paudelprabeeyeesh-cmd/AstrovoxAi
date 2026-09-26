package mlops

type Client struct {
	apiKey string
}

func NewClient(apiKey string) *Client {
	return &Client{apiKey: apiKey}
}

func (c *Client) LogMetrics(experimentID string, metrics map[string]float64) error {
	return nil
}
