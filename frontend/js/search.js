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
    setTimeout(() => toast.remove(), 3000);
  }, 3000);
}

async function searchFetch(endpoint, options = {}) {
  const token = getToken();
  const headers = {
    'Content-Type': 'application/json',
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...options.headers,
  };

  const res = await fetch(`${API_BASE}${endpoint}`, {
    ...options,
    headers,
  });

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
    } catch {}
    window.location.href = '/login.html';
    return Promise.reject(new Error('Unauthorized'));
  }
  return handleResponse(res);
}

function handleResponse(res) {
  if (!res.ok) {
    return res.json().then(err => Promise.reject(new Error(err.detail || err.message || `HTTP ${res.status}`)));
  }
  if (res.status === 204) return Promise.resolve({});
  return res.json();
}

class SearchApp {
  constructor() {
    this.currentTab = 'all';
    this.lastResults = [];
    this.init();
  }

  init() {
    const user = getUser();
    const emailEl = document.getElementById('user-email');
    if (emailEl && user) emailEl.textContent = user.email || 'User';

    document.getElementById('logout-btn')?.addEventListener('click', () => this.handleLogout());
    document.getElementById('search-btn')?.addEventListener('click', () => this.executeSearch());
    document.getElementById('search-input')?.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') this.executeSearch();
    });

    document.querySelectorAll('.search-tab').forEach(tab => {
      tab.addEventListener('click', () => {
        document.querySelectorAll('.search-tab').forEach(t => t.classList.remove('active'));
        tab.classList.add('active');
        this.currentTab = tab.dataset.tab;
        this.renderResults();
      });
    });
  }

  async executeSearch() {
    const query = document.getElementById('search-input')?.value?.trim();
    if (!query) return;

    const resultsEl = document.getElementById('search-results');
    const statsEl = document.getElementById('search-stats');
    resultsEl.innerHTML = '<div class="search-loading"><div class="spinner"></div><span>Searching...</span></div>';
    statsEl.textContent = '';

    const body = {
      query,
      top_k: 20,
      alpha: 0.5,
      sources: this._getSelectedSources(),
      include_web: document.getElementById('src-web')?.checked ?? true,
      include_images: document.getElementById('src-images')?.checked ?? false,
      include_videos: document.getElementById('src-videos')?.checked ?? false,
      include_news: document.getElementById('src-news')?.checked ?? false,
      include_academic: document.getElementById('src-academic')?.checked ?? false,
      include_internal: document.getElementById('src-internal')?.checked ?? true,
      rerank: document.getElementById('opt-rerank')?.checked ?? true,
      generate_citations: document.getElementById('opt-citations')?.checked ?? true,
      verify_sources: document.getElementById('opt-verify')?.checked ?? true,
    };

    try {
      const data = await searchFetch('/search/advanced', { method: 'POST', body: JSON.stringify(body) });
      this.lastResults = data.results || [];
      statsEl.textContent = `${data.result_count || 0} results in ${data.latency_ms || 0}ms from ${(data.sources || []).join(', ')}`;
      this.renderResults();
    } catch (err) {
      resultsEl.innerHTML = `<div class="search-empty"><p>Search failed: ${this._escapeHtml(err.message)}</p></div>`;
    }
  }

  _getSelectedSources() {
    const sources = [];
    if (document.getElementById('src-internal')?.checked) sources.push('internal');
    if (document.getElementById('src-web')?.checked) sources.push('web');
    if (document.getElementById('src-images')?.checked) sources.push('images');
    if (document.getElementById('src-videos')?.checked) sources.push('videos');
    if (document.getElementById('src-news')?.checked) sources.push('news');
    if (document.getElementById('src-academic')?.checked) sources.push('academic');
    return sources.length ? sources : ['hybrid'];
  }

  renderResults() {
    const resultsEl = document.getElementById('search-results');
    let results = this.lastResults;
    if (this.currentTab !== 'all') {
      results = results.filter(r => r.source_type === this.currentTab);
    }
    if (!results.length) {
      resultsEl.innerHTML = '<div class="search-empty"><p>No results found. Try adjusting your search or sources.</p></div>';
      return;
    }
    resultsEl.innerHTML = results.map((r, idx) => {
      const badgeClass = r.verified ? 'badge-verified' : 'badge-unverified';
      const badgeText = r.verified ? 'Verified' : 'Unverified';
      const verificationLabel = r.verified ? 'Verified source' : 'Unverified source';
      const scoreLabel = r.score ? `Score: ${r.score.toFixed(3)}` : '';
      const citationHtml = r.citation ? `<div class="search-citation">${this._escapeHtml(r.citation)}</div>` : '';
      const highlights = (r.highlights || []).map(h => `<div style="font-size:0.8rem;color:var(--text-muted);margin-top:0.25rem;">${this._escapeHtml(h)}</div>`).join('');
      return `
        <div class="search-result-card">
          <div class="search-result-header">
            <a href="${this._escapeHtml(r.url || '#')}" target="_blank" rel="noopener" class="search-result-title">${this._escapeHtml(r.title || 'Untitled')}</a>
            <span class="search-result-badge ${badgeClass}" title="${this._escapeHtml(verificationLabel)}">${badgeText}</span>
          </div>
          <div class="search-result-desc">${this._escapeHtml(r.content || '')}</div>
          ${highlights}
          ${citationHtml}
          <div class="search-result-meta">
            <span>${this._escapeHtml(r.source_name || r.source_type || '')}</span>
            <span>${scoreLabel}</span>
            <span>Type: ${this._escapeHtml(r.source_type || '')}</span>
          </div>
        </div>
      `;
    }).join('');
  }

  _escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }

  async handleLogout() {
    try {
      await fetch(`${API_BASE}/auth/logout`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(getToken() ? { Authorization: `Bearer ${getToken()}` } : {}),
        },
      });
    } catch {}
    localStorage.removeItem('astrovox_access_token');
    localStorage.removeItem('astrovox_refresh_token');
    showToast('Logged out successfully');
    window.location.href = '/login.html';
  }
}

function initSearchApp() {
  window.searchApp = new SearchApp();
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initSearchApp);
} else {
  initSearchApp();
}
