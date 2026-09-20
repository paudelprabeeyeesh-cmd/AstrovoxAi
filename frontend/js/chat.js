const API_BASE = (() => {
  try {
    return localStorage.getItem('api_base') || 'http://localhost:8000';
  } catch {
    return 'http://localhost:8000';
  }
})();

function getToken() {
  try {
    return localStorage.getItem('astrovox_access_token');
  } catch {
    return null;
  }
}

function formatTime(date) {
  return new Date(date).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}

function showError(message) {
  let container = document.getElementById('toast-container');
  if (!container) {
    container = document.createElement('div');
    container.id = 'toast-container';
    container.className = 'toast-container';
    document.body.appendChild(container);
  }
  const toast = document.createElement('div');
  toast.className = 'toast error';
  toast.textContent = message;
  container.appendChild(toast);
  setTimeout(() => {
    toast.style.opacity = '0';
    toast.style.transform = 'translateX(100%)';
    toast.style.transition = 'all 0.3s ease';
    setTimeout(() => toast.remove(), 300);
  }, 4000);
}

function showToast(message, type = 'success') {
  let container = document.getElementById('toast-container');
  if (!container) {
    container = document.createElement('div');
    container.id = 'toast-container';
    container.className = 'toast-container';
    document.body.appendChild(container);
  }
  const toast = document.createElement('div');
  toast.className = `toast ${type}`;
  toast.textContent = message;
  container.appendChild(toast);
  setTimeout(() => {
    toast.style.opacity = '0';
    toast.style.transform = 'translateX(100%)';
    toast.style.transition = 'all 0.3s ease';
    setTimeout(() => toast.remove(), 300);
  }, 3000);
}

class ChatAPI {
  static async solve(text, conversationId = null, onChunk = null) {
    const token = getToken();
    const res = await fetch(`${API_BASE}/solve`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: JSON.stringify({ text, conversation_id: conversationId }),
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'Request failed' }));
      throw new Error(err.detail || err.result || `HTTP ${res.status}`);
    }

    if (onChunk && res.headers.get('content-type')?.includes('text/event-stream')) {
      return ChatAPI._readStream(res, onChunk);
    }

    const data = await res.json();
    return data;
  }

  static async solveStream(text, conversationId = null, onChunk = null, onDone = null, onError = null) {
    const token = getToken();
    try {
      const res = await fetch(`${API_BASE}/solve/stream`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify({ text, conversation_id: conversationId }),
      });

      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: 'Request failed' }));
        const msg = err.detail || err.error || `HTTP ${res.status}`;
        if (onError) onError(new Error(msg));
        return;
      }

      if (!res.body) {
        if (onError) onError(new Error('No response body'));
        return;
      }

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';

        for (const line of lines) {
          const trimmed = line.trim();
          if (!trimmed || trimmed === 'data: [DONE]') {
            if (trimmed === 'data: [DONE]' && onDone) onDone();
            continue;
          }
          if (trimmed.startsWith('data: ')) {
            const payload = trimmed.slice(6);
            try {
              const data = JSON.parse(payload);
              if (data.error) {
                if (onError) onError(new Error(data.error));
                return;
              }
              if (onChunk) onChunk(data);
            } catch {
              // skip malformed JSON
            }
          }
        }
      }

      if (onDone) onDone();
    } catch (err) {
      if (onError) onError(err);
    }
  }

  static async _readStream(res, onChunk) {
      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let fullText = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        const text = decoder.decode(value, { stream: true });
        fullText += text;
        if (onChunk) onChunk(text);
      }
      return { text: fullText };
    }

  static async createConversation(title) {
    const token = getToken();
    const res = await fetch(`${API_BASE}/conversations`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: JSON.stringify({ title }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'Failed' }));
      throw new Error(err.detail || 'Failed to create conversation');
    }
    return res.json();
  }

  static async getConversations() {
    const token = getToken();
    const res = await fetch(`${API_BASE}/conversations`, {
      headers: {
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
    });
    if (!res.ok) throw new Error('Failed to load conversations');
    return res.json();
  }

  static async getMessages(conversationId) {
    const token = getToken();
    const res = await fetch(`${API_BASE}/conversations/${encodeURIComponent(conversationId)}/messages`, {
      headers: {
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
    });
    if (!res.ok) throw new Error('Failed to load messages');
    return res.json();
  }
}

class WebSocketManager {
  constructor(url, sessionId) {
    this.url = url;
    this.sessionId = sessionId;
    this.ws = null;
    this.listeners = new Map();
    this.reconnectAttempts = 0;
    this.maxReconnectAttempts = 5;
    this.reconnectDelay = 1000;
    this.intentionalClose = false;
    this.heartbeatInterval = null;
  }

  connect() {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) return;

    this.intentionalClose = false;
    const token = getToken();
    const wsUrl = `${this.url}/ws/chat/${this.sessionId}?token=${encodeURIComponent(token || '')}`;

    try {
      this.ws = new WebSocket(wsUrl);
    } catch {
      this._scheduleReconnect();
      return;
    }

    this.ws.onopen = () => {
      this.reconnectAttempts = 0;
      this._startHeartbeat();
      this._emit('connected');
    };

    this.ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        this._emit('message', data);
      } catch {
        this._emit('message', { text: event.data });
      }
    };

    this.ws.onerror = () => {
      this._emit('error');
    };

    this.ws.onclose = (event) => {
      this._stopHeartbeat();
      this._emit('disconnected', { code: event.code, reason: event.reason });
      if (!this.intentionalClose) {
        this._scheduleReconnect();
      }
    };
  }

  send(data) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(data));
    }
  }

  close() {
    this.intentionalClose = true;
    this._stopHeartbeat();
    if (this.ws) {
      this.ws.close(1000);
    }
  }

  on(event, callback) {
    if (!this.listeners.has(event)) {
      this.listeners.set(event, []);
    }
    this.listeners.get(event).push(callback);
    return () => {
      const cbs = this.listeners.get(event) || [];
      const idx = cbs.indexOf(callback);
      if (idx >= 0) cbs.splice(idx, 1);
    };
  }

  _emit(event, data) {
    const cbs = this.listeners.get(event) || [];
    cbs.forEach(cb => {
      try { cb(data); } catch {}
    });
  }

  _scheduleReconnect() {
    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      this._emit('reconnect_failed');
      return;
    }
    const delay = this.reconnectDelay * Math.pow(2, this.reconnectAttempts);
    this._emit('reconnecting', { attempt: this.reconnectAttempts + 1, delay });
    setTimeout(() => {
      this.reconnectAttempts++;
      this.connect();
    }, delay);
  }

  _startHeartbeat() {
    this._stopHeartbeat();
    this.heartbeatInterval = setInterval(() => {
      if (this.ws && this.ws.readyState === WebSocket.OPEN) {
        this.ws.send(JSON.stringify({ type: 'ping' }));
      }
    }, 30000);
  }

  _stopHeartbeat() {
    if (this.heartbeatInterval) {
      clearInterval(this.heartbeatInterval);
      this.heartbeatInterval = null;
    }
  }
}

class ChatApp {
  constructor() {
    this.messages = [];
    this.conversations = [];
    this.activeConversationId = null;
    this.isLoading = false;
    this.isStreaming = false;
    this.currentStreamingMsgId = null;
    this.wsManager = null;
    this.abortController = null;
    this.selectedModel = 'gpt-4o';

    this.messageListEl = document.getElementById('chat-messages');
    this.messageInputEl = document.getElementById('message-input');
    this.sendBtnEl = document.getElementById('send-btn');
    this.stopBtnEl = document.getElementById('stop-btn');
    this.conversationListEl = document.getElementById('conversation-list');
    this.newChatBtnEl = document.getElementById('new-chat-btn');
    this.connectionStatusEl = document.getElementById('connection-status');
    this.modelSelectEl = document.getElementById('model-select');

    this._bindEvents();
    this._init();
  }

  _bindEvents() {
    if (this.sendBtnEl) {
      this.sendBtnEl.addEventListener('click', () => this._handleSend());
    }
    if (this.stopBtnEl) {
      this.stopBtnEl.addEventListener('click', () => this._handleStop());
    }
    if (this.messageInputEl) {
      this.messageInputEl.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
          e.preventDefault();
          this._handleSend();
        }
      });
    }
    if (this.newChatBtnEl) {
      this.newChatBtnEl.addEventListener('click', () => this._newConversation());
    }
    if (this.modelSelectEl) {
      this.modelSelectEl.addEventListener('change', (e) => {
        this.selectedModel = e.target.value;
      });
    }
  }

  async _init() {
    this._setLoading(true);
    try {
      await this._loadConversations();
      if (this.conversations.length > 0) {
        await this._loadConversation(this.conversations[0].id);
      }
    } catch (err) {
      showError('Failed to initialize chat: ' + err.message);
    } finally {
      this._setLoading(false);
    }
  }

  async _loadConversations() {
    try {
      this.conversations = await ChatAPI.getConversations();
      this._renderConversationList();
    } catch (err) {
      console.error('Failed to load conversations:', err);
    }
  }

  async _loadConversation(id) {
    this.activeConversationId = id;
    this._renderConversationList();
    try {
      const msgs = await ChatAPI.getMessages(id);
      this.messages = msgs.map(m => ({
        id: m.id,
        role: m.role,
        content: m.content,
        createdAt: m.created_at,
      }));
      this._renderMessages();
    } catch (err) {
      showError('Failed to load messages: ' + err.message);
    }
  }

  async _newConversation() {
    try {
      const conv = await ChatAPI.createConversation('New Chat');
      this.conversations.unshift(conv);
      this._renderConversationList();
      await this._loadConversation(conv.id);
    } catch (err) {
      showError('Failed to create conversation: ' + err.message);
    }
  }

  async _handleSend() {
    if (!this.messageInputEl) return;
    const text = this.messageInputEl.value.trim();
    if (!text || this.isStreaming) return;

    this._appendMessage({ role: 'user', content: text });
    this.messageInputEl.value = '';
    this.messageInputEl.style.height = 'auto';
    this.isStreaming = true;
    this._updateUIState();

    const streamingMsgId = 'stream-' + Date.now();
    this.currentStreamingMsgId = streamingMsgId;
    this._appendMessage({ role: 'assistant', content: '', id: streamingMsgId, isStreaming: true });
    this.abortController = new AbortController();

    let conversationId = this.activeConversationId;
    if (!conversationId) {
      try {
        const conv = await ChatAPI.createConversation(text.slice(0, 50));
        conversationId = conv.id;
        this.conversations.unshift(conv);
        this.activeConversationId = conv.id;
        this._renderConversationList();
      } catch {
        // continue without conversation id
      }
    }

    try {
      await ChatAPI.solveStream(text, conversationId,
        (chunk) => {
          if (this.currentStreamingMsgId === streamingMsgId) {
            this._updateStreamingMessage(streamingMsgId, chunk.result || chunk.text || '');
          }
        },
        () => {
          this._finalizeStreamingMessage(streamingMsgId);
        },
        (err) => {
          this._handleStreamError(streamingMsgId, err.message);
        }
      );
    } catch (err) {
      this._handleStreamError(streamingMsgId, err.message);
    } finally {
      this.isStreaming = false;
      this.currentStreamingMsgId = null;
      this.abortController = null;
      this._updateUIState();
    }
  }

  _handleStop() {
    if (this.abortController) {
      this.abortController.abort();
    }
    if (this.wsManager) {
      this.wsManager.close();
    }
    this.isStreaming = false;
    this.currentStreamingMsgId = null;
    this.abortController = null;
    this._finalizeStreamingMessage(this.currentStreamingMsgId);
    this._updateUIState();
    showToast('Generation stopped');
  }

  _handleStreamError(msgId, errorMsg) {
    if (this.currentStreamingMsgId === msgId) {
      const msg = this.messages.find(m => m.id === msgId);
      if (msg) {
        msg.content = 'Sorry, something went wrong: ' + (errorMsg || 'Unknown error');
        msg.isStreaming = false;
        this._renderMessages();
      }
    }
  }

  _finalizeStreamingMessage(msgId) {
    const msg = this.messages.find(m => m.id === msgId);
    if (msg) {
      msg.isStreaming = false;
    }
    this._renderMessages();
  }

  _appendMessage({ role, content, id, isStreaming }) {
    this.messages.push({
      id: id || Date.now().toString(),
      role,
      content,
      createdAt: new Date(),
      isStreaming: isStreaming || false,
    });
    this._renderMessages();
  }

  _updateStreamingMessage(msgId, content) {
    const msg = this.messages.find(m => m.id === msgId);
    if (msg) {
      msg.content = content;
      this._renderMessages();
    }
  }

  _renderMessages() {
    if (!this.messageListEl) return;
    const inner = this.messageListEl.querySelector('.chat-messages-inner') || this.messageListEl;
    if (!inner) return;

    if (this.messages.length === 0) {
      inner.innerHTML = `
        <div class="empty-state">
          <div class="empty-state-icon">💬</div>
          <h3>Start a conversation</h3>
          <p>Send a message to begin chatting with the AI assistant.</p>
        </div>
      `;
      return;
    }

    inner.innerHTML = this.messages.map(msg => {
      const isUser = msg.role === 'user';
      const avatar = isUser ? 'U' : 'AI';
      const streamingClass = msg.isStreaming ? 'message-streaming' : '';
      return `
        <div class="message ${msg.role} ${streamingClass}">
          <div class="message-avatar">${avatar}</div>
          <div class="message-content">
            <div class="message-bubble">${this._escapeHtml(msg.content)}</div>
            <div class="message-time">${formatTime(msg.createdAt)}</div>
          </div>
        </div>
      `;
    }).join('');

    inner.lastElementChild?.scrollIntoView({ behavior: 'smooth' });
  }

  _renderConversationList() {
    if (!this.conversationListEl) return;
    this.conversationListEl.innerHTML = this.conversations.map(conv => `
      <button class="conversation-item ${conv.id === this.activeConversationId ? 'active' : ''}"
              data-id="${conv.id}">
        ${this._escapeHtml(conv.title || 'Untitled Chat')}
      </button>
    `).join('');

    this.conversationListEl.querySelectorAll('.conversation-item').forEach(btn => {
      btn.addEventListener('click', () => {
        const id = btn.dataset.id;
        if (id) this._loadConversation(id);
      });
    });
  }

  _updateUIState() {
    if (this.sendBtnEl) this.sendBtnEl.style.display = this.isStreaming ? 'none' : 'inline-flex';
    if (this.stopBtnEl) this.stopBtnEl.style.display = this.isStreaming ? 'inline-flex' : 'none';
    if (this.messageInputEl) this.messageInputEl.disabled = this.isStreaming;
    this._updateConnectionStatus(this.isStreaming ? 'connecting' : 'connected');
  }

  _updateConnectionStatus(status) {
    if (!this.connectionStatusEl) return;
    this.connectionStatusEl.className = 'connection-status ' + status;
    const dot = this.connectionStatusEl.querySelector('.dot');
    const text = this.connectionStatusEl.querySelector('.status-text');
    if (dot) dot.style.background = status === 'connected' ? 'var(--success)' : status === 'connecting' ? 'var(--warning)' : 'var(--error)';
    if (text) text.textContent = status === 'connected' ? 'Connected' : status === 'connecting' ? 'Connecting...' : 'Disconnected';
  }

  _setLoading(loading) {
    this.isLoading = loading;
    if (this.messageInputEl) this.messageInputEl.disabled = loading;
  }

  _escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }
}

window.ChatApp = ChatApp;
