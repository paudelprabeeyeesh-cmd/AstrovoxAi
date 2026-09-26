# Astrovox CLI

Command-line interface for Astrovox AI.

## Installation

```bash
# From source
python -m pip install -e cli/

# Or run directly
python cli/astrovox.py
```

## Usage

```bash
# Send a message
astrovox send <conversation_id> "Hello, world!"

# List conversations
astrovox conversations

# Create a new conversation
astrovox create --title "My Chat"

# Stream a message
astrovox stream <conversation_id> "Explain quantum computing"

# Check API health
astrovox health
```

## Configuration

Set the `ASTROVOX_API_KEY` environment variable:

```bash
export ASTROVOX_API_KEY=your-api-key
```

Optionally override the API base URL:

```bash
export ASTROVOX_API_URL=https://api.astrovox.ai/v1
```
