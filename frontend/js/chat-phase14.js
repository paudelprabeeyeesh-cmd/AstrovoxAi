/* Phase 14 Chat Interface JavaScript */
class ChatInterface {
  constructor() {
    this.apiBase = '/api';
    this.currentConversationId = null;
    this.messages = [];
    this.memoryEnabled = true;
    this.user = null;
    this.init();
  }

  init() {
    this.bindEvents();
    this.checkAuth();
    this.loadConversations();
    this.newConversation();
  }

  bindEvents() {
    document.getElementById('new-chat')?.addEventListener('click', () => this.newConversation());
    document.getElementById('chat-form')?.addEventListener('submit', (e) => this.handleSubmit(e));
    document.getElementById('clear-chat')?.addEventListener('click', () => this.clearChat());
    document.getElementById('toggle-memory')?.addEventListener('click', () => this.toggleMemory());
    document.getElementById('logout-btn')?.addEventListener('click', () => this.logout());
    document.getElementById('message-input')?.addEventListener('input', (e) => this.updateInputMeta(e));
    document.getElementById('message-input')?.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        document.getElementById('chat-form')?.dispatchEvent(new Event('submit'));
      }
    });
    document.querySelectorAll('.suggestion-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        const input = document.getElementById('message-input');
        if (input) {
          input.value = btn.dataset.prompt;
          this.updateInputMeta({ target: input });
          document.getElementById('chat-form')?.dispatchEvent(new Event('submit'));
        }
      });
    });
  }

  updateInputMeta(e) {
    const input = e.target;
    const text = input.value;
    document.getElementById('char-count').textContent = `${text.length} characters`;
    document.getElementById('token-count').textContent = `${Math.ceil(text.length / 4)} tokens`;
    document.getElementById('send-btn').disabled = !text.trim();
  }

  async checkAuth() {
    const token = localStorage.getItem('access_token');
    if (!token) {
      window.location.href = '/login.html';
      return;
    }
    try {
      const response = await fetch(`${this.apiBase}/auth/me`, {
        headers: { 'Authorization': `Bearer ${token}` },
      });
      if (response.ok) {
        this.user = await response.json();
        document.getElementById('user-email').textContent = this.user.email;
      } else {
        localStorage.removeItem('access_token');
        window.location.href = '/login.html';
      }
    } catch (error) {
      console.error('Auth check failed:', error);
    }
  }

  newConversation() {
    this.currentConversationId = `conv-${Date.now()}`;
    this.messages = [];
    this.renderMessages();
    document.getElementById('welcome-screen').style.display = 'flex';
  }

  async loadConversations() {
    try {
      const response = await fetch(`${this.apiBase}/conversations`);
      const conversations = await response.json();
      const container = document.getElementById('conversations');
      if (!container) return;
      container.innerHTML = conversations.map(c => `
        <div class="conversation-item" data-id="${c.id}">
          ${c.title || 'New conversation'}
        </div>
      `).join('');
      container.querySelectorAll('.conversation-item').forEach(item => {
        item.addEventListener('click', () => this.loadConversation(item.dataset.id));
      });
    } catch (error) {
      console.error('Failed to load conversations:', error);
    }
  }

  async loadConversation(conversationId) {
    this.currentConversationId = conversationId;
    document.querySelectorAll('.conversation-item').forEach(i => i.classList.remove('active'));
    document.querySelector(`.conversation-item[data-id="${conversationId}"]`)?.classList.add('active');
    try {
      const response = await fetch(`${this.apiBase}/conversations/${conversationId}/messages`);
      this.messages = await response.json();
      document.getElementById('welcome-screen').style.display = 'none';
      this.renderMessages();
    } catch (error) {
      console.error('Failed to load conversation:', error);
    }
  }

  async handleSubmit(e) {
    e.preventDefault();
    const input = document.getElementById('message-input');
    const content = input.value.trim();
    if (!content) return;

    if (!this.currentConversationId) {
      this.newConversation();
    }

    const userMessage = { id: Date.now(), role: 'user', content, created_at: new Date().toISOString() };
    this.messages.push(userMessage);
    this.renderMessages();
    input.value = '';
    this.updateInputMeta({ target: input });
    document.getElementById('welcome-screen').style.display = 'none';

    await this.streamResponse(content);
  }

  async streamResponse(content) {
    const indicator = document.getElementById('typing-indicator');
    indicator.style.display = 'flex';

    const token = localStorage.getItem('access_token');
    const model = document.getElementById('model-select')?.value || 'gpt-4';

    try {
      const response = await fetch(`${this.apiBase}/chat/message`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify({
          conversation_id: this.currentConversationId,
          message: content,
          model: model,
          stream: true,
        }),
      });

      if (!response.ok) {
        throw new Error('Failed to send message');
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let aiContent = '';

      const aiMessage = {
        id: Date.now() + 1,
        role: 'assistant',
        content: '',
        created_at: new Date().toISOString(),
      };
      this.messages.push(aiMessage);
      this.renderMessages();

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        const chunk = decoder.decode(value);
        const lines = chunk.split('\n');
        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const data = line.slice(6);
            if (data === '[DONE]') continue;
            try {
              const parsed = JSON.parse(data);
              if (parsed.delta) {
                aiContent += parsed.delta;
                aiMessage.content = aiContent;
                this.updateLastMessage(aiContent);
              }
            } catch (parseError) {
              aiContent += data;
              aiMessage.content = aiContent;
              this.updateLastMessage(aiContent);
            }
          }
        }
      }

      if (this.memoryEnabled) {
        await this.saveMemory(content, aiContent);
      }

    } catch (error) {
      console.error('Stream error:', error);
      this.messages.push({
        id: Date.now() + 1,
        role: 'assistant',
        content: `Error: ${error.message}`,
        created_at: new Date().toISOString(),
      });
      this.renderMessages();
    } finally {
      indicator.style.display = 'none';
    }
  }

  updateLastMessage(content) {
    const messagesContainer = document.getElementById('messages');
    const lastMessage = messagesContainer.querySelector('.message:last-child .message-bubble');
    if (lastMessage) {
      lastMessage.innerHTML = this.renderMarkdown(content);
      this.scrollToBottom();
    }
  }

  renderMessages() {
    const container = document.getElementById('messages');
    if (!container) return;
    container.innerHTML = this.messages.map(msg => `
      <div class="message ${msg.role}">
        <div class="message-bubble">
          ${msg.role === 'assistant' ? this.renderMarkdown(msg.content) : this.escapeHtml(msg.content)}
          <div class="message-meta">
            <span>${new Date(msg.created_at).toLocaleTimeString()}</span>
            <div class="message-actions">
              <button onclick="chat.copyMessage(${msg.id})">Copy</button>
              ${msg.role === 'user' ? `<button onclick="chat.editMessage(${msg.id})">Edit</button>` : ''}
            </div>
          </div>
        </div>
      </div>
    `).join('');
    this.scrollToBottom();
  }

  renderMarkdown(text) {
    if (!text) return '';
    let html = text
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;');
    html = html.replace(/```(\w+)?\n([\s\S]*?)```/g, '<pre><code class="language-$1">$2</code></pre>');
    html = html.replace(/`([^`]+)`/g, '<code>$1</code>');
    html = html.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
    html = html.replace(/\*([^*]+)\*/g, '<em>$1</em>');
    html = html.replace(/^### (.*$)/gim, '<h3>$1</h3>');
    html = html.replace(/^## (.*$)/gim, '<h2>$1</h2>');
    html = html.replace(/^# (.*$)/gim, '<h1>$1</h1>');
    html = html.replace(/^\- (.*$)/gim, '<li>$1</li>');
    html = html.replace(/\n/g, '<br>');
    return html;
  }

  escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }

  scrollToBottom() {
    const container = document.getElementById('messages-container');
    if (container) container.scrollTop = container.scrollHeight;
  }

  async saveMemory(userContent, aiContent) {
    try {
      const token = localStorage.getItem('access_token');
      await fetch(`${this.apiBase}/memory/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify({
          content: `User: ${userContent}\nAI: ${aiContent}`,
          conversation_id: this.currentConversationId,
          user_id: this.user?.id || 'user',
          importance: 0.5,
        }),
      });
      this.loadMemories();
    } catch (error) {
      console.error('Failed to save memory:', error);
    }
  }

  async loadMemories() {
    try {
      const response = await fetch(`${this.apiBase}/memory/search?q=recent&limit=5`);
      const memories = await response.json();
      const container = document.getElementById('memory-content');
      if (!container) return;
      if (!memories || memories.length === 0) {
        container.innerHTML = '<p class="memory-placeholder">No memories yet.</p>';
        return;
      }
      container.innerHTML = memories.map(m => `
        <div class="memory-item">
          <div class="memory-item-header">
            <span class="memory-importance">${(m[1] * 100).toFixed(0)}% match</span>
            <span>${new Date(m[0].created_at).toLocaleDateString()}</span>
          </div>
          <p>${m[0].content.substring(0, 200)}...</p>
        </div>
      `).join('');
    } catch (error) {
      console.error('Failed to load memories:', error);
    }
  }

  toggleMemory() {
    this.memoryEnabled = !this.memoryEnabled;
    const btn = document.getElementById('toggle-memory');
    const panel = document.getElementById('memory-panel');
    if (btn) btn.textContent = `Memory: ${this.memoryEnabled ? 'ON' : 'OFF'}`;
    if (panel) {
      panel.classList.toggle('open', this.memoryEnabled);
      if (this.memoryEnabled) this.loadMemories();
    }
  }

  clearChat() {
    this.messages = [];
    this.renderMessages();
    document.getElementById('welcome-screen').style.display = 'flex';
  }

  copyMessage(id) {
    const msg = this.messages.find(m => m.id === id);
    if (msg) {
      navigator.clipboard.writeText(msg.content);
    }
  }

  editMessage(id) {
    const msg = this.messages.find(m => m.id === id);
    if (!msg) return;
    const newContent = prompt('Edit message:', msg.content);
    if (newContent !== null && newContent.trim()) {
      msg.content = newContent.trim();
      this.renderMessages();
    }
  }

  async logout() {
    localStorage.removeItem('access_token');
    window.location.href = '/login.html';
  }
}

let chat;
document.addEventListener('DOMContentLoaded', () => {
  chat = new ChatInterface();
});
