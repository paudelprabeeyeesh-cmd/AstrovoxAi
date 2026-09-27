# AstrovoxAI Go SDK

Official Go SDK for AstrovoxAI.

## Installation

```bash
go get github.com/astrovoxai/go-sdk
```

## Quick Start

```go
package main

import (
    "fmt"
    "github.com/astrovoxai/go-sdk"
)

func main() {
    client := sdk.NewClient("avx_...", "https://api.astrovox.ai/v1")
    result, err := client.SendMessage("conv_123", "Hello, Astrovox!", "gpt-4")
    if err != nil {
        panic(err)
    }
    fmt.Println(result)
}
```

See [sdk/go/](../sdk/go/) for the full source code and [Go SDK Guide](/sdk/go) for documentation.
