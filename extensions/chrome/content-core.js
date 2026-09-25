import { AstrovoxCore } from '../shared/core.js'

class AstrovoxContentScript {
  constructor() {
    this.core = null
    this.isOpen = false
    this.highlightedElements = new Map()
  }

  async init() {
    this.core = window.AstrovoxCore || new AstrovoxCore()
    if (this.core.init) {
      await this.core.init()
    }
    this.injectStyles()
    this.setupKeyboardShortcuts()
  }

  injectStyles() {
    if (document.getElementById('astrovox-extension-styles')) return

    const style = document.createElement('style')
    style.id = 'astrovox-extension-styles'
    style.textContent = `
      .astrovox-highlight {
        background: rgba(6, 182, 212, 0.15) !important;
        border-bottom: 2px solid #06b6d4 !important;
        cursor: pointer !important;
        transition: background 0.2s ease !important;
      }
      .astrovox-highlight:hover {
        background: rgba(6, 182, 212, 0.3) !important;
      }
      .astrovox-tooltip {
        position: absolute;
        background: #02040a;
        border: 1px solid #1e293b;
        border-radius: 8px;
        padding: 12px;
        color: #e2e8f0;
        font-family: monospace;
        font-size: 12px;
        max-width: 300px;
        z-index: 2147483647;
        box-shadow: 0 4px 20px rgba(0,0,0,0.4);
        display: none;
      }
      .astrovox-tooltip.visible {
        display: block;
      }
      .astrovox-floating-btn {
        position: fixed;
        bottom: 20px;
        right: 20px;
        width: 48px;
        height: 48px;
        border-radius: 50%;
        background: linear-gradient(135deg, #06b6d4, #3b82f6);
        border: none;
        color: #02040a;
        font-size: 20px;
        cursor: pointer;
        z-index: 2147483647;
        box-shadow: 0 4px 14px rgba(6, 182, 212, 0.4);
        display: flex;
        align-items: center;
        justify-content: center;
        transition: transform 0.2s ease;
      }
      .astrovox-floating-btn:hover {
        transform: scale(1.1);
      }
      .astrovox-sidebar {
        position: fixed;
        top: 0;
        right: -400px;
        width: 380px;
        height: 100vh;
        background: #02040a;
        border-left: 1px solid #1e293b;
        z-index: 2147483646;
        transition: right 0.3s ease;
        display: flex;
        flex-direction: column;
        font-family: monospace;
        box-shadow: -4px 0 20px rgba(0,0,0,0.3);
      }
      .astrovox-sidebar.open {
        right: 0;
      }
    `
    document.head.appendChild(style)
  }

  setupKeyboardShortcuts() {
    document.addEventListener('keydown', (e) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault()
        this.toggleSidebar()
      }
      if (e.key === 'Escape' && this.isOpen) {
        this.toggleSidebar()
      }
    })
  }

  toggleSidebar() {
    this.isOpen = !this.isOpen
    const sidebar = document.querySelector('.astrovox-sidebar')
    if (sidebar) {
      sidebar.classList.toggle('open', this.isOpen)
    }
  }

  async summarizePage() {
    const mainContent = document.body.innerText || document.body.textContent || ''
    const truncated = mainContent.slice(0, 8000)
    try {
      const response = await this.core.summarize(truncated)
      this.showTooltip(`Summary: ${response.content}`, 5000)
      return response
    } catch (e) {
      console.error('Summarize failed:', e)
      return null
    }
  }

  showTooltip(text, duration = 3000) {
    let tooltip = document.querySelector('.astrovox-tooltip')
    if (!tooltip) {
      tooltip = document.createElement('div')
      tooltip.className = 'astrovox-tooltip'
      document.body.appendChild(tooltip)
    }
    tooltip.textContent = text
    tooltip.classList.add('visible')
    tooltip.style.left = '20px'
    tooltip.style.top = '20px'
    setTimeout(() => tooltip.classList.remove('visible'), duration)
  }

  highlightElements(selector) {
    document.querySelectorAll(selector).forEach(el => {
      if (!this.highlightedElements.has(el)) {
        el.classList.add('astrovox-highlight')
        this.highlightedElements.set(el, true)
      }
    })
  }
}

window.AstrovoxContentScript = new AstrovoxContentScript()
window.AstrovoxContentScript.init().catch(console.error)
