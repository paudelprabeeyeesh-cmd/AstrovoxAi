// Browser extension core for Astrovox AI
// Works in Chrome, Firefox, Edge, and Safari via polyfills
const API_BASE = 'https://api.astrovox.ai/v1'

class ExtensionCore {
  constructor() {
    this.settings = {}
    this.conversationId = null
    this.messages = []
    this.eventQueue = []
    this.isProcessing = false
  }

  async init() {
    await this.loadSettings()
    this.setupDefaults()
    this.setupServiceWorker()
    this.setupBackgroundSync()
    return this
  }

  async loadSettings() {
    try {
      if (typeof chrome !== 'undefined' && chrome.storage?.local) {
        const result = await chrome.storage.local.get(['astrovoxSettings', 'astrovoxConversationId'])
        this.settings = result.astrovoxSettings || {}
        this.conversationId = result.astrovoxConversationId || this.generateConversationId()
      } else if (typeof browser !== 'undefined' && browser.storage?.local) {
        const result = await browser.storage.local.get(['astrovoxSettings', 'astrovoxConversationId'])
        this.settings = result.astrovoxSettings || {}
        this.conversationId = result.astrovoxConversationId || this.generateConversationId()
      } else {
        const saved = localStorage.getItem('astrovox-settings')
        this.settings = saved ? JSON.parse(saved) : {}
        this.conversationId = `browser-${Date.now()}`
      }
    } catch (e) {
      console.error('Failed to load settings:', e)
      this.conversationId = `browser-${Date.now()}`
    }
  }

  setupDefaults() {
    this.settings.apiBase = this.settings.apiBase || API_BASE
    this.settings.model = this.settings.model || 'gpt-4'
    this.settings.maxTokens = this.settings.maxTokens || 2048
    this.settings.temperature = this.settings.temperature ?? 0.7
    this.conversationId = this.conversationId || `browser-${Date.now()}`
  }

  async saveSettings(newSettings) {
    this.settings = { ...this.settings, ...newSettings }
    try {
      if (typeof chrome !== 'undefined' && chrome.storage?.local) {
        await chrome.storage.local.set({ astrovoxSettings: this.settings, astrovoxConversationId: this.conversationId })
      } else if (typeof browser !== 'undefined' && browser.storage?.local) {
        await browser.storage.local.set({ astrovoxSettings: this.settings, astrovoxConversationId: this.conversationId })
      } else {
        localStorage.setItem('astrovox-settings', JSON.stringify(this.settings))
        localStorage.setItem('astrovox-conversation-id', this.conversationId)
      }
    } catch (e) {
      console.error('Failed to save settings:', e)
    }
  }

  setupServiceWorker() {
    if (typeof chrome !== 'undefined' && chrome.runtime?.onMessage) {
      chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
        this.handleRuntimeMessage(message, sender, sendResponse)
        return true
      })
    }

    if (typeof self !== 'undefined' && 'ServiceWorkerGlobalScope' in self) {
      self.addEventListener('install', (e) => {
        self.skipWaiting()
      })
      self.addEventListener('activate', (e) => {
        e.waitUntil(self.clients.claim())
      })
      self.addEventListener('fetch', (e) => {
        if (e.request.method === 'POST' && e.request.url.includes('/v1/chat/stream')) {
          e.respondWith(this.handleStreamResponse(e.request))
        }
      })
    }
  }

  async handleStreamResponse(request) {
    try {
      const body = await request.json()
      const response = await fetch(`${this.settings.apiBase}/chat/message`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${this.settings.apiKey}` },
        body: JSON.stringify({ ...body, stream: true })
      })

      if (!response.ok) {
        return new Response(JSON.stringify({ error: response.statusText }), { status: response.status })
      }

      return response
    } catch (e) {
      return new Response(JSON.stringify({ error: e.message }), { status: 500 })
    }
  }

  async handleRuntimeMessage(message, sender, sendResponse) {
    const { type, payload, requestId } = message

    try {
      let result
      switch (type) {
        case 'CHAT':
          result = await this.chat(payload.message)
          break
        case 'EXPLAIN':
          result = await this.explain(payload.code)
          break
        case 'REFACTOR':
          result = await this.refactor(payload.code, payload.language)
          break
        case 'GENERATE_TESTS':
          result = await this.generateTests(payload.code, payload.language)
          break
        case 'REVIEW':
          result = await this.review(payload.code, payload.language)
          break
        case 'DOCUMENT':
          result = await this.document(payload.code, payload.language)
          break
        case 'FIX_BUG':
          result = await this.fixBug(payload.code, payload.bugDescription, payload.language)
          break
        case 'OPTIMIZE':
          result = await this.optimize(payload.code, payload.language)
          break
        case 'SUMMARIZE':
          result = await this.summarize(payload.text)
          break
        case 'TRANSLATE':
          result = await this.translate(payload.text, payload.language)
          break
        case 'DETECT_SECURITY':
          result = await this.detectSecurity(payload.code, payload.language)
          break
        case 'GET_SETTINGS':
          result = this.settings
          break
        case 'SAVE_SETTINGS':
          await this.saveSettings(payload.settings)
          result = { success: true }
          break
        case 'GET_HISTORY':
          result = this.getHistory()
          break
        case 'CLEAR_HISTORY':
          this.clearHistory()
          result = { success: true }
          break
        default:
          throw new Error(`Unknown message type: ${type}`)
      }

      sendResponse({ success: true, data: result, requestId })
    } catch (error) {
      sendResponse({ success: false, error: error.message, requestId })
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
        model: this.settings.model,
        max_tokens: this.settings.maxTokens,
        temperature: this.settings.temperature
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
    this.queueEvent('chat_completed', { messageId: aiMessage.id })
    return aiMessage
  }

  async explain(code, language) {
    const prompt = `Explain this ${language || ''} code concisely:\n\n\`\`\`\n${code}\n\`\`\``
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

  async review(code, language = '') {
    const prompt = `Review this ${language || ''} code for bugs, security issues, and improvements:\n\n\`\`\`\n${code}\n\`\`\``
    return this.chat(prompt)
  }

  async document(code, language = '') {
    const prompt = `Generate documentation for this ${language || ''} code:\n\n\`\`\`\n${code}\n\`\`\``
    return this.chat(prompt)
  }

  async fixBug(code, bugDescription, language) {
    const prompt = `Fix this bug in ${language || ''} code. Bug description: ${bugDescription}\n\n\`\`\`\n${code}\n\`\`\``
    return this.chat(prompt)
  }

  async optimize(code, language = '') {
    const prompt = `Optimize this ${language || ''} code for performance:\n\n\`\`\`\n${code}\n\`\`\``
    return this.chat(prompt)
  }

  async summarize(text) {
    const prompt = `Summarize the following content concisely:\n\n${text}`
    return this.chat(prompt)
  }

  async translate(text, language) {
    const prompt = `Translate the following to ${language}:\n\n${text}`
    return this.chat(prompt)
  }

  async detectSecurity(code, language) {
    const prompt = `Analyze this ${language || ''} code for security vulnerabilities (OWASP Top 10):\n\n\`\`\`\n${code}\n\`\`\``
    return this.chat(prompt)
  }

  getHistory() {
    return [...this.messages]
  }

  clearHistory() {
    this.messages = []
    this.conversationId = this.generateConversationId()
  }

  isConfigured() {
    return !!this.settings.apiKey
  }

  queueEvent(type, data) {
    this.eventQueue.push({ type, data, timestamp: Date.now() })
    if (this.eventQueue.length >= 10) {
      this.flushEvents()
    }
  }

  async flushEvents() {
    if (this.isProcessing || this.eventQueue.length === 0) return
    this.isProcessing = true

    const events = [...this.eventQueue]
    this.eventQueue = []

    try {
      if (typeof chrome !== 'undefined' && chrome.runtime?.sendMessage) {
        chrome.runtime.sendMessage({ type: 'FLUSH_EVENTS', events })
      }
    } catch {
      console.error('Failed to flush events:', e)
    } finally {
      this.isProcessing = false
    }
  }

  generateConversationId() {
    return `browser-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`
  }
}

const extensionCore = new ExtensionCore()
if (typeof window !== 'undefined') {
  window.AstrovoxCore = extensionCore
}
if (typeof self !== 'undefined' && typeof window === 'undefined') {
  self.AstrovoxCore = extensionCore
}

export { ExtensionCore }
export default extensionCore
