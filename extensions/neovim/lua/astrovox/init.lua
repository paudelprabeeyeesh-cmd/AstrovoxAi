-- Astrovox AI - Neovim Plugin Core
-- Provides AI chat integration via Astrovox API with rich features

local M = {}
local api_base = 'https://api.astrovox.ai/v1'
local state = {
  history = {},
  current_conversation = nil,
  config = {
    api_key = vim.fn.getenv('ASTROVOX_API_KEY'),
    model = 'gpt-4',
    max_tokens = 2048,
    temperature = 0.7,
    auto_complete = false,
    keymaps = {
      chat = '<leader>ac',
      explain = '<leader>ae',
      refactor = '<leader>ar',
      tests = '<leader>at',
      review = '<leader>av',
      document = '<leader>ad',
      fix = '<leader>af',
      optimize = '<leader>ao'
    },
    ui = {
      width = 40,
      height = 15,
      border = 'rounded'
    }
  }
}

function M.setup(opts)
  opts = opts or {}
  state.config = vim.tbl_deep_extend('force', state.config, opts)

  if state.config.api_key == '' then
    vim.notify('Astrovox: API key not set. Set ASTROVOX_API_KEY environment variable or pass api_key in config.', vim.log.levels.WARN)
    return
  end

  local keymaps = state.config.keymaps
  vim.keymap.set('n', keymaps.chat, M.start_chat, { desc = 'Astrovox: Start Chat' })
  vim.keymap.set('n', keymaps.explain, M.explain_code, { desc = 'Astrovox: Explain Code' })
  vim.keymap.set('n', keymaps.refactor, M.refactor_code, { desc = 'Astrovox: Refactor Code' })
  vim.keymap.set('n', keymaps.tests, M.generate_tests, { desc = 'Astrovox: Generate Tests' })
  vim.keymap.set('n', keymaps.review, M.review_code, { desc = 'Astrovox: Review Code' })
  vim.keymap.set('n', keymaps.document, M.document_code, { desc = 'Astrovox: Document Code' })
  vim.keymap.set('n', keymaps.fix, M.fix_bug, { desc = 'Astrovox: Fix Bug' })
  vim.keymap.set('n', keymaps.optimize, M.optimize_code, { desc = 'Astrovox: Optimize Code' })

  vim.api.nvim_create_user_command('AstrovoxChat', M.chat_command, { nargs = '*' })
  vim.api.nvim_create_user_command('AstrovoxExplain', M.explain_code, {})
  vim.api.nvim_create_user_command('AstrovoxRefactor', M.refactor_code, {})
  vim.api.nvim_create_user_command('AstrovoxTests', M.generate_tests, {})
  vim.api.nvim_create_user_command('AstrovoxReview', M.review_code, {})
  vim.api.nvim_create_user_command('AstrovoxDocument', M.document_code, {})
  vim.api.nvim_create_user_command('AstrovoxFix', M.fix_bug, {})
  vim.api.nvim_create_user_command('AstrovoxOptimize', M.optimize_code, {})
  vim.api.nvim_create_user_command('AstrovoxClear', M.clear_history, {})

  if state.config.auto_complete then
    M.setup_auto_complete()
  end

  vim.notify('Astrovox AI plugin loaded successfully', vim.log.levels.INFO)
end

function M.setup_auto_complete()
  local group = vim.api.nvim_create_augroup('AstrovoxAutoComplete', { clear = true })
  vim.api.nvim_create_autocmd({ 'InsertEnter' }, {
    group = group,
    pattern = '*',
    callback = function()
      vim.defer_fn(function()
        M.suggest_completion()
      end, 500)
    end
  })
end

function M.suggest_completion()
  local line = vim.api.nvim_get_current_line()
  local col = vim.api.nvim_win_get_cursor(0)[2]
  local context = line:sub(1, col)

  M.api_request('/autocomplete', {
    prompt = context,
    model = state.config.model,
    max_tokens = 100
  }, function(response)
    if response and response.suggestion then
      vim.api.nvim_buf_set_text(0, vim.api.nvim_win_get_cursor(0)[1] - 1, col, vim.api.nvim_win_get_cursor(0)[1] - 1, col, { response.suggestion })
    end
  end)
end

function M.chat_command(opts)
  local prompt = table.concat(opts.fargs, ' ')
  if prompt == '' then
    prompt = vim.fn.input('Astrovox: ')
  end
  if prompt == '' then return end
  M.chat(prompt)
end

function M.chat(prompt)
  local job_id = 'astrovox-chat-' .. os.time()
  local lines = {}
  local curl_args = {
    '--silent', '--show-error', '--location',
    '-X', 'POST', api_base .. '/chat/message',
    '-H', 'Content-Type: application/json',
    '-H', 'Authorization: Bearer ' .. state.config.api_key,
    '-d', vim.json.encode({
      conversation_id = state.current_conversation or ('nvim-' .. os.time()),
      message = prompt,
      model = state.config.model,
      max_tokens = state.config.max_tokens,
      temperature = state.config.temperature
    })
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
        local decoded = vim.json.decode(response)
        local content = decoded.ai_message and decoded.ai_message.content or response
        table.insert(state.history, { role = 'user', content = prompt })
        table.insert(state.history, { role = 'assistant', content = content })
        vim.notify(content, vim.log.levels.INFO)
      else
        vim.notify('Astrovox AI request failed', vim.log.levels.ERROR)
      end
    end
  })
  return job_id
end

function M.explain_code()
  local selection = M.get_selection()
  if not selection then
    vim.notify('No code selected', vim.log.levels.WARN)
    return
  end
  M.chat('Explain this code concisely:\n\n' .. selection)
end

function M.refactor_code()
  local selection = M.get_selection()
  if not selection then
    vim.notify('No code selected', vim.log.levels.WARN)
    return
  end
  M.chat('Refactor this code for better readability and performance:\n\n' .. selection)
end

function M.generate_tests()
  local selection = M.get_selection()
  if not selection then
    vim.notify('No code selected', vim.log.levels.WARN)
    return
  end
  M.chat('Generate unit tests for this code:\n\n' .. selection)
end

function M.review_code()
  local selection = M.get_selection()
  if not selection then
    vim.notify('No code selected', vim.log.levels.WARN)
    return
  end
  M.chat('Review this code for bugs, security issues, and improvements:\n\n' .. selection)
end

function M.document_code()
  local selection = M.get_selection()
  if not selection then
    vim.notify('No code selected', vim.log.levels.WARN)
    return
  end
  M.chat('Generate documentation for this code:\n\n' .. selection)
end

function M.fix_bug()
  local selection = M.get_selection()
  if not selection then
    vim.notify('No code selected', vim.log.levels.WARN)
    return
  end
  local bug_desc = vim.fn.input('Describe the bug: ')
  if bug_desc == '' then return end
  M.chat('Fix this bug: ' .. bug_desc .. '\n\nCode:\n' .. selection)
end

function M.optimize_code()
  local selection = M.get_selection()
  if not selection then
    vim.notify('No code selected', vim.log.levels.WARN)
    return
  end
  M.chat('Optimize this code for performance:\n\n' .. selection)
end

function M.get_selection()
  local start_pos = vim.fn.getpos("'<")
  local end_pos = vim.fn.getpos("'>")
  if start_pos[2] == 0 or end_pos[2] == 0 then
    return vim.fn.getline('.')
  end
  local lines = vim.fn.getline(start_pos[2], end_pos[2])
  return table.concat(lines, '\n')
end

function M.clear_history()
  state.history = {}
  state.current_conversation = nil
  vim.notify('Astrovox conversation cleared', vim.log.levels.INFO)
end

function M.api_request(endpoint, data, callback)
  local lines = {}
  local body = vim.json.encode(data)
  local curl_args = {
    '--silent', '--show-error', '--location',
    '-X', 'POST', api_base .. endpoint,
    '-H', 'Content-Type: application/json',
    '-H', 'Authorization: Bearer ' .. state.config.api_key,
    '-d', body
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
      if exit_code == 0 and callback then
        local response = table.concat(lines, '\n')
        callback(vim.json.decode(response))
      end
    end
  })
  return job
end

function M.get_status()
  return {
    api_key_configured = state.config.api_key ~= '',
    model = state.config.model,
    conversation_id = state.current_conversation,
    history_length = #state.history,
    auto_complete = state.config.auto_complete
  }
end

vim.api.nvim_create_user_command('AstrovoxStatus', function()
  local status = M.get_status()
  vim.notify(vim.inspect(status), vim.log.levels.INFO)
end, {})

return M
