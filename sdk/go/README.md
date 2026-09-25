# Go SDK

Official Go SDK for Astrovox AI.

## Installation

```bash
go get github.com/astrovox/sdk/go
```

## Usage

```go
package main

import (
    "fmt"
    "github.com/astrovox/sdk/go"
)

func main() {
    client := astrovox.NewClient("your-api-key", "https://api.astrovox.ai/v1")

    conversation, err := client.CreateConversation("My Conversation", "gpt-4")
    if err != nil {
        panic(err)
    }

    response, err := client.SendMessage(conversation.ID, "Hello, AI!")
    if err != nil {
        panic(err)
    }

    fmt.Println(response.AiMessage.Content)
}
```

## Error Handling

```go
resp, err := client.SendMessage(convID, "Hello")
if err != nil {
    if strings.Contains(err.Error(), "401") {
        // Handle auth error
    }
    if strings.Contains(err.Error(), "429") {
        // Handle rate limit
    }
}
```
