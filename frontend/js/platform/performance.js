// Frontend Platform - Group 15: Performance budgets and bundle-splitting hooks
const Performance = {
  _metrics: {
    fcp: null,
    lcp: null,
    fid: null,
    cls: 0,
    ttfb: null,
    loadTime: null,
    domContentLoaded: null,
  },
  _budgets: {
    js: 500,
    css: 100,
    images: 500,
    total: 1000,
  },
  _observers: [],

  init() {
    this._measureNavigation();
    this._observeWebVitals();
    this._observeResources();
    this._checkBudgets();
  },

  _measureNavigation() {
    const nav = performance.getEntriesByType('navigation')[0];
    if (!nav) return;

    this._metrics.ttfb = nav.responseStart - nav.requestStart;
    this._metrics.loadTime = nav.loadEventEnd - nav.fetchStart;
    this._metrics.domContentLoaded = nav.domContentLoadedEventEnd - nav.fetchStart;

    this._emit('navigation', this._metrics);
  },

  _observeWebVitals() {
    try {
      const paintObserver = new PerformanceObserver((list) => {
        for (const entry of list.getEntries()) {
          if (entry.name === 'first-contentful-paint') {
            this._metrics.fcp = entry.startTime;
          }
        }
      });
      paintObserver.observe({ type: 'paint', buffered: true });
      this._observers.push(paintObserver);
    } catch {}

    try {
      const lcpObserver = new PerformanceObserver((list) => {
        const entries = list.getEntries();
        const last = entries[entries.length - 1];
        this._metrics.lcp = last.startTime;
        this._emit('lcp', { value: this._metrics.lcp });
      });
      lcpObserver.observe({ type: 'largest-contentful-paint', buffered: true });
      this._observers.push(lcpObserver);
    } catch {}

    try {
      const fidObserver = new PerformanceObserver((list) => {
        for (const entry of list.getEntries()) {
          this._metrics.fid = entry.processingStart - entry.startTime;
          this._emit('fid', { value: this._metrics.fid });
        }
      });
      fidObserver.observe({ type: 'first-input', buffered: true });
      this._observers.push(fidObserver);
    } catch {}

    try {
      const clsObserver = new PerformanceObserver((list) => {
        for (const entry of list.getEntries()) {
          if (!entry.hadRecentInput) {
            this._metrics.cls += entry.value;
          }
        }
        this._emit('cls', { value: this._metrics.cls });
      });
      clsObserver.observe({ type: 'layout-shift', buffered: true });
      this._observers.push(clsObserver);
    } catch {}
  },

  _observeResources() {
    try {
      const resourceObserver = new PerformanceObserver((list) => {
        const resources = list.getEntries().map(entry => ({
          name: entry.name,
          type: entry.initiatorType,
          size: entry.transferSize || 0,
          duration: entry.duration,
        }));

        this._emit('resources', resources);
        this._checkBudgets(resources);
      });
      resourceObserver.observe({ type: 'resource', buffered: true });
      this._observers.push(resourceObserver);
    } catch {}
  },

  _checkBudgets(resources) {
    if (!resources) {
      resources = performance.getEntriesByType('resource').map(entry => ({
        type: entry.initiatorType,
        size: entry.transferSize || 0,
      }));
    }

    const totals = resources.reduce((acc, r) => {
      const category = r.type === 'script' ? 'js' : r.type === 'css' ? 'css' : r.type === 'image' ? 'images' : 'other';
      acc[category] = (acc[category] || 0) + r.size;
      return acc;
    }, {});

    const violations = [];
    for (const [category, budget] of Object.entries(this._budgets)) {
      if (totals[category] > budget * 1024) {
        violations.push({
          category,
          actual: Math.round(totals[category] / 1024),
          budget,
          unit: 'KB',
        });
      }
    }

    if (violations.length > 0) {
      this._emit('budget_violations', violations);
    }
  },

  setBudget(category, sizeKB) {
    this._budgets[category] = sizeKB;
  },

  getMetrics() {
    return { ...this._metrics };
  },

  report() {
    const report = {
      metrics: this.getMetrics(),
      budgets: this._budgets,
      userAgent: navigator.userAgent,
      connection: navigator.connection ? {
        effectiveType: navigator.connection.effectiveType,
        downlink: navigator.connection.downlink,
      } : null,
      timestamp: Date.now(),
    };
    return report;
  },

  destroy() {
    this._observers.forEach(obs => obs.disconnect());
    this._observers = [];
  },

  _listeners = new Map(),

  on(event, callback) {
    if (!this._listeners.has(event)) this._listeners.set(event, []);
    this._listeners.get(event).push(callback);
    return () => {
      const cbs = this._listeners.get(event) || [];
      const idx = cbs.indexOf(callback);
      if (idx >= 0) cbs.splice(idx, 1);
    };
  },

  _emit(event, data) {
    this._listeners.get(event)?.forEach(cb => {
      try { cb(data); } catch {}
    });
  },
};

window.Performance = Performance;
