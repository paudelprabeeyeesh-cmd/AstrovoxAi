# AstrovoxAI Rust SDK

Official Rust SDK for AstrovoxAI.

## Installation

```toml
[dependencies]
astrovox-sdk = "1.0"
```

## Quick Start

```rust
use astrovox_sdk::AstrovoxClient;

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    let client = AstrovoxClient::new("avx_...", None);
    let response = client.send_message("conv_123", "Hello, Astrovox!", "gpt-4").await?;
    println!("{:?}", response);
    Ok(())
}
```

See [sdk/rust/](../sdk/rust/) for the full source code and [Rust SDK Guide](/sdk/rust) for documentation.
