// Content script for Chrome extension
(function() {
  'use strict'

  const INJECTED_ID = 'astrovox-sidebar'
  let isOpen = false
  let messages = []
  let apiKey = ''

  function init() {
    loadSettings()
    if (!apiKey) {
      showSetupPrompt()
      return
    }
    injectSidebar()
  }

  function loadSettings() {
    try {
      const settings = JSON.parse(localStorage.getItem('astrovox-settings') || '{}')
      apiKey = settings.apiKey || ''
    } catch (e) {
      console.error('Failed to load settings:', e)
    }
  }

  function showSetupPrompt() {
    const banner = document.createElement('div')
    banner.id = 'astrovox-setup'
    banner.style.cssText = `
      position: fixed; top: 10px; right: 10px; z-index: 10000;
      background: #02040a; border: 1px solid #06b6d4; border-radius: 12px;
      padding: 16px; color: #e2e8f0; font-family: Inter, sans-serif;
      max-width: 300px; box-shadow: 0 4px 20px rgba(0,0,0,0.3);
    `
    banner.innerHTML = `
      <div style="font-weight: 600; margin-bottom: 8px; color: #67e8f9;">🛸 Astrovox AI</div>
      <div style="font-size: 12px; color: #94a3b8; margin-bottom: 12px;">
        Enter your API key to get started.
      </div>
      <input type="password" id="astrovox-api-key" placeholder="API Key"
        style="width: 100%; padding: 8px; background: #0f172a; border: 1px solid #1e293b;
        border-radius: 6px; color: #e2e8f0; font-size: 12px; margin-bottom: 8px; box-sizing: border-box;" />
      <button id="astrovox-save" style="width: 100%; padding: 8px; background: #06b6d4;
        color: #02040a; border: none; border-radius: 6px; cursor: pointer; font-weight: 600; font-size: 12px;">
        Save & Start
      </button>
    `
    document.body.appendChild(banner)

    document.getElementById('astrovox-save').addEventListener('click', () => {
      const key = document.getElementById('astrovox-api-key').value.trim()
      if (key) {
        apiKey = key
        localStorage.setItem('astrovox-settings', JSON.stringify({ apiKey: key }))
        banner.remove()
        init()
      }
    })
  }

  function injectSidebar() {
    if (document.getElementById(INJECTED_ID)) return

    const sidebar = document.createElement('div')
    sidebar.id = INJECTED_ID
    sidebar.style.cssText = `
      position: fixed; top: 0; right: -400px; width: 380px; height: 100vh;
      background: #02040a; border-left: 1px solid #1e293b; z-index: 9999;
      transition: right 0.3s ease; display: flex; flex-direction: column;
      font-family: 'Inter', sans-serif; box-shadow: -4px 0 20px rgba(0,0,0,0.3);
    `
    sidebar.innerHTML = `
      <div style="padding: 16px; border-bottom: 1px solid #1e293b; display: flex; justify-content: space-between; align-items: center;">
        <div style="font-size: 14px; font-weight: 600; color: #67e8f9;">ASTROVOX</div>
        <button id="astrovox-close" style="background: transparent; border: none; color: #94a3b8; cursor: pointer; font-size: 18px;">×</button>
      </div>
      <div id="astrovox-messages" style="flex: 1; overflow-y: auto; padding: 16px; display: flex; flex-direction: column; gap: 12px;"></div>
      <div style="padding: 12px; border-top: 1px solid #1e293b; display: flex; gap: 8px;">
        <input type="text" id="astrovox-input" placeholder="Ask anything..."
          style="flex: 1; padding: 10px; background: #050a18; border: 1px solid #1e293b;
          border-radius: 20px; color: #67e8f9; font-size: 13px; outline: none;" />
        <button id="astrovox-send" style="padding: 0 16px; background: #06b6d4; color: #02040a;
          border: none; border-radius: 20px; cursor: pointer; font-weight: 700; font-size: 12px;">SEND</button>
      </div>
    `
    document.body.appendChild(sidebar)

    document.getElementById('astrovox-close').addEventListener('click', toggleSidebar)
    document.getElementById('astrovox-send').addEventListener('click', sendMessage)
    document.getElementById('astrovox-input').addEventListener('keydown', (e) => {
      if (e.key === 'Enter') sendMessage()
    })

    chrome.runtime.onMessage.addListener((msg) => {
      if (msg.type === 'EXPLAIN_SELECTION') {
        addMessage('user', msg.text)
        sendMessage()
      }
    })
  }

  function toggleSidebar() {
    const sidebar = document.getElementById(INJECTED_ID)
    isOpen = !isOpen
    sidebar.style.right = isOpen ? '0' : '-400px'
  }

  async function sendMessage() {
    const input = document.getElementById('astrovox-input')
    const message = input.value.trim()
    if (!message) return
    input.value = ''
    addMessage('user', message)

    const loadingDiv = document.createElement('div')
    loadingDiv.style.cssText = 'color: #06b6d4; font-size: 13px; padding: 8px;'
    loadingDiv.textContent = 'Thinking...'
    document.getElementById('astrovox-messages').appendChild(loadingDiv)

    try {
      const response = await fetch(`${API_BASE}/chat/message`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${apiKey}`
        },
        body: JSON.stringify({
          conversation_id: 'browser-' + Date.now(),
          message,
          model: 'gpt-4'
        })
      })
      const data = await response.json()
      loadingDiv.remove()
      addMessage('assistant', data.ai_message?.content || 'No response')
    } catch (error) {
      loadingDiv.remove()
      addMessage('error', `Error: ${error.message}`)
    }
  }

  function addMessage(role, content) {
    const container = document.getElementById('astrovox-messages')
    const div = document.createElement('div')
    div.style.cssText = `
      padding: 12px; border-radius: 12px; font-size: 13px; line-height: 1.6;
      max-width: 90%; word-wrap: break-word;
      ${role === 'user' ? 'background: #06b6d4; color: #02040a; align-self: flex-end;' : 'background: #1e293b; color: #e2e8f0;'}
    `
    div.textContent = content
    container.appendChild(div)
    container.scrollTop = container.scrollHeight
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init)
  } else {
    init()
  }
})()
