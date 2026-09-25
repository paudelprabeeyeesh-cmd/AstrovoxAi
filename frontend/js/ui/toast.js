const Toast = {
  _container: null,
  _toasts = [],

  init() {
    if (this._container) return;

    this._container = document.createElement('div');
    this._container.id = 'toast-container';
    this._container.className = 'toast-container';
    this._container.setAttribute('role', 'region');
    this._container.setAttribute('aria-label', 'Notifications');
    document.body.appendChild(this._container);
  },

  show(message, options = {}) {
    this.init();

    const {
      type = 'info',
      duration = 4000,
      closable = true,
      action = null,
    } = options;

    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.setAttribute('role', 'alert');
    toast.innerHTML = `
      <span class="toast-message">${message}</span>
      ${action ? `<button class="toast-action">${action.label}</button>` : ''}
      ${closable ? `<button class="toast-close" aria-label="Dismiss">&times;</button>` : ''}
    `;

    if (action) {
      toast.querySelector('.toast-action')?.addEventListener('click', () => {
        action.handler();
        this.dismiss(toast);
      });
    }

    toast.querySelector('.toast-close')?.addEventListener('click', () => this.dismiss(toast));

    this._container.appendChild(toast);
    this._toasts.push(toast);

    if (duration > 0) {
      setTimeout(() => this.dismiss(toast), duration);
    }

    return toast;
  },

  success(message, options = {}) {
    return this.show(message, { ...options, type: 'success' });
  },

  error(message, options = {}) {
    return this.show(message, { ...options, type: 'error', duration: 6000 });
  },

  warning(message, options = {}) {
    return this.show(message, { ...options, type: 'warning' });
  },

  info(message, options = {}) {
    return this.show(message, { ...options, type: 'info' });
  },

  dismiss(toast) {
    if (!toast || !toast.parentNode) return;

    Motion.slideOutRight(toast).then(() => {
      toast.remove();
      this._toasts = this._toasts.filter(t => t !== toast);
    });
  },

  clear() {
    this._toasts.forEach(toast => this.dismiss(toast));
  },
};

window.Toast = Toast;
