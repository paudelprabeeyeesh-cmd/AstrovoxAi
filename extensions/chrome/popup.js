import { AstrovoxCore } from '../shared/core.js'

class AstrovoxPopup {
  constructor() {
    this.core = null
  }

  async init() {
    this.core = window.AstrovoxCore || new AstrovoxCore()
    if (this.core.init) {
      await this.core.init()
    }
    this.attachListeners()
  }

  attachListeners() {
    const sendBtn = document.getElementById('send')
    const input = document.getElementById('input')
    const responseDiv = document.getElementById('response')
    const copyBtn = document.getElementById('copy')
    const clearBtn = document.getElementById('clear')

    sendBtn?.addEventListener('click', async () => {
      const text = input?.value.trim()
      if (!text) return

      responseDiv.style.display = 'block'
      responseDiv.textContent = 'Thinking...'
      responseDiv.className = 'popup-response'

      try {
        const res = await chrome.runtime.sendMessage({ type: 'CHAT', payload: { message: text } })
        if (res.error) {
          responseDiv.textContent = res.error
          responseDiv.classList.add('popup-error')
        } else {
          responseDiv.textContent = res.content || JSON.stringify(res)
        }
      } catch (e) {
        responseDiv.textContent = 'Failed to send message'
        responseDiv.classList.add('popup-error')
      }
    })

    input?.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) {
        sendBtn?.click()
      }
    })

    copyBtn?.addEventListener('click', async () => {
      const text = responseDiv?.textContent
      if (text) {
        try {
          await navigator.clipboard.writeText(text)
          copyBtn.textContent = 'Copied!'
          setTimeout(() => { copyBtn.textContent = 'Copy' }, 2000)
        } catch (err) {
          console.error('Copy failed:', err)
        }
      }
    })

    clearBtn?.addEventListener('click', () => {
      if (responseDiv) {
        responseDiv.style.display = 'none'
        responseDiv.textContent = ''
        responseDiv.className = 'popup-response'
      }
      if (input) input.value = ''
    })
  }
}

window.AstrovoxPopup = new AstrovoxPopup()
window.AstrovoxPopup.init().catch(console.error)
