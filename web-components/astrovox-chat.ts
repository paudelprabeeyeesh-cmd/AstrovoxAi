import { html, css, customElement, property } from 'lit'
import { classMap } from 'lit/directives/class-map.js'
import { styleMap } from 'lit/directives/style-map.js'

@customElement('astrovox-chat')
export class AstrovoxChat extends HTMLElement {
  @property({ type: String }) apiKey = ''
  @property({ type: String }) theme = 'dark'
  @property({ type: Boolean }) enableVoice = false
  @property({ type: Boolean }) enableBranching = false
  @property({ type: String }) placeholder = 'Type your message...'

  static styles = css`
    :host {
      display: block;
      font-family: var(--astrovox-font-sans, 'Inter', sans-serif);
      --astrovox-bg: #02040a;
      --astrovox-surface: #0f172a;
      --astrovox-border: #1e293b;
      --astrovox-text: #e2e8f0;
      --astrovox-text-muted: #64748b;
      --astrovox-primary: #06b6d4;
      --astrovox-accent: #67e8f9;
    }
    .container {
      display: flex;
      flex-direction: column;
      height: 100%;
      background: var(--astrovox-bg);
      border: 1px solid var(--astrovox-border);
      border-radius: 12px;
      overflow: hidden;
    }
    .header {
      padding: 12px 16px;
      border-bottom: 1px solid var(--astrovox-border);
      background: var(--astrovox-surface);
    }
    .header-title {
      margin: 0;
      font-size: 14px;
      color: var(--astrovox-accent);
      letter-spacing: 1px;
      font-weight: 600;
    }
    .messages {
      flex: 1;
      overflow-y: auto;
      padding: 16px;
      display: flex;
      flex-direction: column;
      gap: 12px;
    }
    .message {
      max-width: 75%;
      padding: 12px 16px;
      border-radius: 12px;
      font-size: 13px;
      line-height: 1.6;
      word-wrap: break-word;
    }
    .message.user {
      align-self: flex-end;
      background: var(--astrovox-primary);
      color: var(--astrovox-bg);
    }
    .message.assistant {
      align-self: flex-start;
      background: var(--astrovox-surface);
      border: 1px solid var(--astrovox-border);
      color: var(--astrovox-text);
    }
    .input-area {
      padding: 12px 16px;
      border-top: 1px solid var(--astrovox-border);
      background: var(--astrovox-surface);
      display: flex;
      gap: 8px;
    }
    .input {
      flex: 1;
      padding: 10px 14px;
      border: 1px solid var(--astrovox-border);
      border-radius: 24px;
      background: var(--astrovox-bg);
      color: var(--astrovox-text);
      font-size: 13px;
      font-family: inherit;
      outline: none;
    }
    .input:focus {
      border-color: var(--astrovox-primary);
    }
    .send-btn {
      padding: 0 20px;
      background: var(--astrovox-primary);
      color: var(--astrovox-bg);
      border: none;
      border-radius: 24px;
      cursor: pointer;
      font-weight: 700;
      font-size: 12px;
      font-family: inherit;
    }
    .empty-state {
      text-align: center;
      color: var(--astrovox-text-muted);
      padding: 40px 20px;
      font-size: 13px;
    }
  `

  messages: any[] = []
  input = ''

  render() {
    return html`
      <div class="container">
        <div class="header">
          <h3 class="header-title">ASTROVOX AI</h3>
        </div>
        <div class="messages" role="log" aria-live="polite">
          ${this.messages.length === 0
            ? html`<div class="empty-state">Start a conversation!</div>`
            : this.messages.map(msg => html`
              <div class=${classMap({ message: true, user: msg.role === 'user', assistant: msg.role === 'assistant' })}>
                ${msg.content}
              </div>
            `)
          }
        </div>
        <div class="input-area">
          <input
            class="input"
            type="text"
            placeholder=${this.placeholder}
            .value=${this.input}
            @input=${this.handleInput}
            @keydown=${this.handleKeyDown}
            aria-label="Message input"
          />
          <button class="send-btn" @click=${this.sendMessage}>SEND</button>
        </div>
      </div>
    `
  }

  handleInput(e: any) {
    this.input = e.target.value
  }

  handleKeyDown(e: KeyboardEvent) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      this.sendMessage()
    }
  }

  async sendMessage() {
    if (!this.input.trim()) return
    this.messages = [...this.messages, { role: 'user', content: this.input }]
    const userMessage = this.input
    this.input = ''

    const response = await fetch('https://api.astrovox.ai/v1/chat/message', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${this.apiKey}`
      },
      body: JSON.stringify({ conversation_id: 'default', message: userMessage, model: 'gpt-4' })
    })

    const result = await response.json()
    this.messages = [...this.messages, result.ai_message]
  }
}

declare global {
  interface HTMLElementTagNameMap {
    'astrovox-chat': AstrovoxChat
  }
}
