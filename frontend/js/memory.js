/* eslint-disable no-console */
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

async function memoryFetch(endpoint, options = {}) {
  const token = getToken();
  const res = await fetch(`${API_BASE}${endpoint}`, {
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...options.headers,
    },
    ...options,
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
        return memoryFetch(endpoint, options);
      }
    } catch {
      // fall through
    }
    showError('Session expired. Please log in again.');
    setTimeout(() => { window.location.href = '/login'; }, 2000);
    throw new Error('Unauthorized');
  }

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Request failed' }));
    throw new Error(err.detail || err.message || `HTTP ${res.status}`);
  }

  if (res.status === 204) {
    return null;
  }

  return res.json();
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

class MemoryPanel {
  constructor() {
    this.container = document.getElementById('memory-panel-content');
    this.searchInput = document.getElementById('memory-search-input');
    this.memoriesList = document.getElementById('memory-list');
    this.statsEl = document.getElementById('memory-stats');
    this.addForm = document.getElementById('memory-add-form');
    this._bindEvents();
    this._init();
  }

  _bindEvents() {
    if (this.searchInput) {
      this.searchInput.addEventListener('input', (e) => {
        this._search(e.target.value);
      });
    }
    if (this.addForm) {
      this.addForm.addEventListener('submit', (e) => {
        e.preventDefault();
        this._addMemory();
      });
    }
  }

  async _init() {
    await this._loadStats();
    await this._loadMemories();
  }

  async _loadStats() {
    if (!this.statsEl) return;
    try {
      const data = await memoryFetch('/memory-system/stats');
      const stats = data.stats || {};
      this.statsEl.innerHTML = `
        <div class="stat-card">
          <div class="stat-value">${stats.total || 0}</div>
          <div class="stat-label">Total Memories</div>
        </div>
        <div class="stat-card">
          <div class="stat-value">${stats.compressed || 0}</div>
          <div class="stat-label">Compressed</div>
        </div>
        <div class="stat-card">
          <div class="stat-value">${stats.knowledge_graph?.nodes || 0}</div>
          <div class="stat-label">Knowledge Nodes</div>
        </div>
        <div class="stat-card">
          <div class="stat-value">${stats.knowledge_graph?.edges || 0}</div>
          <div class="stat-label">Knowledge Edges</div>
        </div>
      `;
    } catch {
      this.statsEl.innerHTML = `
        <div class="stat-card"><div class="stat-value">-</div><div class="stat-label">Stats unavailable</div></div>
      `;
    }
  }

  async _loadMemories(query = '') {
    if (!this.memoriesList) return;
    try {
      const data = await memoryFetch(`/memory-system/recall${query ? '?query=' + encodeURIComponent(query) : ''}`);
      const memories = data.memories || [];
      if (!memories.length) {
        this.memoriesList.innerHTML = '<div class="empty-state">No memories found</div>';
        return;
      }
      this.memoriesList.innerHTML = memories.map(m => `
        <div class="memory-item" data-id="${m.memory_id}">
          <div class="memory-header">
            <span class="memory-category">${m.category}</span>
            <span class="memory-tier ${m.tier}">${m.tier}</span>
          </div>
          <div class="memory-content">${this._escapeHtml(m.content)}</div>
          <div class="memory-footer">
            <span class="memory-importance">Importance: ${(m.importance * 100).toFixed(0)}%</span>
            <span class="memory-date">${new Date(m.accessed_at).toLocaleDateString()}</span>
          </div>
          <div class="memory-actions">
            <button class="btn btn-sm btn-secondary" onclick="memoryPanel.editMemory('${m.memory_id}')">Edit</button>
            <button class="btn btn-sm btn-danger" onclick="memoryPanel.deleteMemory('${m.memory_id}')">Delete</button>
          </div>
        </div>
      `).join('');
    } catch {
      this.memoriesList.innerHTML = '<div class="empty-state">Failed to load memories</div>';
    }
  }

  async _addMemory() {
    if (!this.addForm) return;
    const formData = new FormData(this.addForm);
    const content = formData.get('content')?.toString().trim();
    if (!content) return;
    try {
      await memoryFetch('/memory-system/remember', {
        method: 'POST',
        body: JSON.stringify({
          content,
          category: formData.get('category') || 'fact',
          tier: formData.get('tier') || 'medium',
          user_explicit: true,
        }),
      });
      this.addForm.reset();
      showToast('Memory saved');
      this._loadMemories();
      this._loadStats();
    } catch (err) {
      showError(err.message);
    }
  }

  async editMemory(memoryId) {
    const newContent = prompt('Edit memory:');
    if (!newContent || !newContent.trim()) return;
    try {
      await memoryFetch(`/memory-system/memory/${memoryId}`, {
        method: 'PUT',
        body: JSON.stringify({ memory_id: memoryId, content: newContent.trim() }),
      });
      showToast('Memory updated');
      this._loadMemories();
    } catch (err) {
      showError(err.message);
    }
  }

  async deleteMemory(memoryId) {
    if (!confirm('Delete this memory?')) return;
    try {
      await memoryFetch(`/memory-system/memory/${memoryId}`, {
        method: 'DELETE',
      });
      showToast('Memory deleted');
      this._loadMemories();
      this._loadStats();
    } catch (err) {
      showError(err.message);
    }
  }

  async _search(query) {
    await this._loadMemories(query);
  }

  _escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }
}

let memoryPanel;

function initMemoryPanel() {
  if (!memoryPanel) {
    memoryPanel = new MemoryPanel();
  }
  return memoryPanel;
}

if (typeof window !== 'undefined') {
  window.addEventListener('DOMContentLoaded', () => {
    const memoryPanelEl = document.getElementById('memory-panel');
    if (memoryPanelEl) {
      initMemoryPanel();
    }
  });
}
