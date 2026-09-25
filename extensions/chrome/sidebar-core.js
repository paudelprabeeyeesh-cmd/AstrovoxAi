import { AstrovoxCore } from '../shared/core.js'

class AstrovoxSidebar {
  constructor() {
    this.core = null
    this.container = null
    this.isOpen = false
  }

  async init() {
    this.core = window.AstrovoxCore || new AstrovoxCore()
    if (this.core.init) {
      await this.core.init()
    }
    this.injectUI()
    this.attachListeners()
  }

  injectUI() {
    if (document.getElementById('astrovox-sidebar-container')) return

    this.container = document.createElement('div')
    this.container.id = 'astrovox-sidebar-container'
    this.container.innerHTML = `
      <div class="astrovox-sidebar-header">
        <span class="astrovox-logo">ASTROVOX</span>
        <button id="astrovox-close-sidebar" aria-label="Close sidebar">x</button>
      </div>
      <div class="astrovox-messages" id="astrovox-messages"></div>
      <form class="astrovox-form" id="astrovox-form">
        <input type="text" id="astrovox-input" placeholder="Ask anything..." autocomplete="off" />
        <button type="submit" id="astrovox-send">SEND</button>
      </form>
    `
    document.body.appendChild(this.container)
  }

  attachListeners() {
    const closeBtn = document.getElementById('astrovox-close-sidebar')
    const form = document.getElementById('astrovox-form')
    const input = document.getElementById('astrovox-input')

    closeBtn?.addEventListener('click', () => this.toggle())
    form?.addEventListener('submit', (e) => {
      e.preventDefault()
      this.handleSend(input?.value)
    })
  }

  toggle() {
    this.isOpen = !this.isOpen
    this.container.style.display = this.isOpen ? 'flex' : 'none'
  }

  async handleSend(message) {
    if (!message?.trim()) return
    this.addMessage('user', message)
    const input = document.getElementById('astrovox-input')
    input.value = ''

    try {
      const response = await this.core.chat(message)
      this.addMessage('assistant', response.content)
    } catch (e) {
      this.addMessage('error', `Error: ${e.message}`)
    }
  }

  addMessage(role, content) {
    const container = document.getElementById('astrovox-messages')
    if (!container) return

    const div = document.createElement('div')
    div.className = `astrovox-message astrovox-message-${role}`
    div.textContent = content
    container.appendChild(div)
    container.scrollTop = container.scrollHeight
  }
}

window.AstrovoxSidebar = new AstrovoxSidebar()
window.AstrovoxSidebar.init().catch(console.error)
