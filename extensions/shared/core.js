// Shared browser extension core
const API_BASE = 'https://api.astrovox.ai/v1'

class AstrovoxCore {
  constructor() {
    this.settings = {}
    this.conversationId = null
    this.messages = []
  }

  async init() {
    await this.loadSettings()
    this.setupDefaults()
  }

  async loadSettings() {
    try {
      if (typeof chrome !== 'undefined' && chrome.storage?.local) {
        const result = await chrome.storage.local.get(['astrovoxSettings'])
        this.settings = result.astrovoxSettings || {}
      } else if (typeof browser !== 'undefined' && browser.storage?.local) {
        const result = await browser.storage.local.get(['astrovoxSettings'])
        this.settings = result.astrovoxSettings || {}
      } else {
        const saved = localStorage.getItem('astrovox-settings')
        this.settings = saved ? JSON.parse(saved) : {}
      }
    } catch (e) {
      console.error('Failed to load settings:', e)
    }
  }

  setupDefaults() {
    this.conversationId = this.settings.conversationId || `browser-${Date.now()}`
    this.settings.apiBase = this.settings.apiBase || API_BASE
    this.settings.model = this.settings.model || 'gpt-4'
  }

  async saveSettings(newSettings) {
    this.settings = { ...this.settings, ...newSettings }
    try {
      if (typeof chrome !== 'undefined' && chrome.storage?.local) {
        await chrome.storage.local.set({ astrovoxSettings: this.settings })
      } else if (typeof browser !== 'undefined' && browser.storage?.local) {
        await browser.storage.local.set({ astrovoxSettings: this.settings })
      } else {
        localStorage.setItem('astrovox-settings', JSON.stringify(this.settings))
      }
    } catch (e) {
      console.error('Failed to save settings:', e)
    }
  }

  async chat(message) {
    if (!this.settings.apiKey) {
      throw new Error('API key not configured. Please set your API key in settings.')
    }

    const userMessage = { role: 'user', content: message, timestamp: new Date().toISOString() }
    this.messages.push(userMessage)

    const response = await fetch(`${this.settings.apiBase}/chat/message`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${this.settings.apiKey}`
      },
      body: JSON.stringify({
        conversation_id: this.conversationId,
        message,
        model: this.settings.model
      })
    })

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: response.statusText }))
      throw new Error(error.detail || `HTTP ${response.status}`)
    }

    const data = await response.json()
    const aiMessage = {
      role: 'assistant',
      content: data.ai_message?.content || data.content || JSON.stringify(data),
      timestamp: new Date().toISOString()
    }
    this.messages.push(aiMessage)
    return aiMessage
  }

  async explain(code) {
    const prompt = `Explain this code concisely:\n\n\`\`\`\n${code}\n\`\`\``
    return this.chat(prompt)
  }

  async refactor(code, language = '') {
    const prompt = `Refactor this ${language || ''} code for better readability and performance:\n\n\`\`\`\n${code}\n\`\`\``
    return this.chat(prompt)
  }

  async generateTests(code, language = '') {
    const prompt = `Generate unit tests for this ${language || ''} code:\n\n\`\`\`\n${code}\n\`\`\``
    return this.chat(prompt)
  }

  async summarize(text) {
    const prompt = `Summarize the following content:\n\n${text}`
    return this.chat(prompt)
  }

  getHistory() {
    return [...this.messages]
  }

  clearHistory() {
    this.messages = []
    this.conversationId = `browser-${Date.now()}`
  }

  isConfigured() {
    return !!this.settings.apiKey
  }
}

if (typeof window !== 'undefined') {
  window.AstrovoxCore = new AstrovoxCore()
  window.AstrovoxCore.init().catch(console.error)
}

if (typeof self !== 'undefined' && typeof window === 'undefined') {
  self.AstrovoxCore = new AstrovoxCore()
  self.AstrovoxCore.init().catch(console.error)
}

export { AstrovoxCore }
export default AstrovoxCore
