-- Astrovox AI Neovim Plugin
-- Provides AI-powered code assistance

local M = {}

M.config = {
  api_key = vim.fn.getenv('ASTROVOX_API_KEY'),
  model = 'gpt-4',
  auto_complete = true,
  keymaps = {
    chat = '<leader>ac',
    explain = '<leader>ae',
    refactor = '<leader>ar',
    tests = '<leader>at'
  }
}

function M.setup(opts)
  opts = opts or {}
  M.config = vim.tbl_deep_extend('force', M.config, opts)

  if M.config.api_key == '' then
    vim.notify('Astrovox: API key not set. Set ASTROVOX_API_KEY environment variable.', vim.log.levels.WARN)
    return
  end

  local keymaps = M.config.keymaps
  vim.keymap.set('n', keymaps.chat, M.start_chat, { desc = 'Astrovox: Start Chat' })
  vim.keymap.set('n', keymaps.explain, M.explain_code, { desc = 'Astrovox: Explain Code' })
  vim.keymap.set('n', keymaps.refactor, M.refactor_code, { desc = 'Astrovox: Refactor Code' })
  vim.keymap.set('n', keymaps.tests, M.generate_tests, { desc = 'Astrovox: Generate Tests' })
end

function M.start_chat()
  vim.notify('Astrovox: Chat feature coming soon', vim.log.levels.INFO)
end

function M.explain_code()
  local selection = vim.fn.getregion(vim.fn.getpos("'<"), vim.fn.getpos("'>"))
  vim.notify('Astrovox: Explaining code...', vim.log.levels.INFO)
end

function M.refactor_code()
  vim.notify('Astrovox: Refactoring code...', vim.log.levels.INFO)
end

function M.generate_tests()
  vim.notify('Astrovox: Generating tests...', vim.log.levels.INFO)
end

return M
