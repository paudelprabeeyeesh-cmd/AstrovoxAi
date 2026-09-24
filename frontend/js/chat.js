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

class SSEManager {
  constructor(url, options = {}) {
    this.url = url;
    this.options = {
      method: options.method || 'POST',
      headers: options.headers || {},
      body: options.body || null,
      reconnect: options.reconnect !== false,
      maxReconnectAttempts: options.maxReconnectAttempts || 10,
      reconnectDelay: options.reconnectDelay || 1000,
      maxReconnectDelay: options.maxReconnectDelay || 30000,
      eventId: options.eventId || null,
      lastEventId: options.lastEventId || null,
    };
    this.eventId = this.options.eventId;
    this.lastEventId = this.options.lastEventId;
    this.reconnectAttempts = 0;
    this.abortController = null;
    this.reader = null;
    this.isIntentionallyClosed = false;
    this.isConnecting = false;
    this.handlers = {};
    this.state = 'disconnected';
    this._reconnectTimer = null;
  }

  get connectionState() {
    return this.state;
  }

  on(event, handler) {
    if (!this.handlers[event]) this.handlers[event] = [];
    this.handlers[event].push(handler);
    return () => {
      this.handlers[event] = this.handlers[event].filter(h => h !== handler);
    };
  }

  _emit(event, data) {
    (this.handlers[event] || []).forEach(h => {
      try { h(data); } catch (e) { console.error('SSE handler error:', e); }
    });
  }

  _setState(state) {
    this.state = state;
    this._emit('state', state);
  }

  async connect() {
    if (this.isConnecting) return;
    this.isConnecting = true;
    this.isIntentionallyClosed = false;
    this.abortController = new AbortController();

    const headers = {
      'Content-Type': 'application/json',
      ...this.options.headers,
    };
    const effectiveEventId = this.eventId || this.lastEventId;
    if (effectiveEventId) {
      headers['Last-Event-ID'] = effectiveEventId;
    }

    try {
      this._setState('connecting');
      const res = await fetch(this.url, {
        method: this.options.method,
        headers,
        body: this.options.body ? JSON.stringify(this.options.body) : null,
        signal: this.abortController.signal,
      });

      if (!res.ok) {
        const err = new Error(`HTTP ${res.status}`);
        err.status = res.status;
        this._setState('error');
        this._emit('error', err);
        this._scheduleReconnect();
        return;
      }

      this.reconnectAttempts = 0;
      this._setState('open');
      this._emit('open');

      this.reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';

      try {
        while (true) {
          const { done, value } = await this.reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split('\n');
          buffer = lines.pop() || '';

          let currentEvent = 'message';
          let currentData = '';

          for (const line of lines) {
            const trimmed = line.trim();
            if (!trimmed || trimmed.startsWith(':')) continue;
            if (trimmed.startsWith('event:')) {
              currentEvent = trimmed.slice(6).trim();
            } else if (trimmed.startsWith('data:')) {
              currentData += trimmed.slice(5).trim();
            } else if (trimmed.startsWith('id:')) {
              this.eventId = trimmed.slice(3).trim();
              this.lastEventId = this.eventId;
            } else if (trimmed.startsWith('retry:')) {
              const retryMs = parseInt(trimmed.slice(6).trim(), 10);
              if (!isNaN(retryMs) && retryMs > 0) {
                this.options.reconnectDelay = Math.min(retryMs, this.options.maxReconnectDelay);
              }
            }
          }

          if (currentData) {
            try {
              const data = JSON.parse(currentData);
              this._emit(currentEvent, data);
            } catch {
              this._emit(currentEvent, currentData);
            }
          }
        }
      } catch (err) {
        if (err.name === 'AbortError') {
          this._setState('closed');
        } else {
          this._setState('error');
          this._emit('error', err);
        }
      } finally {
        this._emit('close');
        if (!this.isIntentionallyClosed) {
          this._scheduleReconnect();
        }
      }
    } catch (err) {
      if (err.name === 'AbortError') {
        this._setState('closed');
        this._emit('close');
      } else {
        this._setState('error');
        this._emit('error', err);
        this._scheduleReconnect();
      }
    } finally {
      this.isConnecting = false;
    }
  }

  _scheduleReconnect() {
    if (this.isIntentionallyClosed) return;
    if (!this.options.reconnect) return;
    if (this.reconnectAttempts >= this.options.maxReconnectAttempts) {
      this._setState('reconnect_failed');
      this._emit('reconnect_failed');
      return;
    }

    const baseDelay = this.options.reconnectDelay;
    const jitter = baseDelay * 0.1 * Math.random();
    const delay = Math.min(baseDelay * Math.pow(2, this.reconnectAttempts) + jitter, this.options.maxReconnectDelay);
    this._setState('reconnecting');
    this._emit('reconnecting', { attempt: this.reconnectAttempts + 1, delay: Math.round(delay) });
    this._reconnectTimer = setTimeout(() => {
      this.reconnectAttempts++;
      this.connect();
    }, delay);
  }

  close() {
    this.isIntentionallyClosed = true;
    if (this._reconnectTimer) {
      clearTimeout(this._reconnectTimer);
      this._reconnectTimer = null;
    }
    if (this.abortController) {
      this.abortController.abort();
    }
    if (this.reader) {
      this.reader.cancel();
    }
    this.isConnecting = false;
    this._setState('closed');
  }
}

class ChatAPI {
  static async solve(text, conversationId = null, options = {}) {
    const token = getToken();
    const model = options.model || 'gpt-4';
    const res = await fetch(`${API_BASE}/chat/message`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: JSON.stringify({
        conversation_id: conversationId,
        message: text,
        model: model,
        stream: false,
      }),
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'Request failed' }));
      throw new Error(err.detail || err.result || `HTTP ${res.status}`);
    }

    return res.json();
  }

  static async solveStream(text, conversationId = null, options = {}) {
    const token = getToken();
    const model = options.model || 'gpt-4';
    const body = {
      conversation_id: conversationId,
      message: text,
      model: model,
      stream: true,
      lastEventId: options.lastEventId || null,
    };

    const sse = new SSEManager(`${API_BASE}/chat/stream`, {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
      body: body,
      reconnect: options.reconnect !== false,
      maxReconnectAttempts: options.maxReconnectAttempts || 5,
      eventId: options.eventId || null,
      lastEventId: options.lastEventId || null,
    });

    return new Promise((resolve, reject) => {
      let fullContent = '';
      let isDone = false;
      let hasError = false;
      let fallbackEmitted = false;
      let metadataReceived = false;

      const finish = (err, data) => {
        if (hasError) return;
        hasError = true;
        sse.close();
        if (err) return reject(err);
        resolve({
          ...data,
          text: fullContent,
          fallback: fallbackEmitted,
        });
      };

      const retryableStatuses = [408, 429, 502, 503, 504];

      sse.on('metadata', (data) => {
        metadataReceived = true;
        if (options.onMetadata) options.onMetadata(data);
      });

      sse.on('token', (data) => {
        fullContent += data.content || '';
        if (options.onChunk) options.onChunk(data);
      });

      sse.on('done', (data) => {
        isDone = true;
        fallbackEmitted = data.fallback || fallbackEmitted;
        if (options.onDone) options.onDone(data);
        finish(null, { ...data, text: fullContent });
      });

      sse.on('fallback', (data) => {
        fallbackEmitted = true;
        if (options.onFallback) options.onFallback(data);
      });

      sse.on('error', (err) => {
        const isRetryable = err.status && retryableStatuses.includes(err.status);
        if (options.onError) options.onError(err, isRetryable);
        if (isRetryable && !isDone) {
          return;
        }
        finish(err);
      });

      sse.on('close', () => {
        if (!isDone && !hasError) {
          finish(new Error('Stream closed unexpectedly'));
        }
      });

      sse.on('reconnect_failed', () => {
        if (!isDone && !hasError) {
          finish(new Error('Reconnection failed after maximum attempts'));
        }
      });

      sse.on('state', (state) => {
        if (options.onState) options.onState(state);
      });

      sse.connect();
    });
  }

  static async createConversation(title) {
    const token = getToken();
    const res = await fetch(`${API_BASE}/chat/conversations`, {
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
    const data = await res.json();
    return data.conversation || data;
  }

  static async getConversations() {
    const token = getToken();
    const res = await fetch(`${API_BASE}/chat/conversations`, {
      headers: {
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
    });
    if (!res.ok) throw new Error('Failed to load conversations');
    const data = await res.json();
    return data.conversations || [];
  }

  static async getMessages(conversationId) {
    const token = getToken();
    const res = await fetch(`${API_BASE}/chat/conversations/${encodeURIComponent(conversationId)}/messages`, {
      headers: {
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
    });
    if (!res.ok) throw new Error('Failed to load messages');
    const data = await res.json();
    return data.messages || [];
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
    this.sseManager = null;
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
      await ChatAPI.solveStream(text, conversationId, {
        model: this.selectedModel,
        onMetadata: (data) => {
          this.sseManager = window.__lastSseManager;
        },
        onChunk: (data) => {
          if (this.currentStreamingMsgId === streamingMsgId) {
            this._updateStreamingMessage(streamingMsgId, data.content || '');
          }
        },
        onDone: () => {
          this._finalizeStreamingMessage(streamingMsgId);
        },
        onFallback: (data) => {
          showToast(`Falling back to ${data.to_provider}: ${data.reason}`, 'warning');
        },
        onError: (err, isRetryable) => {
          this._handleStreamError(streamingMsgId, err.message || 'Stream error', isRetryable);
        },
        onState: (state) => {
          this._updateConnectionStatus(state === 'open' ? 'connected' : state === 'connecting' ? 'connecting' : 'disconnected');
        },
      });
    } catch (err) {
      this._handleStreamError(streamingMsgId, err.message);
    } finally {
      this.isStreaming = false;
      this.currentStreamingMsgId = null;
      this._updateUIState();
    }
  }

  _handleStop() {
    if (this.sseManager) {
      this.sseManager.close();
      this.sseManager = null;
    }
    if (this.wsManager) {
      this.wsManager.close();
    }
    this.isStreaming = false;
    const msgId = this.currentStreamingMsgId;
    this.currentStreamingMsgId = null;
    this._finalizeStreamingMessage(msgId);
    this._updateUIState();
    showToast('Generation stopped');
  }

  _handleStreamError(msgId, errorMsg, isRetryable = false) {
    if (this.currentStreamingMsgId === msgId) {
      const msg = this.messages.find(m => m.id === msgId);
      if (msg) {
        msg.content = 'Sorry, something went wrong: ' + (errorMsg || 'Unknown error');
        msg.isStreaming = false;
        this._renderMessages();
      }
      if (isRetryable) {
        showToast('Connection issue. Retrying...', 'warning');
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
    if (!this.isStreaming) {
      this._updateConnectionStatus('connected');
    }
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
