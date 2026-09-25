const Motion = {
  _prefersReducedMotion() {
    return window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  },

  animate(element, keyframes, options = {}) {
    if (this._prefersReducedMotion()) {
      if (options.finalStyle) {
        Object.assign(element.style, options.finalStyle);
      }
      return Promise.resolve();
    }

    const duration = options.duration ?? 300;
    const easing = options.easing ?? 'ease';
    const fill = options.fill ?? 'forwards';

    return element.animate(keyframes, {
      duration,
      easing,
      fill,
      delay: options.delay ?? 0,
    }).finished;
  },

  fadeIn(element, options = {}) {
    return this.animate(element, [
      { opacity: '0', transform: 'translateY(0.5rem)' },
      { opacity: '1', transform: 'translateY(0)' },
    ], { duration: 300, ...options, finalStyle: { opacity: '1', transform: 'none' } });
  },

  fadeOut(element, options = {}) {
    return this.animate(element, [
      { opacity: '1', transform: 'translateY(0)' },
      { opacity: '0', transform: 'translateY(0.5rem)' },
    ], { duration: 300, ...options, finalStyle: { opacity: '0', transform: 'translateY(0.5rem)' } });
  },

  slideInRight(element, options = {}) {
    return this.animate(element, [
      { transform: 'translateX(100%)', opacity: '0' },
      { transform: 'translateX(0)', opacity: '1' },
    ], { duration: 300, ...options, finalStyle: { transform: 'none', opacity: '1' } });
  },

  slideOutRight(element, options = {}) {
    return this.animate(element, [
      { transform: 'translateX(0)', opacity: '1' },
      { transform: 'translateX(100%)', opacity: '0' },
    ], { duration: 300, ...options, finalStyle: { transform: 'translateX(100%)', opacity: '0' } });
  },

  scaleIn(element, options = {}) {
    return this.animate(element, [
      { opacity: '0', transform: 'scale(0.95)' },
      { opacity: '1', transform: 'scale(1)' },
    ], { duration: 200, ...options, finalStyle: { opacity: '1', transform: 'scale(1)' } });
  },

  scaleOut(element, options = {}) {
    return this.animate(element, [
      { opacity: '1', transform: 'scale(1)' },
      { opacity: '0', transform: 'scale(0.95)' },
    ], { duration: 200, ...options, finalStyle: { opacity: '0', transform: 'scale(0.95)' } });
  },

  pulse(element, options = {}) {
    if (this._prefersReducedMotion()) return Promise.resolve();
    return this.animate(element, [
      { transform: 'scale(1)' },
      { transform: 'scale(1.05)' },
      { transform: 'scale(1)' },
    ], { duration: 300, ...options, finalStyle: { transform: 'scale(1)' } });
  },

  shake(element, options = {}) {
    if (this._prefersReducedMotion()) return Promise.resolve();
    return this.animate(element, [
      { transform: 'translateX(0)' },
      { transform: 'translateX(-4px)' },
      { transform: 'translateX(4px)' },
      { transform: 'translateX(-4px)' },
      { transform: 'translateX(4px)' },
      { transform: 'translateX(0)' },
    ], { duration: 400, ...options, finalStyle: { transform: 'translateX(0)' } });
  },
};

window.Motion = Motion;
