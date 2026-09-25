import { AstrovoxCore } from '../shared/core.js'

class AstrovoxContent {
  constructor() {
    this.core = null
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
    if (document.getElementById('astrovox-floating-btn')) return

    const btn = document.createElement('button')
    btn.id = 'astrovox-floating-btn'
    btn.innerHTML = '&#129302;'
    btn.title = 'Open Astrovox AI'
    document.body.appendChild(btn)
  }

  attachListeners() {
    document.addEventListener('keydown', (e) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault()
        this.core?.clearHistory()
        this.showToast('Conversation cleared')
      }
    })

    chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
      if (msg.type === 'EXPLAIN_SELECTION') {
        this.core?.explain(msg.text).then(response => {
          this.showToast(`Explanation: ${response?.content?.slice(0, 200)}...`)
        }).catch(() => {})
      }
      if (msg.type === 'SUMMARIZE_SELECTION') {
        this.core?.summarize(msg.text).then(response => {
          this.showToast(`Summary: ${response?.content?.slice(0, 200)}...`)
        }).catch(() => {})
      }
    })
  }

  showToast(message) {
    const existing = document.querySelector('.astrovox-toast')
    if (existing) existing.remove()

    const toast = document.createElement('div')
    toast.className = 'astrovox-toast'
    toast.textContent = message
    Object.assign(toast.style, {
      position: 'fixed',
      bottom: '80px',
      right: '20px',
      background: '#02040a',
      border: '1px solid #1e293b',
      borderRadius: '8px',
      padding: '12px 16px',
      color: '#e2e8f0',
      fontFamily: 'monospace',
      fontSize: '12px',
      zIndex: '2147483647',
      boxShadow: '0 4px 20px rgba(0,0,0,0.4)',
      maxWidth: '300px'
    })
    document.body.appendChild(toast)
    setTimeout(() => toast.remove(), 4000)
  }
}

window.AstrovoxContent = new AstrovoxContent()
window.AstrovoxContent.init().catch(console.error)
