-- Astrovox AI - Neovim Plugin
-- Provides AI chat integration via Astrovox API

local M = {}
local api_base = 'https://api.astrovox.ai/v1'

function M.setup(opts)
  opts = opts or {}
  api_base = opts.api_base or api_base
end

function M.chat(prompt)
  local job_id = 'astrovox-chat-' .. os.time()
  local lines = {}
  local curl_args = {
    '--silent', '--show-error', '--location',
    '-X', 'POST', api_base .. '/chat/message',
    '-H', 'Content-Type: application/json',
    '-d', vim.json.encode({ message = prompt })
  }
  local job = vim.fn.jobstart(curl_args, {
    stdout_buffered = true,
    on_stdout = function(_, data)
      if data then
        for _, line in ipairs(data) do
          if line ~= '' then table.insert(lines, line) end
        end
      end
    end,
    on_exit = function(_, exit_code)
      if exit_code == 0 then
        local response = table.concat(lines, '\n')
        vim.notify(response, vim.log.levels.INFO)
      else
        vim.notify('Astrovox AI request failed', vim.log.levels.ERROR)
      end
    end
  })
  return job_id
end

function M.explain()
  local code = vim.fn.getline('.')
  M.chat('Explain this code: ' .. code)
end

function M.tests()
  local code = vim.fn.getline('.')
  M.chat('Generate unit tests for: ' .. code)
end

function M.refactor()
  local code = vim.fn.getline('.')
  M.chat('Refactor this code for readability: ' .. code)
end

vim.api.nvim_create_user_command('AstrovoxChat', function(opts) M.chat(opts.args) end, { nargs = '*' })
vim.api.nvim_create_user_command('AstrovoxExplain', M.explain, {})
vim.api.nvim_create_user_command('AstrovoxTests', M.tests, {})
vim.api.nvim_create_user_command('AstrovoxRefactor', M.refactor, {})

return M
