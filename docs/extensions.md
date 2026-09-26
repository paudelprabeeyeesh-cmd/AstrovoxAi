# Extensions Guide

AstrovoxAI extensions bring AI capabilities directly into your favorite tools. Enhance your workflow with intelligent assistance wherever you code, browse, or create.

## Available Extensions

- [VS Code](#vs-code)
- [JetBrains](#jetbrains)
- [Chrome](#chrome)
- [Firefox](#firefox)
- [Safari](#safari)
- [Neovim](#neovim)
- [Web Components](#web-components)

## VS Code

### Features

- Chat panel with streaming responses
- Inline code completion
- Code explanation, refactoring, test generation
- Bug fixing and optimization suggestions
- Security issue detection
- Auto-update notifications
- Context-aware suggestions
- Multi-file understanding

### Installation

Search "Astrovox AI" in VS Code Marketplace or install from command line:

```bash
code --install-extension astrovox.ai-vscode
```

### Configuration

```json
{
  "astrovox.apiKey": "your-api-key",
  "astrovox.model": "gpt-4",
  "astrovox.temperature": 0.7,
  "astrovox.maxTokens": 1000,
  "astrovox.autoComplete": true,
  "astrovox.securityScan": true
}
```

### Commands

| Command | Description |
|---------|-------------|
| `Astrovox: Explain Code` | Explain selected code |
| `Astrovox: Refactor` | Refactor selected code |
| `Astrovox: Generate Tests` | Generate unit tests |
| `Astrovox: Fix Bug` | Find and fix bugs |
| `Astrovox: Optimize` | Performance optimization |
| `Astrovox: Security Scan` | Detect security issues |

## JetBrains

### Features

- Tool window for chat
- Context actions for explain, refactor, generate tests
- Live templates for common AI prompts
- Settings integration for API key and model selection
- Code inspections with AI suggestions
- Smart code completion

### Installation

Search "Astrovox AI" in JetBrains Marketplace.

### Configuration

```xml
<application>
  <component name="AstrovoxSettings">
    <option name="apiKey" value="your-api-key" />
    <option name="model" value="gpt-4" />
    <option name="temperature" value="0.7" />
    <option name="maxTokens" value="1000" />
  </component>
</application>
```

## Chrome

### Features

- Sidebar chat with persistent history
- Context menu integration
- Content script for page summarization
- Notification support
- Quick actions for common tasks
- Screenshot context sharing

### Installation

Install from Chrome Web Store.

### Usage

1. Click the Astrovox icon in the toolbar
2. Chat in the sidebar
3. Right-click selected text for AI actions
4. Use keyboard shortcuts for quick access

## Firefox

### Features

- Sidebar chat with persistent history
- Context menu integration
- Content script for page summarization
- Notification support
- Privacy-first design

### Installation

Install from Firefox Add-ons.

## Safari

### Features

- Toolbar popup for quick access
- Reading list integration
- Page summarization
- Share extension

### Installation

Install from App Store.

## Neovim

### Features

- Floating chat window
- Inline completions via LSP
- Telescope integration
- Keybindings for common actions
- Buffer-aware context

### Installation

```bash
# Using lazy.nvim
{
  'astrovox/astrovox.nvim',
  config = function()
    require('astrovox').setup({
      api_key = vim.env.ASTROVOX_API_KEY,
      model = 'gpt-4',
      max_tokens = 1000,
      temperature = 0.7,
    })
  end
}
```

### Usage

```lua
-- Chat
:lua require('astrovox').chat()

-- Explain code
:lua require('astrovox').explain()

-- Refactor
:lua require('astrovox').refactor()

-- Generate tests
:lua require('astrovox').generate_tests()
```

### Keybindings

```lua
vim.keymap.set('v', '<leader>ae', ':lua require("astrovox").explain()<CR>')
vim.keymap.set('v', '<leader>ar', ':lua require("astrovox").refactor()<CR>')
vim.keymap.set('v', '<leader>at', ':lua require("astrovox").generate_tests()<CR>')
vim.keymap.set('n', '<leader>ac', ':lua require("astrovox").chat()<CR>')
```

## Web Components

Use AstrovoxAI in any web application with web components:

```html
<!DOCTYPE html>
<html>
<head>
  <script type="module" src="https://cdn.astrovox.ai/web-components.js"></script>
</head>
<body>
  <astrovox-chat
    api-key="your-api-key"
    theme="dark"
    model="gpt-4"
    enable-voice
    enable-branching
  ></astrovox-chat>
</body>
</html>
```

### Available Components

| Component | Description |
|-----------|-------------|
| `<astrovox-chat>` | Full chat interface |
| `<astrovox-input>` | Standalone input component |
| `<astrovox-message>` | Single message display |
| `<astrovox-models>` | Model selector dropdown |
| `<astrovox-settings>` | Settings panel |

## Extension Development

Build your own extensions using the AstrovoxAI Extension SDK:

```typescript
import { AstrovoxExtension, Message, Context } from '@astrovox/extension-sdk'

const extension = new AstrovoxExtension({
  name: 'my-extension',
  version: '1.0.0',
  apiKey: process.env.ASTROVOX_API_KEY
})

extension.onMessage(async (message: Message, context: Context) => {
  // Custom processing
  return message
})

extension.onCommand('custom-command', async (args) => {
  // Custom command logic
  return { result: 'success' }
})

export default extension
```

### Extension Manifest

```json
{
  "name": "my-extension",
  "version": "1.0.0",
  "description": "My custom Astrovox extension",
  "engines": {
    "astrovox": "^2.0.0"
  },
  "permissions": [
    "chat.read",
    "chat.write",
    "files.read"
  ],
  "main": "dist/index.js"
}
```

## Marketplace

Browse and install community extensions:

```bash
# List available extensions
astrovox extensions list

# Install extension
astrovox extensions install my-extension

# Publish extension
astrovox extensions publish
```

## Security

All extensions:
- Require explicit permission grants
- Run in isolated contexts
- Communicate via secure APIs
- Are audited for security (VSCode/JetBrains marketplace)
- Support API key rotation
