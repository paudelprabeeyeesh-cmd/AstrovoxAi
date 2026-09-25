# Rust SDK

Official Rust SDK for Astrovox AI.

## Installation

```toml
[dependencies]
astrovox = "0.1"
tokio = { version = "1", features = ["full"] }
serde = { version = "1", features = ["derive"] }
```

## Usage

```rust
use astrovox::AstrovoxClient;

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    let client = AstrovoxClient::new("your-api-key", Some("https://api.astrovox.ai/v1"));

    let conversation = client.create_conversation("My Conversation", "gpt-4").await?;
    let response = client.send_message(&conversation.id, "Hello, AI!").await?;

    println!("{}", response.ai_message.content);
    Ok(())
}
```

## Error Handling

```rust
match client.send_message(&conv_id, "Hello").await {
    Ok(response) => println!("{}", response.ai_message.content),
    Err(e) => eprintln!("Error: {}", e),
}
```
