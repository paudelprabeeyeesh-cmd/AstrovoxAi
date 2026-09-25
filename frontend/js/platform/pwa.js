// Frontend Platform - Group 5: PWA install, update, and cache strategies
const PWA = {
  _deferredPrompt: null,
  _isInstallable: false,
  _updateAvailable: false,
  _newWorker: null,

  init() {
    window.addEventListener('beforeinstallprompt', (e) => {
      e.preventDefault();
      this._deferredPrompt = e;
      this._isInstallable = true;
      this._emit('installable');
    });

    window.addEventListener('appinstalled', () => {
      this._isInstallable = false;
      this._deferredPrompt = null;
      this._emit('installed');
    });

    if ('serviceWorker' in navigator) {
      navigator.serviceWorker.addEventListener('controllerchange', () => {
        this._updateAvailable = true;
        this._emit('update');
      });
    }
  },

  async promptInstall() {
    if (!this._deferredPrompt) return false;

    this._deferredPrompt.prompt();
    const result = await this._deferredPrompt.userChoice;
    this._deferredPrompt = null;
    this._isInstallable = false;

    return result.outcome === 'accepted';
  },

  isInstallable() {
    return this._isInstallable;
  },

  isUpdateAvailable() {
    return this._updateAvailable;
  },

  async reload() {
    if (!('serviceWorker' in navigator)) return;
    const reg = await navigator.serviceWorker.getRegistration();
    if (reg && reg.waiting) {
      reg.waiting.postMessage({ type: 'SKIP_WAITING' });
      window.location.reload();
    }
  },

  on(event, callback) {
    if (!this._listeners) this._listeners = new Map();
    if (!this._listeners.has(event)) this._listeners.set(event, []);
    this._listeners.get(event).push(callback);
    return () => {
      const cbs = this._listeners.get(event) || [];
      const idx = cbs.indexOf(callback);
      if (idx >= 0) cbs.splice(idx, 1);
    };
  },

  _emit(event, data) {
    const cbs = this._listeners?.get(event) || [];
    cbs.forEach(cb => {
      try { cb(data); } catch {}
    });
  },
};

window.PWA = PWA;
