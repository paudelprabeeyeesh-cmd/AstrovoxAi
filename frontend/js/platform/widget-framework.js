const WidgetFramework = {
  _widgets = new Map(),
  _layout = [],
  _container: null,

  register(widget) {
    const def = {
      id: widget.id || crypto.randomUUID(),
      name: widget.name,
      type: widget.type || 'custom',
      size: widget.size || 'medium',
      render: widget.render,
      onMount: widget.onMount || null,
      onUnmount: widget.onUnmount || null,
      onResize: widget.onResize || null,
      dependencies: widget.dependencies || [],
      refreshInterval: widget.refreshInterval || 0,
      _timer: null,
    };

    this._widgets.set(def.id, def);
    return def.id;
  },

  mount(container, widgetIds) {
    this._container = container;
    this._layout = widgetIds;

    container.innerHTML = '';
    container.className = 'dashboard-shell';

    widgetIds.forEach(id => {
      const widget = this._widgets.get(id);
      if (!widget) return;

      const el = document.createElement('div');
      el.className = `widget widget-${widget.size}`;
      el.id = `widget-${id}`;
      el.setAttribute('data-widget-id', id);
      el.innerHTML = `
        <div class="widget-header">
          <h3 class="widget-title">${widget.name}</h3>
          <div class="widget-actions">
            <button class="widget-action-btn" data-action="refresh" aria-label="Refresh">↻</button>
            <button class="widget-action-btn" data-action="settings" aria-label="Settings">⋯</button>
          </div>
        </div>
        <div class="widget-body">${widget.render()}</div>
        <div class="widget-footer"></div>
      `;

      el.querySelector('[data-action="refresh"]')?.addEventListener('click', () => this.refresh(id));
      el.querySelector('[data-action="settings"]')?.addEventListener('click', () => this._openSettings(id));

      container.appendChild(el);

      if (widget.onMount) {
        try {
          widget.onMount(el.querySelector('.widget-body'));
        } catch {}
      }

      if (widget.refreshInterval > 0) {
        widget._timer = setInterval(() => this.refresh(id), widget.refreshInterval);
      }
    });
  },

  refresh(id) {
    const widget = this._widgets.get(id);
    if (!widget) return;

    const el = document.getElementById(`widget-${id}`);
    if (!el) return;

    const body = el.querySelector('.widget-body');
    if (body) {
      try {
        body.innerHTML = widget.render();
        if (widget.onMount) widget.onMount(body);
      } catch (err) {
        body.innerHTML = `<div class="widget-error">Failed to refresh: ${err.message}</div>`;
      }
    }
  },

  unmount(id) {
    const widget = this._widgets.get(id);
    if (!widget) return;

    if (widget._timer) clearInterval(widget._timer);
    if (widget.onUnmount) {
      const el = document.getElementById(`widget-${id}`);
      try { widget.onUnmount(el?.querySelector('.widget-body')); } catch {}
    }

    document.getElementById(`widget-${id}`)?.remove();
    this._layout = this._layout.filter(lid => lid !== id);
  },

  _openSettings(id) {
    const widget = this._widgets.get(id);
    if (!widget) return;

    Modal.open({
      title: `${widget.name} Settings`,
      content: `<p>Configure ${widget.name} widget.</p>`,
      confirmText: 'Save',
      cancelText: 'Close',
    });
  },

  getLayout() {
    return [...this._layout];
  },

  setLayout(widgetIds) {
    this._layout = widgetIds;
    if (this._container) {
      this.mount(this._container, widgetIds);
    }
  },

  resize(id, size) {
    const el = document.getElementById(`widget-${id}`);
    if (el) {
      el.classList.remove('widget-small', 'widget-medium', 'widget-large', 'widget-full');
      el.classList.add(`widget-${size}`);
    }

    const widget = this._widgets.get(id);
    if (widget) {
      widget.size = size;
      if (widget.onResize) {
        const body = el?.querySelector('.widget-body');
        try { widget.onResize(body, size); } catch {}
      }
    }
  },
};

window.WidgetFramework = WidgetFramework;
