# Astrovox AI - Neovim Plugin

## Features

- Chat with AI in floating window
- Explain code
- Generate tests
- Refactor code

## Installation

### lazy.nvim
```lua
{
  'astrovox/astrovox.nvim',
  dependencies = { 'nvim-lua/plenary.nvim' },
  config = function()
    require('astrovox').setup({
      api_key = os.getenv('ASTROVOX_API_KEY'),
      model = 'gpt-4'
    })
  end
}
```

### packer.nvim
```lua
use 'astrovox/astrovox.nvim'
```

## Usage

- `<leader>ac` - Open chat
- `<leader>ae` - Explain selection
- `<leader>ar` - Refactor selection
- `<leader>at` - Generate tests

## Configuration

```lua
require('astrovox').setup({
  api_key = 'your-api-key',
  model = 'gpt-4',
  auto_complete = false,
  keymaps = {
    chat = '<leader>ac',
    explain = '<leader>ae',
    refactor = '<leader>ar',
    tests = '<leader>at'
  }
})
```
