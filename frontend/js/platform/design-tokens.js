// Frontend Platform - Group 7: Design token system
const DesignTokens = {
  _customTokens: new Map(),
  _computedTokens: new Map(),

  define(tokenName, value, override = false) {
    if (!override && this._customTokens.has(tokenName)) {
      return this._customTokens.get(tokenName);
    }

    this._customTokens.set(tokenName, value);
    document.documentElement.style.setProperty(`--token-${tokenName}`, value);
    return value;
  },

  get(tokenName) {
    if (this._customTokens.has(tokenName)) {
      return this._customTokens.get(tokenName);
    }

    const computed = getComputedStyle(document.documentElement).getPropertyValue(`--token-${tokenName}`);
    return computed?.trim() || null;
  },

  remove(tokenName) {
    this._customTokens.delete(tokenName);
    document.documentElement.style.removeProperty(`--token-${tokenName}`);
  },

  defineGroup(group) {
    for (const [name, value] of Object.entries(group)) {
      this.define(name, value);
    }
  },

  spacing: {
    xs: '0.25rem',
    sm: '0.5rem',
    md: '1rem',
    lg: '1.5rem',
    xl: '2rem',
    '2xl': '3rem',
  },

  typography: {
    fontSizes: {
      xs: '0.75rem',
      sm: '0.875rem',
      base: '1rem',
      lg: '1.125rem',
      xl: '1.25rem',
      '2xl': '1.5rem',
      '3xl': '1.875rem',
    },
    fontWeights: {
      normal: 400,
      medium: 500,
      semibold: 600,
      bold: 700,
    },
    lineHeights: {
      tight: 1.25,
      normal: 1.5,
      relaxed: 1.75,
    },
  },

  borderRadius: {
    none: '0',
    sm: '0.25rem',
    md: '0.5rem',
    lg: '0.75rem',
    xl: '1rem',
    full: '9999px',
  },

  shadows: {
    sm: '0 1px 2px 0 rgb(0 0 0 / 0.05)',
    md: '0 4px 6px -1px rgb(0 0 0 / 0.1)',
    lg: '0 10px 15px -3px rgb(0 0 0 / 0.1)',
    xl: '0 20px 25px -5px rgb(0 0 0 / 0.1)',
  },

  init() {
    this.defineGroup({ ...this.spacing, prefix: 'space' });
    this.defineGroup({ ...this.typography.fontSizes, prefix: 'fontSize' });
  },
};

window.DesignTokens = DesignTokens;
