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

  static async getFolders() {
    const token = getToken();
    const res = await fetch(`${API_BASE}/api/core/folders`, {
      headers: {
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
    });
    if (!res.ok) throw new Error('Failed to load folders');
    return res.json();
  }

  static async createFolder(name, color = '#0ea5e9') {
    const token = getToken();
    const res = await fetch(`${API_BASE}/api/core/folders`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: JSON.stringify({ name, color }),
    });
    if (!res.ok) throw new Error('Failed to create folder');
    return res.json();
  }

  static async moveConversationToFolder(conversationId, folderId) {
    const token = getToken();
    const res = await fetch(`${API_BASE}/api/core/conversations/${encodeURIComponent(conversationId)}/folder`, {
      method: 'PATCH',
      headers: {
        'Content-Type': 'application/json',
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: JSON.stringify({ folder_id: folderId }),
    });
    if (!res.ok) throw new Error('Failed to move conversation');
    return res.json();
  }

  static async pinConversation(conversationId) {
    const token = getToken();
    const res = await fetch(`${API_BASE}/api/core/conversations/${encodeURIComponent(conversationId)}/pin`, {
      method: 'POST',
      headers: {
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
    });
    if (!res.ok) throw new Error('Failed to pin conversation');
    return res.json();
  }

  static async unpinConversation(conversationId) {
    const token = getToken();
    const res = await fetch(`${API_BASE}/api/core/conversations/${encodeURIComponent(conversationId)}/pin`, {
      method: 'DELETE',
      headers: {
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
    });
    if (!res.ok) throw new Error('Failed to unpin conversation');
    return res.json();
  }

  static async shareConversation(conversationId, sharedWithUserIds = []) {
    const token = getToken();
    const res = await fetch(`${API_BASE}/api/core/conversations/share`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: JSON.stringify({ conversation_id: conversationId, shared_with_user_ids: sharedWithUserIds }),
    });
    if (!res.ok) throw new Error('Failed to share conversation');
    return res.json();
  }

  static async getSharedConversations() {
    const token = getToken();
    const res = await fetch(`${API_BASE}/api/core/conversations/shared`, {
      headers: {
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
    });
    if (!res.ok) throw new Error('Failed to load shared conversations');
    return res.json();
  }

  static async searchConversations(query, limit = 20) {
    const token = getToken();
    const res = await fetch(`${API_BASE}/api/core/conversations/search`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: JSON.stringify({ query, limit }),
    });
    if (!res.ok) throw new Error('Search failed');
    return res.json();
  }

  static async exportConversation(conversationId, fmt = 'json') {
    const token = getToken();
    const res = await fetch(`${API_BASE}/api/core/conversations/${encodeURIComponent(conversationId)}/export?fmt=${encodeURIComponent(fmt)}`, {
      headers: {
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
    });
    if (!res.ok) throw new Error('Export failed');
    return res;
  }

  static async uploadFile(file) {
    const token = getToken();
    const formData = new FormData();
    formData.append('file', file);
    const res = await fetch(`${API_BASE}/api/core/upload`, {
      method: 'POST',
      headers: {
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: formData,
    });
    if (!res.ok) throw new Error('Upload failed');
    return res.json();
  }

  static async textToSpeech(text, voice = 'alloy') {
    const token = getToken();
    const res = await fetch(`${API_BASE}/api/core/voice/tts`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: JSON.stringify({ text, voice }),
    });
    if (!res.ok) throw new Error('TTS failed');
    return res.blob();
  }

  static async speechToText(file) {
    const token = getToken();
    const formData = new FormData();
    formData.append('file', file);
    const res = await fetch(`${API_BASE}/api/core/voice/stt`, {
      method: 'POST',
      headers: {
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: formData,
    });
    if (!res.ok) throw new Error('STT failed');
    return res.json();
  }

  static async analyzeImage(imageUrl, prompt) {
    const token = getToken();
    const res = await fetch(`${API_BASE}/api/core/vision/analyze`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: JSON.stringify({ image_url: imageUrl, prompt }),
    });
    if (!res.ok) throw new Error('Image analysis failed');
    return res.json();
  }

  static async getProfile() {
    const token = getToken();
    const res = await fetch(`${API_BASE}/api/core/profile`, {
      headers: {
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
    });
    if (!res.ok) throw new Error('Failed to load profile');
    return res.json();
  }

  static async updateProfile(data) {
    const token = getToken();
    const res = await fetch(`${API_BASE}/api/core/profile`, {
      method: 'PATCH',
      headers: {
        'Content-Type': 'application/json',
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: JSON.stringify(data),
    });
    if (!res.ok) throw new Error('Failed to update profile');
    return res.json();
  }

  static async getSettings() {
    const token = getToken();
    const res = await fetch(`${API_BASE}/api/core/settings`, {
      headers: {
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
    });
    if (!res.ok) throw new Error('Failed to load settings');
    return res.json();
  }

  static async updateSettings(data) {
    const token = getToken();
    const res = await fetch(`${API_BASE}/api/core/settings`, {
      method: 'PATCH',
      headers: {
        'Content-Type': 'application/json',
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: JSON.stringify(data),
    });
    if (!res.ok) throw new Error('Failed to update settings');
    return res.json();
  }

  static async getI18nPack(lang = 'en') {
    const res = await fetch(`${API_BASE}/api/core/i18n?lang=${encodeURIComponent(lang)}`);
    if (!res.ok) throw new Error('Failed to load translations');
    return res.json();
  }

  static async getThemes() {
    const res = await fetch(`${API_BASE}/api/core/themes`);
    if (!res.ok) throw new Error('Failed to load themes');
    return res.json();
  }

  static async saveMemory(content, importance = 1) {
    const token = getToken();
    const res = await fetch(`${API_BASE}/api/core/memory/hooks`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: JSON.stringify({ content, importance }),
    });
    if (!res.ok) throw new Error('Failed to save memory');
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
    this.folders = [];
    this.activeConversationId = null;
    this.activeFolderId = null;
    this.isLoading = false;
    this.isStreaming = false;
    this.currentStreamingMsgId = null;
    this.wsManager = null;
    this.abortController = null;
    this.selectedModel = 'gpt-4o';
    this.mediaRecorder = null;
    this.audioChunks = [];
    this.isRecording = false;
    this.i18n = {};
    this.currentLang = 'en';

    this.messageListEl = document.getElementById('chat-messages');
    this.messageInputEl = document.getElementById('message-input');
    this.sendBtnEl = document.getElementById('send-btn');
    this.stopBtnEl = document.getElementById('stop-btn');
    this.conversationListEl = document.getElementById('conversation-list');
    this.newChatBtnEl = document.getElementById('new-chat-btn');
    this.connectionStatusEl = document.getElementById('connection-status');
    this.modelSelectEl = document.getElementById('model-select');
    this.searchInputEl = document.getElementById('conversation-search');
    this.folderSelectEl = document.getElementById('folder-select');
    this.pinBtnEl = document.getElementById('pin-conversation-btn');
    this.shareBtnEl = document.getElementById('share-conversation-btn');
    this.exportBtnEl = document.getElementById('export-conversation-btn');
    this.uploadBtnEl = document.getElementById('upload-file-btn');
    this.voiceBtnEl = document.getElementById('voice-input-btn');
    this.ttsBtnEl = document.getElementById('tts-btn');
    this.themeBtnEl = document.getElementById('theme-btn');
    this.langBtnEl = document.getElementById('lang-btn');

    this._bindEvents();
    this._init();
  }

  t(key, fallback) {
    const pack = this.i18n.translations || {};
    return pack[key] || fallback || key;
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
    if (this.searchInputEl) {
      this.searchInputEl.addEventListener('input', (e) => {
        this._handleSearch(e.target.value);
      });
    }
    if (this.folderSelectEl) {
      this.folderSelectEl.addEventListener('change', (e) => {
        this._handleFolderChange(e.target.value);
      });
    }
    if (this.pinBtnEl) {
      this.pinBtnEl.addEventListener('click', () => this._togglePin());
    }
    if (this.shareBtnEl) {
      this.shareBtnEl.addEventListener('click', () => this._handleShare());
    }
    if (this.exportBtnEl) {
      this.exportBtnEl.addEventListener('click', () => this._handleExport());
    }
    if (this.uploadBtnEl) {
      this.uploadBtnEl.addEventListener('click', () => this._handleUpload());
    }
    if (this.voiceBtnEl) {
      this.voiceBtnEl.addEventListener('click', () => this._toggleVoiceRecording());
    }
    if (this.ttsBtnEl) {
      this.ttsBtnEl.addEventListener('click', () => this._handleTTS());
    }
    if (this.themeBtnEl) {
      this.themeBtnEl.addEventListener('click', () => this._cycleTheme());
    }
    if (this.langBtnEl) {
      this.langBtnEl.addEventListener('click', () => this._cycleLanguage());
    }

    this._initRealityBending();
  }

  _initRealityBending() {
    if (typeof AstrovoxReality === 'undefined') return;
    try {
      AstrovoxReality.enableGravityPanels('.chat-layout, .chat-sidebar, .chat-main');
      const chatMain = document.querySelector('.chat-main');
      if (chatMain) AstrovoxReality.addRiftToElement(chatMain);
      const sidebar = document.querySelector('.chat-sidebar');
      if (sidebar) AstrovoxReality.applyPhysicsToElement(sidebar, 0.03);
    } catch {}
  }

  async _init() {
    this._setLoading(true);
    try {
      await this._loadI18n();
      await this._loadSettings();
      await this._loadFolders();
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

  async _loadI18n() {
    try {
      const lang = localStorage.getItem('astrovox_lang') || 'en';
      this.currentLang = lang;
      const data = await ChatAPI.getI18nPack(lang);
      this.i18n = data;
      if (this.messageInputEl) {
        this.messageInputEl.placeholder = this.t('search_placeholder', 'Send a message...');
      }
    } catch {}
  }

  async _loadSettings() {
    try {
      const data = await ChatAPI.getSettings();
      const settings = data.settings || {};
      if (settings.theme && typeof ThemeEngine !== 'undefined') {
        ThemeEngine.apply(settings.theme);
      }
      if (settings.language) {
        this.currentLang = settings.language;
        localStorage.setItem('astrovox_lang', settings.language);
        await this._loadI18n();
      }
    } catch {}
  }

  async _loadFolders() {
    try {
      const data = await ChatAPI.getFolders();
      this.folders = data.folders || [];
      this._renderFolderOptions();
    } catch (err) {
      console.error('Failed to load folders:', err);
    }
  }

  _renderFolderOptions() {
    if (!this.folderSelectEl) return;
    this.folderSelectEl.innerHTML = `
      <option value="">${this.t('folders', 'Folders')}</option>
      ${this.folders.map(f => `<option value="${f.id}">${this._escapeHtml(f.name)}</option>`).join('')}
    `;
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
        parts: m.parts,
      }));
      this._renderMessages();
    } catch (err) {
      showError('Failed to load messages: ' + err.message);
    }
  }

  async _newConversation() {
    try {
      const title = this.t('new_chat', 'New Chat');
      const conv = await ChatAPI.createConversation(title);
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
    this._stopRecording();
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
          <h3>${this.t('new_chat', 'Start a conversation')}</h3>
          <p>Send a message to begin chatting with the AI assistant.</p>
        </div>
      `;
      return;
    }

    inner.innerHTML = this.messages.map(msg => {
      const isUser = msg.role === 'user';
      const avatar = isUser ? 'U' : 'AI';
      const streamingClass = msg.isStreaming ? 'message-streaming' : '';
      let renderedContent = this._escapeHtml(msg.content);
      if (!isUser && typeof Markdown !== 'undefined') {
        renderedContent = Markdown.render(msg.content);
      }
      if (!isUser && typeof Monaco !== 'undefined') {
        renderedContent = renderedContent.replace(/<pre><code class="language-(\w+)">([\s\S]*?)<\/code><\/pre>/g, (match, lang, code) => {
          const id = 'code-' + Math.random().toString(36).slice(2);
          return `<div class="code-block" data-lang="${lang}" data-id="${id}"><pre><code>${code}</code></pre></div>`;
        });
      }
      return `
        <div class="message ${msg.role} ${streamingClass}">
          <div class="message-avatar">${avatar}</div>
          <div class="message-content">
            <div class="message-bubble">${renderedContent}</div>
            <div class="message-actions">
              <button class="message-action-btn copy-btn" title="Copy">📋</button>
              ${!isUser ? `<button class="message-action-btn tts-action-btn" title="Read aloud">🔊</button>` : ''}
            </div>
            <div class="message-time">${formatTime(msg.createdAt)}</div>
          </div>
        </div>
      `;
    }).join('');

    inner.querySelectorAll('.copy-btn').forEach(btn => {
      btn.addEventListener('click', (e) => {
        const bubble = e.target.closest('.message-content')?.querySelector('.message-bubble');
        const text = bubble?.textContent || '';
        navigator.clipboard.writeText(text).then(() => showToast('Copied to clipboard'));
      });
    });

    inner.querySelectorAll('.tts-action-btn').forEach(btn => {
      btn.addEventListener('click', async (e) => {
        const bubble = e.target.closest('.message-content')?.querySelector('.message-bubble');
        const text = bubble?.textContent || '';
        if (!text) return;
        try {
          const blob = await ChatAPI.textToSpeech(text);
          const url = URL.createObjectURL(blob);
          const audio = new Audio(url);
          audio.play();
        } catch (err) {
          showError('TTS failed: ' + err.message);
        }
      });
    });

    inner.lastElementChild?.scrollIntoView({ behavior: 'smooth' });
  }

  _renderConversationList() {
    if (!this.conversationListEl) return;
    const pinned = this.conversations.filter(c => c.is_pinned);
    const unpinned = this.conversations.filter(c => !c.is_pinned);
    const sorted = [...pinned, ...unpinned];

    this.conversationListEl.innerHTML = sorted.map(conv => `
      <button class="conversation-item ${conv.id === this.activeConversationId ? 'active' : ''} ${conv.is_pinned ? 'pinned' : ''}"
              data-id="${conv.id}" data-folder="${conv.folder_id || ''}">
        <span class="conv-title">${this._escapeHtml(conv.title || 'Untitled Chat')}</span>
        <span class="conv-actions">
          ${conv.is_pinned ? '<span class="pin-icon">📌</span>' : ''}
        </span>
      </button>
    `).join('');

    this.conversationListEl.querySelectorAll('.conversation-item').forEach(btn => {
      btn.addEventListener('click', () => {
        const id = btn.dataset.id;
        if (id) {
          if (typeof AstrovoxReality !== 'undefined') {
            AstrovoxReality.wormholeNavigateToConversation(id);
          }
          this._loadConversation(id);
        }
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

  async _handleSearch(query) {
    if (!query || query.length < 2) {
      await this._loadConversations();
      return;
    }
    try {
      const data = await ChatAPI.searchConversations(query);
      const results = data.results || [];
      if (results.length === 0) {
        this.conversations = [];
      } else {
        this.conversations = results.map(r => ({
          id: r.id,
          title: r.title || r.snippet ? (r.title || 'Match') : 'Untitled',
          is_pinned: false,
        }));
      }
      this._renderConversationList();
    } catch (err) {
      console.error('Search failed:', err);
    }
  }

  async _handleFolderChange(folderId) {
    if (!this.activeConversationId) return;
    try {
      await ChatAPI.moveConversationToFolder(this.activeConversationId, folderId || null);
      showToast('Conversation moved');
      await this._loadConversations();
    } catch (err) {
      showError('Failed to move conversation: ' + err.message);
    }
  }

  async _togglePin() {
    if (!this.activeConversationId) return;
    const conv = this.conversations.find(c => c.id === this.activeConversationId);
    if (!conv) return;
    try {
      if (conv.is_pinned) {
        await ChatAPI.unpinConversation(this.activeConversationId);
        showToast('Unpinned');
      } else {
        await ChatAPI.pinConversation(this.activeConversationId);
        showToast('Pinned');
      }
      await this._loadConversations();
    } catch (err) {
      showError('Failed to update pin: ' + err.message);
    }
  }

  async _handleShare() {
    if (!this.activeConversationId) return;
    const email = prompt('Enter email to share with:');
    if (!email) return;
    try {
      await ChatAPI.shareConversation(this.activeConversationId, [email]);
      showToast('Conversation shared');
    } catch (err) {
      showError('Failed to share: ' + err.message);
    }
  }

  async _handleExport() {
    if (!this.activeConversationId) return;
    const fmt = confirm('Export as Markdown? Cancel for JSON.') ? 'markdown' : 'json';
    try {
      const res = await ChatAPI.exportConversation(this.activeConversationId, fmt);
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `conversation_${this.activeConversationId}.${fmt === 'markdown' ? 'md' : 'json'}`;
      a.click();
      URL.revokeObjectURL(url);
      showToast('Exported successfully');
    } catch (err) {
      showError('Export failed: ' + err.message);
    }
  }

  async _handleUpload() {
    const input = document.createElement('input');
    input.type = 'file';
    input.accept = 'image/*,.pdf,.txt,.md';
    input.onchange = async (e) => {
      const file = e.target.files[0];
      if (!file) return;
      try {
        const data = await ChatAPI.uploadFile(file);
        const url = data.file?.url || '';
        if (url) {
          this.messageInputEl.value += `\n[Uploaded: ${data.file.filename}](${url})\n`;
        }
        showToast('File uploaded');
      } catch (err) {
        showError('Upload failed: ' + err.message);
      }
    };
    input.click();
  }

  async _toggleVoiceRecording() {
    if (this.isRecording) {
      this._stopRecording();
      return;
    }
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      this.audioChunks = [];
      this.mediaRecorder = new MediaRecorder(stream);
      this.mediaRecorder.ondataavailable = (e) => {
        if (e.data.size > 0) this.audioChunks.push(e.data);
      };
      this.mediaRecorder.onstop = async () => {
        const blob = new Blob(this.audioChunks, { type: 'audio/webm' });
        stream.getTracks().forEach(track => track.stop());
        try {
          const data = await ChatAPI.speechToText(blob);
          if (data.text) {
            this.messageInputEl.value += (this.messageInputEl.value ? ' ' : '') + data.text;
          }
        } catch (err) {
          showError('Transcription failed: ' + err.message);
        }
      };
      this.mediaRecorder.start();
      this.isRecording = true;
      if (this.voiceBtnEl) this.voiceBtnEl.classList.add('recording');
      showToast('Recording...');
    } catch (err) {
      showError('Microphone access denied');
    }
  }

  _stopRecording() {
    if (this.mediaRecorder && this.mediaRecorder.state !== 'inactive') {
      this.mediaRecorder.stop();
    }
    this.isRecording = false;
    if (this.voiceBtnEl) this.voiceBtnEl.classList.remove('recording');
  }

  async _handleTTS() {
    if (!this.activeConversationId) return;
    const msgs = this.messages.filter(m => m.role === 'assistant');
    if (msgs.length === 0) return;
    const last = msgs[msgs.length - 1];
    try {
      const blob = await ChatAPI.textToSpeech(last.content);
      const url = URL.createObjectURL(blob);
      const audio = new Audio(url);
      audio.play();
    } catch (err) {
      showError('TTS failed: ' + err.message);
    }
  }

  _cycleTheme() {
    if (typeof ThemeEngine === 'undefined') return;
    const themes = ThemeEngine.getAvailable();
    const current = ThemeEngine.getCurrent();
    const idx = themes.indexOf(current);
    const next = themes[(idx + 1) % themes.length];
    ThemeEngine.apply(next);
    ChatAPI.updateSettings({ theme: next }).catch(() => {});
  }

  async _cycleLanguage() {
    const langs = ['en', 'es', 'fr', 'de', 'ja', 'zh'];
    const idx = langs.indexOf(this.currentLang);
    const next = langs[(idx + 1) % langs.length];
    this.currentLang = next;
    localStorage.setItem('astrovox_lang', next);
    await this._loadI18n();
    this._renderConversationList();
    this._renderMessages();
    ChatAPI.updateSettings({ language: next }).catch(() => {});
  }
}

window.ChatApp = ChatApp;
