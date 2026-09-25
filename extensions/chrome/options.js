import { AstrovoxCore } from '../shared/core.js'

class AstrovoxOptions {
  constructor() {
    this.core = null
  }

  async init() {
    this.core = window.AstrovoxCore || new AstrovoxCore()
    if (this.core.init) {
      await this.core.init()
    }
    this.loadSettings()
    this.attachListeners()
  }

  loadSettings() {
    const fields = ['apiUrl', 'apiKey', 'model', 'autoSuggest', 'showHighlights']
    fields.forEach(field => {
      const el = document.getElementById(field)
      if (!el) return
      const value = this.core.settings[field]
      if (typeof value === 'boolean') {
        el.checked = value
      } else {
        el.value = value || ''
      }
    })
  }

  attachListeners() {
    const saveBtn = document.getElementById('save')
    const status = document.getElementById('status')

    saveBtn?.addEventListener('click', async () => {
      const settings = {
        apiUrl: document.getElementById('apiUrl')?.value || '',
        apiKey: document.getElementById('apiKey')?.value || '',
        model: document.getElementById('model')?.value || 'gpt-4',
        autoSuggest: document.getElementById('autoSuggest')?.checked || false,
        showHighlights: document.getElementById('showHighlights')?.checked !== false
      }

      await this.core.saveSettings(settings)

      if (status) {
        status.textContent = 'Settings saved'
        setTimeout(() => { status.textContent = '' }, 2000)
      }
    })

    const resetBtn = document.getElementById('reset')
    resetBtn?.addEventListener('click', async () => {
      await this.core.saveSettings({})
      this.loadSettings()
      if (status) {
        status.textContent = 'Settings reset'
        setTimeout(() => { status.textContent = '' }, 2000)
      }
    })
  }
}

window.AstrovoxOptions = new AstrovoxOptions()
window.AstrovoxOptions.init().catch(console.error)
