// Frontend Platform - Group 9: Global search with keyboard navigation
const GlobalSearch = {
  _container: null,
  _input: null,
  _results: null,
  _isOpen = false,
  _sources = [],
  _query = '',
  _selectedIndex = 0,
  _currentResults = [],

  registerSource(source) {
    this._sources.push({
      id: source.id || crypto.randomUUID(),
      name: source.name,
      icon: source.icon || '📄',
      search: source.search,
      maxResults: source.maxResults || 5,
    });
  },

  open() {
    if (this._isOpen) return;
    this._isOpen = true;
    this._render();
    this._input?.focus();
    document.addEventListener('keydown', this._keyHandler);
    document.addEventListener('click', this._clickHandler);
  },

  close() {
    if (!this._isOpen) return;
    this._isOpen = false;
    this._container?.remove();
    this._container = null;
    this._input = null;
    this._results = null;
    this._selectedIndex = 0;
    this._currentResults = [];
    document.removeEventListener('keydown', this._keyHandler);
    document.removeEventListener('click', this._clickHandler);
  },

  _keyHandler = (e) => {
    if (e.key === 'Escape') {
      this.close();
      return;
    }

    if (e.key === 'ArrowDown') {
      e.preventDefault();
      this._selectedIndex = Math.min(this._selectedIndex + 1, this._currentResults.length);
      this._updateSelection();
      return;
    }

    if (e.key === 'ArrowUp') {
      e.preventDefault();
      this._selectedIndex = Math.max(this._selectedIndex - 1, 0);
      this._updateSelection();
      return;
    }

    if (e.key === 'Enter') {
      e.preventDefault();
      this._executeSelected();
      return;
    }
  },

  _clickHandler = (e) => {
    if (this._container && !this._container.contains(e.target)) {
      this.close();
    }
  },

  _render() {
    if (this._container) this._container.remove();

    this._container = document.createElement('div');
    this._container.className = 'global-search-overlay';
    this._container.setAttribute('role', 'dialog');
    this._container.setAttribute('aria-modal', 'true');
    this._container.setAttribute('aria-label', 'Global search');

    this._container.innerHTML = `
      <div class="global-search">
        <div class="global-search-input-wrapper">
          <span class="global-search-icon" aria-hidden="true">🔍</span>
          <input type="text" class="global-search-input" placeholder="Search across conversations, files, and commands..." autocomplete="off" />
          <kbd class="global-search-shortcut">ESC</kbd>
        </div>
        <div class="global-search-results" role="listbox"></div>
        <div class="global-search-footer">
          <span><kbd>↑↓</kbd> Navigate</span>
          <span><kbd>↵</kbd> Open</span>
          <span><kbd>ESC</kbd> Close</span>
        </div>
      </div>
    `;

    this._input = this._container.querySelector('.global-search-input');
    this._results = this._container.querySelector('.global-search-results');

    this._input?.addEventListener('input', (e) => this._search(e.target.value));
    this._input?.addEventListener('keydown', this._keyHandler);

    this._search('');
    document.body.appendChild(this._container);
  },

  async _search(query) {
    if (!this._results) return;

    this._query = query;
    this._selectedIndex = 0;
    this._currentResults = [];

    if (!query.trim()) {
      this._renderSuggestions();
      return;
    }

    const allResults = [];
    for (const source of this._sources) {
      try {
        const results = await source.search(query);
        const items = (results || []).slice(0, source.maxResults).map(r => ({
          ...r,
          sourceId: source.id,
          sourceName: source.name,
          sourceIcon: source.icon,
        }));
        allResults.push(...items);
      } catch {
        // skip failed source
      }
    }

    this._currentResults = allResults;
    this._renderResults(allResults);
  },

  _renderSuggestions() {
    if (!this._results) return;

    const sourcesHtml = this._sources.map(source => `
      <div class="global-search-source">
        <span class="global-search-source-icon">${source.icon}</span>
        <span>${source.name}</span>
      </div>
    `).join('');

    this._results.innerHTML = `
      <div class="global-search-suggestions">
        <div class="global-search-suggestions-title">Sources</div>
        ${sourcesHtml}
      </div>
    `;
  },

  _renderResults(results) {
    if (!this._results) return;

    if (results.length === 0) {
      this._results.innerHTML = `
        <div class="global-search-empty">
          <div class="global-search-empty-icon">🔍</div>
          <p>No results found for "${this._escapeHtml(this._query)}"</p>
        </div>
      `;
      return;
    }

    this._results.innerHTML = results.map((result, idx) => `
      <div class="global-search-result-item ${idx === 0 ? 'selected' : ''}" role="option" data-index="${idx}" data-url="${result.url || '#'}">
        <span class="global-search-result-icon">${result.sourceIcon || '📄'}</span>
        <div class="global-search-result-content">
          <div class="global-search-result-title">${this._escapeHtml(result.title)}</div>
          <div class="global-search-result-desc">${this._escapeHtml(result.description || '')}</div>
        </div>
        <span class="global-search-result-source">${result.sourceName}</span>
      </div>
    `).join('');

    this._results.querySelectorAll('.global-search-result-item').forEach(item => {
      item.addEventListener('click', () => {
        const url = item.dataset.url;
        if (url && url !== '#') {
          window.location.href = url;
        }
        this.close();
      });
    });
  },

  _updateSelection() {
    const items = this._results?.querySelectorAll('.global-search-result-item');
    items?.forEach((item, idx) => {
      item.classList.toggle('selected', idx === this._selectedIndex);
    });
  },

  _executeSelected() {
    const items = this._results?.querySelectorAll('.global-search-result-item');
    const selected = items?.[this._selectedIndex];
    if (selected) {
      const url = selected.dataset.url;
      if (url && url !== '#') {
        window.location.href = url;
      }
      this.close();
    }
  },

  _escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  },
};

window.GlobalSearch = GlobalSearch;
