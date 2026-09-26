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

function getUser() {
  try {
    const raw = localStorage.getItem('astrovox_user');
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}

function setUser(user) {
  localStorage.setItem('astrovox_user', JSON.stringify(user));
}

function clearUser() {
  localStorage.removeItem('astrovox_user');
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

function apiFetch(endpoint, options = {}) {
  let token = getToken();
  const headers = {
    'Content-Type': 'application/json',
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...options.headers,
  };

  return fetch(`${API_BASE}${endpoint}`, {
    ...options,
    headers,
  }).then(async (res) => {
    if (res.status === 401) {
      try {
        const refresh = await fetch(`${API_BASE}/auth/refresh`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ refresh_token: localStorage.getItem('astrovox_refresh_token') }),
        });
        if (refresh.ok) {
          const data = await refresh.json();
          localStorage.setItem('astrovox_access_token', data.access_token);
          headers.Authorization = `Bearer ${data.access_token}`;
          return fetch(`${API_BASE}${endpoint}`, { ...options, headers }).then(r => handleResponse(r));
        }
      } catch {
        // fall through
      }
      redirectToLogin();
      return Promise.reject(new Error('Unauthorized'));
    }
    return handleResponse(res);
  });
}

function handleResponse(res) {
  if (!res.ok) {
    return res.json().then(err => Promise.reject(new Error(err.detail || err.message || `HTTP ${res.status}`)));
  }
  if (res.status === 204) return Promise.resolve({});
  return res.json();
}

function redirectToLogin() {
  clearUser();
  localStorage.removeItem('astrovox_access_token');
  localStorage.removeItem('astrovox_refresh_token');
  window.location.href = '/login.html';
}

class App {
  constructor() {
    this.currentPage = 'login';
    this.chatApp = null;
    this.dashboardApp = null;
    this.authState = {
      user: getUser(),
      isAuthenticated: !!getToken(),
    };

    this._checkAuthAndRoute();
  }

  _checkAuthAndRoute() {
    const hash = window.location.hash.replace('#', '') || '/login';
    const path = window.location.pathname;

    if (path === '/login.html' || path === '/register.html' || path === '/forgot-password.html') {
      if (this.authState.isAuthenticated) {
        window.location.href = '/dashboard.html';
        return;
      }
      this._showAuthPage(path);
    } else if (path === '/dashboard.html') {
      if (!this.authState.isAuthenticated) {
        window.location.href = '/login.html';
        return;
      }
      this._showDashboard();
    } else if (path === '/chat.html') {
      if (!this.authState.isAuthenticated) {
        window.location.href = '/login.html';
        return;
      }
      this._showChat();
    } else if (path === '/image-ai.html') {
      if (!this.authState.isAuthenticated) {
        window.location.href = '/login.html';
        return;
      }
      this._showImageAI();
    } else if (path === '/search.html') {
      if (!this.authState.isAuthenticated) {
        window.location.href = '/login.html';
        return;
      }
      this._showSearch();
    } else if (path === '/agents.html') {
      if (!this.authState.isAuthenticated) {
        window.location.href = '/login.html';
        return;
      }
      this._showAgents();
    } else if (path === '/tools.html') {
      if (!this.authState.isAuthenticated) {
        window.location.href = '/login.html';
        return;
      }
      this._showTools();
    } else if (path === '/coding.html') {
      if (!this.authState.isAuthenticated) {
        window.location.href = '/login.html';
        return;
      }
      this._showCoding();
    } else if (path === '/inference.html') {
      if (!this.authState.isAuthenticated) {
        window.location.href = '/login.html';
        return;
      }
      this._showInference();
    } else if (path === '/audio.html') {
      if (!this.authState.isAuthenticated) {
        window.location.href = '/login.html';
        return;
      }
      this._showAudio();
    } else if (path === '/security.html') {
      if (!this.authState.isAuthenticated) {
        window.location.href = '/login.html';
        return;
      }
      this._showSecurity();
    } else if (path === '/apps.html') {
      if (!this.authState.isAuthenticated) {
        window.location.href = '/login.html';
        return;
      }
      this._showApps();
    } else if (path === '/multi-agent.html') {
      if (!this.authState.isAuthenticated) {
        window.location.href = '/login.html';
        return;
      }
      this._showMultiAgent();
    } else if (path === '/developer-platform.html') {
      if (!this.authState.isAuthenticated) {
        window.location.href = '/login.html';
        return;
      }
      this._showDeveloperPlatform();
    } else if (path === '/extensions.html') {
      if (!this.authState.isAuthenticated) {
        window.location.href = '/login.html';
        return;
      }
      this._showExtensions();
    } else if (path === '/integrations.html') {
      if (!this.authState.isAuthenticated) {
        window.location.href = '/login.html';
        return;
      }
      this._showIntegrations();
    } else if (path === '/sdks.html') {
      if (!this.authState.isAuthenticated) {
        window.location.href = '/login.html';
        return;
      }
      this._showSdks();
    } else if (path === '/memory.html') {
      if (!this.authState.isAuthenticated) {
        window.location.href = '/login.html';
        return;
      }
      this._showMemory();
    } else {
      if (this.authState.isAuthenticated) {
        window.location.href = '/dashboard.html';
      } else {
        window.location.href = '/login.html';
      }
    }
  }

  _showAuthPage(path) {
    const app = document.getElementById('app');
    if (!app) return;

    const isRegister = path === '/register.html';
    const isForgot = path === '/forgot-password.html';

    app.innerHTML = `
      <div class="auth-page rbp-rift">
        <div class="auth-card rbp-gravity-panel" data-gravity="normal">
          <h1>${isForgot ? 'Reset Password' : isRegister ? 'Create an account' : 'Welcome back'}</h1>
          <p class="subtitle">${isForgot ? 'Enter your email to reset your password' : isRegister ? 'Enter your details to get started' : 'Enter your credentials to access your account'}</p>
          <form id="auth-form">
            ${isRegister ? `
              <div class="form-group">
                <label for="name">Full Name</label>
                <input type="text" id="name" placeholder="John Doe" ${isRegister ? 'required' : ''} />
              </div>
            ` : ''}
            <div class="form-group">
              <label for="email">Email</label>
              <input type="email" id="email" placeholder="name@example.com" required />
              <div id="email-error" class="form-error"></div>
            </div>
            <div class="form-group">
              <label for="password">Password</label>
              <input type="password" id="password" placeholder="${isRegister ? 'Min. 8 characters' : 'Enter your password'}" required minlength="8" />
              <div id="password-error" class="form-error"></div>
            </div>
            ${isRegister ? `
              <div class="form-group">
                <label for="confirmPassword">Confirm Password</label>
                <input type="password" id="confirmPassword" placeholder="Re-enter your password" required minlength="8" />
                <div id="confirm-error" class="form-error"></div>
              </div>
            ` : ''}
            <div id="auth-error" class="form-error" style="margin-bottom: 1rem;"></div>
            <button type="submit" class="btn btn-primary" style="width: 100%;" id="auth-submit-btn">
              <span id="auth-btn-text">${isForgot ? 'Send Reset Link' : isRegister ? 'Create Account' : 'Sign In'}</span>
            </button>
          </form>
          <div class="form-footer">
            ${isForgot ? `
              Remember your password? <a href="/login.html">Sign in</a>
            ` : isRegister ? `
              Already have an account? <a href="/login.html">Sign in</a>
            ` : `
              Don't have an account? <a href="/register.html">Sign up</a><br/>
              <a href="/forgot-password.html" style="font-size: 0.75rem;">Forgot password?</a>
            `}
          </div>
        </div>
      </div>
    `;

    const form = document.getElementById('auth-form');
    if (form) {
      form.addEventListener('submit', (e) => {
        e.preventDefault();
        this._handleAuthSubmit(path);
      });
    }

    this._initRealityAuth();
  }

  _initRealityAuth() {
    if (typeof AstrovoxReality === 'undefined') return;
    try {
      const card = document.querySelector('.auth-card');
      if (card) AstrovoxReality.applyPhysicsToElement(card, 0.02);
    } catch {}
  }

  async _handleAuthSubmit(path) {
    const email = document.getElementById('email')?.value?.trim();
    const password = document.getElementById('password')?.value;
    const name = document.getElementById('name')?.value?.trim();
    const confirmPassword = document.getElementById('confirmPassword')?.value;
    const errorEl = document.getElementById('auth-error');
    const submitBtn = document.getElementById('auth-submit-btn');
    const btnText = document.getElementById('auth-btn-text');

    if (!email || !password) {
      if (errorEl) errorEl.textContent = 'Please fill in all required fields';
      return;
    }

    const isRegister = path === '/register.html';
    const isForgot = path === '/forgot-password.html';

    if (isRegister && password !== confirmPassword) {
      if (errorEl) errorEl.textContent = 'Passwords do not match';
      return;
    }

    if (submitBtn) submitBtn.disabled = true;
    if (btnText) btnText.textContent = 'Please wait...';
    if (errorEl) errorEl.textContent = '';

    try {
      if (isForgot) {
        const res = await fetch(`${API_BASE}/auth/forgot-password`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ email }),
        });
        if (!res.ok) {
          const err = await res.json().catch(() => ({ detail: 'Failed' }));
          throw new Error(err.detail || 'Failed to send reset link');
        }
        showToast('Password reset link sent to your email', 'success');
        setTimeout(() => { window.location.href = '/login.html'; }, 2000);
        return;
      }

      if (isRegister) {
        const res = await fetch(`${API_BASE}/auth/register`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ email, password, name }),
        });
        if (!res.ok) {
          const err = await res.json().catch(() => ({ detail: 'Registration failed' }));
          throw new Error(err.detail || err.message || 'Registration failed');
        }
        const data = await res.json();
        showToast('Account created! Please check your email to verify.', 'success');
        setTimeout(() => { window.location.href = '/login.html'; }, 2000);
        return;
      }

      const res = await fetch(`${API_BASE}/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password }),
      });

      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: 'Login failed' }));
        throw new Error(err.detail || err.message || 'Invalid email or password');
      }

      const data = await res.json();
      localStorage.setItem('astrovox_access_token', data.access_token);
      if (data.refresh_token) localStorage.setItem('astrovox_refresh_token', data.refresh_token);
      setUser({ id: data.user_id, email: data.email });
      this.authState = { user: { id: data.user_id, email: data.email }, isAuthenticated: true };
      showToast('Welcome back!', 'success');
      window.location.href = '/dashboard.html';
    } catch (err) {
      if (errorEl) errorEl.textContent = err.message;
      showError(err.message);
    } finally {
      if (submitBtn) submitBtn.disabled = false;
      if (btnText) btnText.textContent = isForgot ? 'Send Reset Link' : isRegister ? 'Create Account' : 'Sign In';
    }
  }

  _showChat() {
    const app = document.getElementById('app');
    if (!app) return;

    const user = getUser();
    app.innerHTML = `
      <div class="navbar">
        <a href="/dashboard.html" class="navbar-brand">
          <div class="logo">A</div>
          <span>AstrovoxAI</span>
        </a>
        <nav class="navbar-nav">
          <a href="/chat.html" class="nav-link active">Chat</a>
          <a href="/dashboard.html" class="nav-link" data-reality-teleport>Dashboard</a>
          <a href="/agents.html" class="nav-link">Agents</a>
          <a href="/tools.html" class="nav-link">Tools</a>
          <a href="/coding.html" class="nav-link">Coding</a>
          <a href="/search.html" class="nav-link">Search</a>
          <a href="/rag.html" class="nav-link">RAG</a>
          <a href="/image-ai.html" class="nav-link">Image AI</a>
          <a href="/video.html" class="nav-link">Video</a>
          <a href="/audio.html" class="nav-link">Audio</a>
          <div class="nav-user">
            <span style="font-size: 0.875rem; color: var(--text-secondary);">${user?.email || 'User'}</span>
            <button class="btn btn-sm btn-secondary" id="logout-btn">Logout</button>
          </div>
        </nav>
      </div>
      <div class="chat-layout rbp-gravity-panel" data-gravity="normal">
        <aside class="chat-sidebar">
          <div class="chat-sidebar-header" style="display: flex; align-items: center; justify-content: space-between;">
            <h2>Conversations</h2>
            <button class="btn btn-sm btn-primary" id="new-chat-btn">+ New</button>
          </div>
          <div class="chat-sidebar-tools" style="padding: 0.5rem; border-bottom: 1px solid var(--border);">
            <input type="text" id="conversation-search" placeholder="Search conversations..." class="search-input" />
            <select id="folder-select" class="folder-select">
              <option value="">All Folders</option>
            </select>
          </div>
          <div class="conversation-list" id="conversation-list">
            <div class="loading-container">
              <div class="spinner"></div>
              <span>Loading...</span>
            </div>
          </div>
        </aside>
        <main class="chat-main rbp-rift">
          <div class="chat-toolbar" style="display: flex; align-items: center; justify-content: space-between; padding: 0.5rem 1rem; border-bottom: 1px solid var(--border); background: var(--bg-secondary);">
            <div class="chat-toolbar-left" style="display: flex; align-items: center; gap: 0.5rem;">
              <span id="active-conversation-title" style="font-weight: 600; font-size: 0.875rem;">Select a conversation</span>
            </div>
            <div class="chat-toolbar-actions" style="display: flex; gap: 0.5rem;">
              <button class="btn btn-sm btn-secondary" id="pin-conversation-btn" title="Pin">📌</button>
              <button class="btn btn-sm btn-secondary" id="share-conversation-btn" title="Share">🔗</button>
              <button class="btn btn-sm btn-secondary" id="export-conversation-btn" title="Export">📥</button>
              <button class="btn btn-sm btn-secondary" id="upload-file-btn" title="Upload">📎</button>
              <button class="btn btn-sm btn-secondary" id="voice-input-btn" title="Voice">🎤</button>
              <button class="btn btn-sm btn-secondary" id="tts-btn" title="Read aloud">🔊</button>
              <button class="btn btn-sm btn-secondary" id="theme-btn" title="Theme">🎨</button>
              <button class="btn btn-sm btn-secondary" id="lang-btn" title="Language">🌐</button>
            </div>
          </div>
          <div class="chat-messages" id="chat-messages">
            <div class="chat-messages-inner">
              <div class="empty-state">
                <div class="empty-state-icon">💬</div>
                <h3>Start a conversation</h3>
                <p>Send a message to begin chatting with the AI assistant.</p>
              </div>
            </div>
          </div>
          <div class="chat-input-area">
            <div class="chat-input-wrapper">
              <textarea id="message-input" placeholder="Send a message..." rows="1"></textarea>
              <div class="chat-input-actions">
                <select id="model-select" class="model-selector">
                  <option value="gpt-4o">GPT-4o</option>
                  <option value="claude-3.5-sonnet">Claude 3.5</option>
                  <option value="gemini-2.0-flash">Gemini 2.0</option>
                </select>
                <button class="btn btn-primary" id="send-btn">Send</button>
                <button class="btn btn-danger" id="stop-btn" style="display: none;">Stop</button>
              </div>
            </div>
          </div>
        </main>
      </div>
    `;

    document.getElementById('logout-btn')?.addEventListener('click', () => this._handleLogout());
    this._initRealityNav();
    this.chatApp = new ChatApp();
  }

  _showImageAI() {
    const app = document.getElementById('app');
    if (!app) return;
    const imgApp = new ImageAIApp();
  }

  _showAgents() {
    const app = document.getElementById('app');
    if (!app) return;
    window.location.href = '/agents.html';
  }

  _showTools() {
    const app = document.getElementById('app');
    if (!app) return;
    window.location.href = '/tools.html';
  }

  _showCoding() {
    const app = document.getElementById('app');
    if (!app) return;
    window.location.href = '/coding.html';
  }

  _showInference() {
    const app = document.getElementById('app');
    if (!app) return;
    window.location.href = '/inference.html';
  }

  _showAudio() {
    const app = document.getElementById('app');
    if (!app) return;
    window.location.href = '/audio.html';
  }

  _showSecurity() {
    const app = document.getElementById('app');
    if (!app) return;
    window.location.href = '/security.html';
  }

  _showApps() {
    const app = document.getElementById('app');
    if (!app) return;
    window.location.href = '/apps.html';
  }

  _showMultiAgent() {
    const app = document.getElementById('app');
    if (!app) return;
    window.location.href = '/multi-agent.html';
  }

  _showDeveloperPlatform() {
    const app = document.getElementById('app');
    if (!app) return;
    window.location.href = '/developer-platform.html';
  }

  _showExtensions() {
    const app = document.getElementById('app');
    if (!app) return;
    window.location.href = '/extensions.html';
  }

  _showIntegrations() {
    const app = document.getElementById('app');
    if (!app) return;
    window.location.href = '/integrations.html';
  }

  _showSdks() {
    const app = document.getElementById('app');
    if (!app) return;
    window.location.href = '/sdks.html';
  }

  _showMemory() {
    const app = document.getElementById('app');
    if (!app) return;
    window.location.href = '/memory.html';
  }

  _initRealityNav() {
    if (typeof AstrovoxReality === 'undefined') return;
    try {
      document.querySelectorAll('[data-reality-teleport]').forEach(el => {
        el.addEventListener('click', (e) => {
          e.preventDefault();
          const href = el.getAttribute('href');
          if (href === '/dashboard.html') AstrovoxReality.teleportToWorkspace('dashboard');
        });
      });
    } catch {}
  }

  _showDashboard() {
    const app = document.getElementById('app');
    if (!app) return;

    const user = getUser();
    app.innerHTML = `
      <div class="navbar">
        <a href="/dashboard.html" class="navbar-brand">
          <div class="logo">A</div>
          <span>AstrovoxAI</span>
        </a>
        <nav class="navbar-nav">
          <a href="/chat.html" class="nav-link" data-reality-teleport>Chat</a>
          <a href="/dashboard.html" class="nav-link active">Dashboard</a>
          <div class="nav-user">
            <span style="font-size: 0.875rem; color: var(--text-secondary);">${user?.email || 'User'}</span>
            <button class="btn btn-sm btn-secondary" id="logout-btn">Logout</button>
          </div>
        </nav>
      </div>
      <div class="page-content">
        <div class="container">
          <div id="dashboard-header" style="margin-bottom: 1.5rem; display: flex; align-items: center; justify-content: space-between;">
            <div>
              <h1 style="font-size: 1.875rem; font-weight: 700;">Dashboard</h1>
              <p style="color: var(--text-muted); font-size: 0.875rem;">Welcome back! Here is your overview.</p>
            </div>
            <div id="rbp-dashboard-badges"></div>
          </div>
          <div id="dashboard-loading" class="loading-container" style="display: none;">
            <div class="spinner"></div>
            <span>Loading dashboard...</span>
          </div>
          <div id="dashboard-error" style="display: none; color: var(--error); margin-bottom: 1rem;"></div>
          <div class="stats-grid rbp-gravity-panel" data-gravity="normal" id="stats-grid"></div>
          <div class="dashboard-grid rbp-rift">
            <div id="usage-chart"></div>
            <div class="dashboard-card" id="activity-list">
              <h3>Recent Activity</h3>
              <p class="desc">Latest events across your workspace</p>
              <div id="activity-items"></div>
            </div>
          </div>
          <div id="cost-tracker" style="margin-top: 1.5rem;"></div>
        </div>
      </div>
    `;

    document.getElementById('logout-btn')?.addEventListener('click', () => this._handleLogout());
    this._initRealityNav();
    this.dashboardApp = new DashboardApp();
  }

  _showSearch() {
    const app = document.getElementById('app');
    if (!app) return;

    const user = getUser();
    app.innerHTML = `
      <div class="search-page">
        <div class="search-navbar">
          <a href="/dashboard.html" class="navbar-brand">
            <div class="logo">A</div>
            <span>AstrovoxAI</span>
          </a>
          <nav class="navbar-nav">
            <a href="/chat.html" class="nav-link">Chat</a>
            <a href="/dashboard.html" class="nav-link">Dashboard</a>
            <a href="/search.html" class="nav-link active">Search</a>
            <div class="nav-user">
              <span style="font-size: 0.875rem; color: var(--text-secondary);">${user?.email || 'User'}</span>
              <button class="btn btn-sm btn-secondary" id="logout-btn">Logout</button>
            </div>
          </nav>
        </div>
        <div class="search-layout">
          <aside class="search-sidebar">
            <h3>Sources</h3>
            <label><input type="checkbox" id="src-internal" checked> Internal Documents</label>
            <label><input type="checkbox" id="src-web" checked> Web</label>
            <label><input type="checkbox" id="src-images"> Images</label>
            <label><input type="checkbox" id="src-videos"> Videos</label>
            <label><input type="checkbox" id="src-news"> News</label>
            <label><input type="checkbox" id="src-academic"> Academic</label>
            <h3 style="margin-top: 1rem;">Options</h3>
            <label><input type="checkbox" id="opt-rerank" checked> Rerank results</label>
            <label><input type="checkbox" id="opt-citations" checked> Generate citations</label>
            <label><input type="checkbox" id="opt-verify" checked> Verify sources</label>
          </aside>
          <main class="search-main">
            <div class="search-header">
              <h1>Advanced Search</h1>
              <p>Hybrid BM25 + dense retrieval across internal documents, web, images, videos, news, and academic sources.</p>
            </div>
            <div class="search-input-wrapper">
              <input type="text" id="search-input" placeholder="Search across documents, web, images, videos..." autocomplete="off" />
              <button class="btn btn-primary" id="search-btn">Search</button>
            </div>
            <div class="search-stats" id="search-stats"></div>
            <div class="search-tabs" id="search-tabs">
              <div class="search-tab active" data-tab="all">All</div>
              <div class="search-tab" data-tab="internal">Documents</div>
              <div class="search-tab" data-tab="web">Web</div>
              <div class="search-tab" data-tab="images">Images</div>
              <div class="search-tab" data-tab="videos">Videos</div>
              <div class="search-tab" data-tab="news">News</div>
              <div class="search-tab" data-tab="academic">Academic</div>
            </div>
            <div class="search-results" id="search-results"></div>
          </main>
        </div>
      </div>
    `;

    document.getElementById('logout-btn')?.addEventListener('click', () => this._handleLogout());
    window.searchApp = new SearchApp();
  }

  async _handleLogout() {
    try {
      await fetch(`${API_BASE}/auth/logout`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(getToken() ? { Authorization: `Bearer ${getToken()}` } : {}),
        },
      });
    } catch {
      // ignore
    }
    localStorage.removeItem('astrovox_access_token');
    localStorage.removeItem('astrovox_refresh_token');
    clearUser();
    this.authState = { user: null, isAuthenticated: false };
    this.chatApp = null;
    this.dashboardApp = null;
    showToast('Logged out successfully');
    window.location.href = '/login.html';
  }
}

function initRouter() {
  window.addEventListener('hashchange', () => {
    if (window.app) {
      window.app._checkAuthAndRoute();
    }
  });

  document.addEventListener('DOMContentLoaded', () => {
    window.app = new App();
  });
}

window.addEventListener('DOMContentLoaded', initRouter);
