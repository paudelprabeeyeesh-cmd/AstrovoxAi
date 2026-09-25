// Frontend Platform - Group 12: Collaboration cursors and presence indicators
const Presence = {
  _users = new Map(),
  _cursors = new Map(),
  _heartbeatInterval = null,
  _userId = null,
  _ws = null,

  init(userId) {
    this._userId = userId;

    this._heartbeatInterval = setInterval(() => {
      this._sendHeartbeat();
    }, 5000);
  },

  connect(wsUrl) {
    if (this._ws) this._ws.close();

    try {
      this._ws = new WebSocket(wsUrl);

      this._ws.onopen = () => {
        this._sendHeartbeat();
      };

      this._ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          this._handleMessage(data);
        } catch {
          // ignore malformed messages
        }
      };

      this._ws.onclose = () => {
        setTimeout(() => this.connect(wsUrl), 3000);
      };

      this._ws.onerror = () => {
        this._ws.close();
      };
    } catch {
      setTimeout(() => this.connect(wsUrl), 3000);
    }
  },

  _handleMessage(data) {
    switch (data.type) {
      case 'presence':
        this._updateUser(data.user);
        break;
      case 'cursor':
        this._updateCursor(data.userId, data.cursor);
        break;
      case 'leave':
        this._removeUser(data.userId);
        break;
    }
  },

  _sendHeartbeat() {
    if (this._ws?.readyState === WebSocket.OPEN) {
      this._ws.send(JSON.stringify({
        type: 'heartbeat',
        userId: this._userId,
        timestamp: Date.now(),
      }));
    }
  },

  _updateUser(user) {
    this._users.set(user.id, {
      ...user,
      lastSeen: Date.now(),
    });

    this._emit('user_update', user);
    this._renderCursor(user);
  },

  _updateCursor(userId, cursor) {
    if (!this._users.has(userId)) return;

    const user = this._users.get(userId);
    user.cursor = cursor;
    user.lastSeen = Date.now();

    this._renderCursor(user);
    this._emit('cursor_move', { userId, cursor });
  },

  _removeUser(userId) {
    this._users.delete(userId);
    this._removeCursor(userId);
    this._emit('user_leave', { userId });
  },

  _renderCursor(user) {
    let cursorEl = document.getElementById(`cursor-${user.id}`);

    if (!cursorEl) {
      cursorEl = document.createElement('div');
      cursorEl.id = `cursor-${user.id}`;
      cursorEl.className = 'collaboration-cursor';
      cursorEl.setAttribute('aria-hidden', 'true');
      cursorEl.innerHTML = `
        <div class="collaboration-cursor-pointer" style="background: ${user.color || '#0ea5e9'};"></div>
        <div class="collaboration-cursor-label" style="background: ${user.color || '#0ea5e9'};">${user.name || 'User'}</div>
      `;
      document.body.appendChild(cursorEl);
      this._cursors.set(user.id, cursorEl);
    }

    if (user.cursor) {
      cursorEl.style.transform = `translate(${user.cursor.x}px, ${user.cursor.y}px)`;
      cursorEl.style.display = 'block';
    }

    setTimeout(() => {
      if (Date.now() - user.lastSeen > 10000) {
        cursorEl.style.display = 'none';
      }
    }, 10000);
  },

  _removeCursor(userId) {
    const el = document.getElementById(`cursor-${userId}`);
    el?.remove();
    this._cursors.delete(userId);
  },

  broadcastCursor(x, y) {
    if (this._ws?.readyState === WebSocket.OPEN) {
      this._ws.send(JSON.stringify({
        type: 'cursor',
        userId: this._userId,
        cursor: { x, y },
      }));
    }
  },

  getUsers() {
    return Array.from(this._users.values());
  },

  getUser(userId) {
    return this._users.get(userId);
  },

  destroy() {
    if (this._heartbeatInterval) {
      clearInterval(this._heartbeatInterval);
      this._heartbeatInterval = null;
    }

    this._cursors.forEach(el => el.remove());
    this._cursors.clear();
    this._users.clear();

    if (this._ws) {
      this._ws.close();
      this._ws = null;
    }
  },

  _listeners = new Map(),

  on(event, callback) {
    if (!this._listeners.has(event)) this._listeners.set(event, []);
    this._listeners.get(event).push(callback);
    return () => {
      const cbs = this._listeners.get(event) || [];
      const idx = cbs.indexOf(callback);
      if (idx >= 0) cbs.splice(idx, 1);
    };
  },

  _emit(event, data) {
    this._listeners.get(event)?.forEach(cb => {
      try { cb(data); } catch {}
    });
  },
};

window.Presence = Presence;
