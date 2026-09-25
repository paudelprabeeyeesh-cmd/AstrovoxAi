# Astrovox AI - VS Code Extension

## Features

- Chat with AI in sidebar
- Explain selected code
- Generate unit tests
- Refactor code
- Document code

## Installation

```bash
# Install from VSIX
code --install-extension astrovox-vscode-1.0.0.vsix

# Or install from marketplace
ext install astrovox.astrovox-vscode
```

## Usage

### Chat
Press `Ctrl+Shift+A` (or `Cmd+Shift+A` on Mac) to open chat.

### Explain Code
1. Select code
2. Press `Ctrl+Shift+E`
3. AI explains the selected code

### Generate Tests
1. Select function/class
2. Press `Ctrl+Shift+T`
3. AI generates unit tests

## Configuration

```json
{
  "astrovox.apiKey": "your-api-key",
  "astrovox.model": "gpt-4",
  "astrovox.temperature": 0.7
}
```
