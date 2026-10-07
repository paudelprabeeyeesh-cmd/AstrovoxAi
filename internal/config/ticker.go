package config

import "time"

func timeTicker(intervalMS int64) *time.Ticker {
	if intervalMS <= 0 {
		intervalMS = 500
	}
	return time.NewTicker(time.Duration(intervalMS) * time.Millisecond)
}
