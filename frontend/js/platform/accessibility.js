// Frontend Platform - Group 1: Accessible component primitives and focus management
const FOCUSABLE_SELECTOR = [
  'a[href]',
  'button:not([disabled])',
  'input:not([disabled])',
  'textarea:not([disabled])',
  'select:not([disabled])',
  '[tabindex]:not([tabindex="-1"])',
  'audio[controls]',
  'video[controls]',
  '[contenteditable]:not([contenteditable="false"])',
  'details > summary',
  'details',
  'fieldset',
  'output',
].join(', ');

function getFocusableElements(root = document) {
  return Array.from(root.querySelectorAll(FOCUSABLE_SELECTOR)).filter(
    (el) => !el.hasAttribute('disabled') && el.offsetParent !== null
  );
}

function trapFocus(container) {
  const focusable = getFocusableElements(container);
  if (!focusable.length) return () => {};

  const first = focusable[0];
  const last = focusable[focusable.length - 1];

  function handler(e) {
    if (e.key !== 'Tab') return;
    if (e.shiftKey) {
      if (document.activeElement === first) {
        e.preventDefault();
        last.focus();
      }
    } else {
      if (document.activeElement === last) {
        e.preventDefault();
        first.focus();
      }
    }
  }

  container.addEventListener('keydown', handler);
  first.focus();

  return () => container.removeEventListener('keydown', handler);
}

function restoreFocus(element) {
  if (element && typeof element.focus === 'function') {
    element.focus();
  }
}

function announce(message, priority = 'polite') {
  let liveRegion = document.getElementById('a11y-live-region');
  if (!liveRegion) {
    liveRegion = document.createElement('div');
    liveRegion.id = 'a11y-live-region';
    liveRegion.setAttribute('aria-live', 'polite');
    liveRegion.setAttribute('aria-atomic', 'true');
    liveRegion.className = 'sr-only';
    liveRegion.style.cssText = 'position:absolute;width:1px;height:1px;padding:0;margin:-1px;overflow:hidden;clip:rect(0,0,0,0);white-space:nowrap;border:0;';
    document.body.appendChild(liveRegion);
  }
  liveRegion.setAttribute('aria-live', priority);
  liveRegion.textContent = '';
  requestAnimationFrame(() => {
    liveRegion.textContent = message;
  });
}

function skipToMain() {
  const main = document.getElementById('main-content') || document.querySelector('main');
  if (main) {
    main.setAttribute('tabindex', '-1');
    main.focus();
    main.addEventListener('blur', () => main.removeAttribute('tabindex'), { once: true });
  }
}

class FocusManager {
  constructor() {
    this._previousActive = null;
    this._containers = new Map();
  }

  register(containerId, containerElement) {
    this._containers.set(containerId, containerElement);
  }

  capture() {
    this._previousActive = document.activeElement;
  }

  restore() {
    restoreFocus(this._previousActive);
    this._previousActive = null;
  }

  trap(containerId) {
    const container = this._containers.get(containerId);
    if (!container) return () => {};
    return trapFocus(container);
  }

  moveToNext() {
    const focusable = getFocusableElements();
    if (!focusable.length) return;
    const current = document.activeElement;
    const idx = focusable.indexOf(current);
    const next = focusable[(idx + 1) % focusable.length];
    next?.focus();
  }

  moveToPrevious() {
    const focusable = getFocusableElements();
    if (!focusable.length) return;
    const current = document.activeElement;
    const idx = focusable.indexOf(current);
    const prev = focusable[(idx - 1 + focusable.length) % focusable.length];
    prev?.focus();
  }
}

window.A11y = {
  FOCUSABLE_SELECTOR,
  getFocusableElements,
  trapFocus,
  restoreFocus,
  announce,
  skipToMain,
  FocusManager,
};
