const OfflineQueue = {
  _queue: [],
  _isOnline: navigator.onLine,
  _syncInProgress: false,
  _maxRetries: 3,
  _storageKey: 'astrovox_offline_queue',

  _load() {
    try {
      const raw = localStorage.getItem(this._storageKey);
      this._queue = raw ? JSON.parse(raw) : [];
    } catch {
      this._queue = [];
    }
  },

  _save() {
    try {
      localStorage.setItem(this._storageKey, JSON.stringify(this._queue));
    } catch {
      // storage full or unavailable
    }
  },

  enqueue(request) {
    const item = {
      id: crypto.randomUUID(),
      request,
      attempts: 0,
      createdAt: Date.now(),
      status: 'pending',
    };

    this._queue.push(item);
    this._save();

    if (this._isOnline) {
      this._processQueue();
    }

    return item.id;
  },

  async _processQueue() {
    if (this._syncInProgress || !this._isOnline) return;
    this._syncInProgress = true;

    const pending = this._queue.filter(item => item.status === 'pending');
    for (const item of pending) {
      try {
        item.status = 'processing';
        this._save();

        const response = await fetch(item.request.url, {
          method: item.request.method || 'POST',
          headers: item.request.headers || {},
          body: item.request.body,
        });

        if (response.ok) {
          item.status = 'completed';
          this._queue = this._queue.filter(q => q.id !== item.id);
          this._save();
        } else {
          throw new Error(`HTTP ${response.status}`);
        }
      } catch (err) {
        item.attempts++;
        item.lastError = err.message;

        if (item.attempts >= this._maxRetries) {
          item.status = 'failed';
        } else {
          item.status = 'pending';
        }
        this._save();
      }
    }

    this._syncInProgress = false;

    if (this._queue.some(item => item.status === 'pending')) {
      setTimeout(() => this._processQueue(), 5000);
    }
  },

  remove(id) {
    this._queue = this._queue.filter(item => item.id !== id);
    this._save();
  },

  getPending() {
    return this._queue.filter(item => item.status === 'pending' || item.status === 'processing');
  },

  getFailed() {
    return this._queue.filter(item => item.status === 'failed');
  },

  retryFailed() {
    this._queue.forEach(item => {
      if (item.status === 'failed') {
        item.status = 'pending';
        item.attempts = 0;
        item.lastError = null;
      }
    });
    this._save();

    if (this._isOnline) {
      this._processQueue();
    }
  },

  clear() {
    this._queue = [];
    this._save();
  },

  init() {
    this._load();

    window.addEventListener('online', () => {
      this._isOnline = true;
      this._processQueue();
    });

    window.addEventListener('offline', () => {
      this._isOnline = false;
    });

    if (this._isOnline) {
      this._processQueue();
    }
  },
};

window.OfflineQueue = OfflineQueue;
