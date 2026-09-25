const CommandPalette = {
  _container: null,
  _input: null,
  _results: null,
  _commands = [],
  _isOpen = false,
  _selectedIndex = 0,

  register(command) {
    this._commands.push({
      id: command.id || crypto.randomUUID(),
      label: command.label,
      shortcut: command.shortcut || null,
      icon: command.icon || null,
      keywords: command.keywords || [],
      action: command.action,
      category: command.category || 'General',
    });
  },

  open() {
    if (this._isOpen) return;
    this._isOpen = true;
    this._render();
    this._input?.focus();
    document.addEventListener('keydown', this._handleKeydown);
    document.addEventListener('click', this._handleClickOutside);
  },

  close() {
    if (!this._isOpen) return;
    this._isOpen = false;
    this._container?.remove();
    this._container = null;
    this._input = null;
    this._results = null;
    this._selectedIndex = 0;
    document.removeEventListener('keydown', this._handleKeydown);
    document.removeEventListener('click', this._handleClickOutside);
  },

  _handleKeydown = (e) => {
    if (e.key === 'Escape') {
      this.close();
      return;
    }

    if (e.key === 'ArrowDown') {
      e.preventDefault();
      this._selectedIndex = Math.min(this._selectedIndex + 1, this._results?.children.length ?? 0);
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

  _handleClickOutside = (e) => {
    if (this._container && !this._container.contains(e.target)) {
      this.close();
    }
  },

  _render() {
    if (this._container) this._container.remove();

    this._container = document.createElement('div');
    this._container.className = 'command-palette-overlay';
    this._container.setAttribute('role', 'dialog');
    this._container.setAttribute('aria-modal', 'true');
    this._container.setAttribute('aria-label', 'Command palette');

    this._container.innerHTML = `
      <div class="command-palette">
        <div class="command-palette-input-wrapper">
          <span class="command-palette-icon" aria-hidden="true">🔍</span>
          <input type="text" class="command-palette-input" placeholder="Type a command or search..." autocomplete="off" />
          <kbd class="command-palette-shortcut">ESC</kbd>
        </div>
        <div class="command-palette-results" role="listbox"></div>
      </div>
    `;

    this._input = this._container.querySelector('.command-palette-input');
    this._results = this._container.querySelector('.command-palette-results');

    this._input?.addEventListener('input', (e) => this._filter(e.target.value));
    this._input?.addEventListener('keydown', this._handleKeydown);

    this._filter('');
    document.body.appendChild(this._container);
  },

  _filter(query) {
    if (!this._results) return;

    const lower = query.toLowerCase();
    const filtered = this._commands.filter(cmd => {
      if (!query) return true;
      return (
        cmd.label.toLowerCase().includes(lower) ||
        cmd.keywords.some(k => k.toLowerCase().includes(lower)) ||
        cmd.category.toLowerCase().includes(lower)
      );
    });

    this._selectedIndex = 0;
    this._results.innerHTML = filtered.map((cmd, idx) => `
      <div class="command-palette-item ${idx === 0 ? 'selected' : ''}" role="option" data-id="${cmd.id}" data-index="${idx}">
        <span class="command-palette-item-label">${cmd.label}</span>
        <span class="command-palette-item-meta">
          ${cmd.category ? `<span class="command-palette-category">${cmd.category}</span>` : ''}
          ${cmd.shortcut ? `<kbd>${cmd.shortcut}</kbd>` : ''}
        </span>
      </div>
    `).join('');

    this._results.querySelectorAll('.command-palette-item').forEach(item => {
      item.addEventListener('click', () => {
        const id = item.dataset.id;
        const cmd = this._commands.find(c => c.id === id);
        if (cmd) {
          this.close();
          cmd.action();
        }
      });
    });
  },

  _updateSelection() {
    const items = this._results?.querySelectorAll('.command-palette-item');
    items?.forEach((item, idx) => {
      item.classList.toggle('selected', idx === this._selectedIndex);
    });
  },

  _executeSelected() {
    const items = this._results?.querySelectorAll('.command-palette-item');
    const selected = items?.[this._selectedIndex];
    if (selected) {
      const id = selected.dataset.id;
      const cmd = this._commands.find(c => c.id === id);
      if (cmd) {
        this.close();
        cmd.action();
      }
    }
  },
};

window.CommandPalette = CommandPalette;
