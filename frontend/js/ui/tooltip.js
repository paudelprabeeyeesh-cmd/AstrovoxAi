// Frontend Platform - Group 6: Tooltip with positioning and accessibility
const Tooltip = {
  _instances: new Map(),
  _globalHandler: null,

  attach(element, text, options = {}) {
    const tooltip = document.createElement('div');
    tooltip.className = 'tooltip';
    tooltip.setAttribute('role', 'tooltip');
    tooltip.id = 'tooltip-' + Date.now() + '-' + Math.random().toString(36).slice(2, 8);
    tooltip.textContent = text;
    document.body.appendChild(tooltip);

    const instance = {
      element,
      tooltip,
      options: {
        position: options.position || 'top',
        delay: options.delay || 400,
        offset: options.offset || 8,
      },
    };

    let timeout;
    const show = () => {
      timeout = setTimeout(() => this._show(instance), instance.options.delay);
    };

    const hide = () => {
      clearTimeout(timeout);
      this._hide(instance);
    };

    element.addEventListener('mouseenter', show);
    element.addEventListener('mouseleave', hide);
    element.addEventListener('focus', show);
    element.addEventListener('blur', hide);

    element.setAttribute('aria-describedby', tooltip.id);
    this._instances.set(tooltip.id, instance);

    return {
      update(newText) {
        tooltip.textContent = newText;
      },
      destroy() {
        hide();
        tooltip.remove();
        element.removeAttribute('aria-describedby');
        this._instances.delete(tooltip.id);
      },
    };
  },

  _show(instance) {
    const { element, tooltip, options } = instance;
    const rect = element.getBoundingClientRect();
    const tooltipRect = tooltip.getBoundingClientRect();

    let top, left;

    switch (options.position) {
      case 'bottom':
        top = rect.bottom + options.offset;
        left = rect.left + rect.width / 2 - tooltipRect.width / 2;
        break;
      case 'left':
        top = rect.top + rect.height / 2 - tooltipRect.height / 2;
        left = rect.left - tooltipRect.width - options.offset;
        break;
      case 'right':
        top = rect.top + rect.height / 2 - tooltipRect.height / 2;
        left = rect.right + options.offset;
        break;
      default:
        top = rect.top - tooltipRect.height - options.offset;
        left = rect.left + rect.width / 2 - tooltipRect.width / 2;
    }

    left = Math.max(8, Math.min(left, window.innerWidth - tooltipRect.width - 8));
    top = Math.max(8, Math.min(top, window.innerHeight - tooltipRect.height - 8));

    tooltip.style.top = top + 'px';
    tooltip.style.left = left + 'px';
    tooltip.classList.add('tooltip-visible');
  },

  _hide(instance) {
    instance.tooltip.classList.remove('tooltip-visible');
  },

  destroyAll() {
    this._instances.forEach((instance, id) => {
      instance.tooltip.remove();
      instance.element.removeAttribute('aria-describedby');
    });
    this._instances.clear();
  },
};

window.Tooltip = Tooltip;
