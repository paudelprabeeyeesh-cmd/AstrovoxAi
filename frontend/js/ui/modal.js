// Frontend Platform - Group 6: Modal dialog with focus trap
const Modal = {
  _container: null,
  _activeModal: null,
  _previousFocus: null,

  open(options = {}) {
    if (this._activeModal) this.close();

    this._previousFocus = document.activeElement;
    const {
      title = '',
      content = '',
      onConfirm = null,
      onCancel = null,
      confirmText = 'Confirm',
      cancelText = 'Cancel',
      size = 'md',
      showClose = true,
    } = options;

    this._activeModal = {
      title,
      content,
      onConfirm,
      onCancel,
      confirmText,
      cancelText,
      size,
      showClose,
    };

    this._render();
    const { release } = A11y.trapFocus(this._container);
    this._trapRelease = release;
    this._container?.querySelector('.modal-close, .modal-confirm, .modal-cancel')?.focus();
  },

  close() {
    if (this._trapRelease) {
      this._trapRelease();
      this._trapRelease = null;
    }

    if (this._container) {
      Motion.scaleOut(this._container).then(() => {
        this._container?.remove();
        this._container = null;
      });
    }

    this._activeModal = null;

    if (this._previousFocus) {
      A11y.restoreFocus(this._previousFocus);
      this._previousFocus = null;
    }
  },

  confirm() {
    if (this._activeModal?.onConfirm) {
      const result = this._activeModal.onConfirm();
      if (result && typeof result.then === 'function') {
        result.catch(() => {});
      }
    }
    this.close();
  },

  cancel() {
    if (this._activeModal?.onCancel) {
      this._activeModal.onCancel();
    }
    this.close();
  },

  _render() {
    if (this._container) this._container.remove();

    const { title, content, confirmText, cancelText, size, showClose } = this._activeModal;

    this._container = document.createElement('div');
    this._container.className = 'modal-overlay';
    this._container.setAttribute('role', 'dialog');
    this._container.setAttribute('aria-modal', 'true');
    this._container.setAttribute('aria-labelledby', 'modal-title');

    this._container.innerHTML = `
      <div class="modal modal-${size}" role="document">
        <div class="modal-header">
          <h2 id="modal-title" class="modal-title">${title}</h2>
          ${showClose ? `<button class="modal-close" aria-label="Close">&times;</button>` : ''}
        </div>
        <div class="modal-body">${content}</div>
        <div class="modal-footer">
          <button class="btn btn-secondary modal-cancel">${cancelText}</button>
          <button class="btn btn-primary modal-confirm">${confirmText}</button>
        </div>
      </div>
    `;

    document.body.appendChild(this._container);
    Motion.scaleIn(this._container.querySelector('.modal'));

    this._container.querySelector('.modal-close')?.addEventListener('click', () => this.close());
    this._container.querySelector('.modal-cancel')?.addEventListener('click', () => this.cancel());
    this._container.querySelector('.modal-confirm')?.addEventListener('click', () => this.confirm());

    this._container.addEventListener('click', (e) => {
      if (e.target === this._container) this.cancel();
    });

    document.addEventListener('keydown', this._escHandler = (e) => {
      if (e.key === 'Escape') this.close();
    });
  },
};

window.Modal = Modal;
