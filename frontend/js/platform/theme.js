const ThemeEngine = {
  _currentTheme: 'dark',
  _themes: {
    dark: {
      '--bg-primary': '#0f172a',
      '--bg-secondary': '#1e293b',
      '--bg-tertiary': '#334155',
      '--text-primary': '#f1f5f9',
      '--text-secondary': '#94a3b8',
      '--text-muted': '#64748b',
      '--accent': '#0ea5e9',
      '--accent-hover': '#0284c7',
      '--border': '#334155',
      '--error': '#ef4444',
      '--success': '#22c55e',
      '--warning': '#f59e0b',
    },
    light: {
      '--bg-primary': '#ffffff',
      '--bg-secondary': '#f8fafc',
      '--bg-tertiary': '#f1f5f9',
      '--text-primary': '#0f172a',
      '--text-secondary': '#475569',
      '--text-muted': '#94a3b8',
      '--accent': '#0ea5e9',
      '--accent-hover': '#0284c7',
      '--border': '#e2e8f0',
      '--error': '#ef4444',
      '--success': '#22c55e',
      '--warning': '#f59e0b',
    },
    midnight: {
      '--bg-primary': '#020617',
      '--bg-secondary': '#0f172a',
      '--bg-tertiary': '#1e293b',
      '--text-primary': '#f8fafc',
      '--text-secondary': '#cbd5e1',
      '--text-muted': '#64748b',
      '--accent': '#38bdf8',
      '--accent-hover': '#0ea5e9',
      '--border': '#1e293b',
      '--error': '#f87171',
      '--success': '#4ade80',
      '--warning': '#fbbf24',
    },
  },

  _storageKey: 'astrovox_theme',

  init() {
    const stored = this._getStoredTheme();
    if (stored) this.apply(stored);

    window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', (e) => {
      if (!localStorage.getItem(this._storageKey)) {
        this.apply(e.matches ? 'dark' : 'light');
      }
    });
  },

  getCurrent() {
    return this._currentTheme;
  },

  getAvailable() {
    return Object.keys(this._themes);
  },

  apply(themeName) {
    const theme = this._themes[themeName];
    if (!theme) return;

    this._currentTheme = themeName;
    const root = document.documentElement;

    for (const [token, value] of Object.entries(theme)) {
      root.style.setProperty(token, value);
    }

    root.setAttribute('data-theme', themeName);
    localStorage.setItem(this._storageKey, themeName);

    this._emit('change', themeName);
  },

  register(name, tokens) {
    this._themes[name] = { ...this._themes[name], ...tokens };
  },

  getToken(token) {
    const theme = this._themes[this._currentTheme];
    return theme?.[token] || getComputedStyle(document.documentElement).getPropertyValue(token).trim();
  },

  _getStoredTheme() {
    try {
      return localStorage.getItem(this._storageKey);
    } catch {
      return null;
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

window.ThemeEngine = ThemeEngine;
