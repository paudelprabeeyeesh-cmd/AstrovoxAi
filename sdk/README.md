# SDKs

Astrovox provides official SDKs for multiple languages.

## Python

```python
import astrovox

client = astrovox.AstrovoxClient(api_key="your-key")
conversation = client.create_conversation(title="My Chat")
response = client.send_message(conversation.id, "Hello!")
print(response['ai_message']['content'])
```

[Full Documentation](./python/README.md)

## TypeScript

```typescript
import { AstrovoxClient } from '@astrovox/sdk'

const client = new AstrovoxClient({ apiKey: 'your-key' })
const conversation = await client.createConversation({ title: 'My Chat' })
const response = await client.sendMessage({ conversationId: conversation.id, message: 'Hello!' })
console.log(response.ai_message.content)
```

[Full Documentation](./typescript/README.md)

## Go

```go
package main

import "github.com/astrovox/sdk/go"

client := astrovox.NewClient("your-key")
conversation, _ := client.CreateConversation("My Chat", "gpt-4")
response, _ := client.SendMessage(conversation.ID, "Hello!")
fmt.Println(response.AiMessage.Content)
```

[Full Documentation](./go/README.md)

## Rust

```rust
use astrovox::AstrovoxClient;

let client = AstrovoxClient::new("your-key", None);
let conversation = client.create_conversation("My Chat", "gpt-4").await?;
let response = client.send_message(&conversation.id, "Hello!").await?;
println!("{}", response.ai_message.content);
```

[Full Documentation](./rust/README.md)
