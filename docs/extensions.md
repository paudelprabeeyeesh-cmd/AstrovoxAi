# Extensions Guide

AstrovoxAI extensions bring AI capabilities directly into your favorite tools.

## VS Code
- Chat panel with streaming responses
- Inline code completion
- Code explanation, refactoring, test generation
- Bug fixing and optimization suggestions
- Security issue detection
- Auto-update notifications

Install: Search "Astrovox AI" in VS Code Marketplace.

## JetBrains
- Tool window for chat
- Context actions for explain, refactor, generate tests
- Live templates for common AI prompts
- Settings integration for API key and model selection

Install: Search "Astrovox AI" in JetBrains Marketplace.

## Chrome / Firefox / Safari
- Sidebar chat with persistent history
- Context menu integration
- Content script for page summarization
- Notification support

Install from respective extension stores.

## Neovim
- Floating chat window
- Inline completions via LSP
- Telescope integration
- Keybindings for common actions

```lua
require('astrovox').setup({
  api_key = vim.env.ASTROVOX_API_KEY,
  model = 'gpt-4',
})
```
