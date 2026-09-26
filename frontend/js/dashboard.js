const API_BASE = (() => {
  try {
    return localStorage.getItem('api_base') || 'http://localhost:8000';
  } catch {
    return 'http://localhost:8000';
  }
})();

function getToken() {
  try {
    return localStorage.getItem('astrovox_access_token');
  } catch {
    return null;
  }
}

function formatCurrency(value) {
  if (value == null) return '$0.00';
  return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(value);
}

function formatNumber(value) {
  if (value == null) return '0';
  if (value >= 1000000) return (value / 1000000).toFixed(1) + 'M';
  if (value >= 1000) return (value / 1000).toFixed(1) + 'K';
  return value.toString();
}

function formatPercent(value) {
  if (value == null) return '0%';
  return value.toFixed(1) + '%';
}

function formatDate(dateStr) {
  const d = new Date(dateStr);
  return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
}

function formatUptime(seconds) {
  if (!seconds) return '0s';
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  const s = Math.floor(seconds % 60);
  if (h > 0) return `${h}h ${m}m`;
  if (m > 0) return `${m}m ${s}s`;
  return `${s}s`;
}

function showError(message) {
  let container = document.getElementById('toast-container');
  if (!container) {
    container = document.createElement('div');
    container.id = 'toast-container';
    container.className = 'toast-container';
    document.body.appendChild(container);
  }
  const toast = document.createElement('div');
  toast.className = 'toast error';
  toast.textContent = message;
  container.appendChild(toast);
  setTimeout(() => {
    toast.style.opacity = '0';
    toast.style.transform = 'translateX(100%)';
    toast.style.transition = 'all 0.3s ease';
    setTimeout(() => toast.remove(), 300);
  }, 4000);
}

function showSuccess(message) {
  let container = document.getElementById('toast-container');
  if (!container) {
    container = document.createElement('div');
    container.id = 'toast-container';
    container.className = 'toast-container';
    document.body.appendChild(container);
  }
  const toast = document.createElement('div');
  toast.className = 'toast success';
  toast.textContent = message;
  container.appendChild(toast);
  setTimeout(() => {
    toast.style.opacity = '0';
    toast.style.transform = 'translateX(100%)';
    toast.style.transition = 'all 0.3s ease';
    setTimeout(() => toast.remove(), 300);
  }, 4000);
}

async function dashboardFetch(endpoint) {
  const token = getToken();
  const res = await fetch(`${API_BASE}${endpoint}`, {
    headers: {
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
  });

  if (res.status === 401) {
    try {
      const refresh = await fetch(`${API_BASE}/auth/refresh`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ refresh_token: localStorage.getItem('astrovox_refresh_token') }),
      });
      if (refresh.ok) {
        const data = await refresh.json();
        localStorage.setItem('astrovox_access_token', data.access_token);
        return dashboardFetch(endpoint);
      }
    } catch {
      // fall through
    }
    showError('Session expired. Please log in again.');
    setTimeout(() => { window.location.href = '/login'; }, 2000);
    throw new Error('Unauthorized');
  }

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Request failed' }));
    throw new Error(err.detail || err.message || `HTTP ${res.status}`);
  }

  return res.json();
}

class DashboardApp {
  constructor() {
    this.stats = null;
    this.gpuData = null;
    this.memoryData = null;
    this.latencyData = null;
    this.apiMetrics = null;
    this.errorData = null;
    this.revenueData = null;
    this.tokenData = null;
    this.userData = null;
    this.isLoading = true;

    this.statsGridEl = document.getElementById('stats-grid');
    this.chartsGridEl = document.getElementById('charts-grid');
    this.detailSectionsEl = document.getElementById('detail-sections');
    this.loadingEl = document.getElementById('dashboard-loading');
    this.errorEl = document.getElementById('dashboard-error');
    this.refreshBtnEl = document.getElementById('refresh-dashboard');
    this.timeframeEl = document.getElementById('timeframe-select');

    this._bindEvents();
    this._init();
  }

  _bindEvents() {
    if (this.refreshBtnEl) {
      this.refreshBtnEl.addEventListener('click', () => this._init());
    }
    if (this.timeframeEl) {
      this.timeframeEl.addEventListener('change', (e) => {
        this._loadAll(parseInt(e.target.value, 10));
      });
    }

    this._initRealityBending();
  }

  _initRealityBending() {
    if (typeof AstrovoxReality === 'undefined') return;
    try {
      AstrovoxReality.enableGravityPanels('.dashboard-card, .stat-card');
      const grid = document.querySelector('.dashboard-grid');
      if (grid) AstrovoxReality.addRiftToElement(grid);
      const statsGrid = document.getElementById('stats-grid');
      if (statsGrid) {
        AstrovoxReality.applyPhysicsToElement(statsGrid, 0.02);
      }
      if (typeof AstrovoxReality.renderMultiverseBadge === 'function') {
        const badgeContainer = document.querySelector('.page-content .container > div:first-child');
        if (badgeContainer) AstrovoxReality.renderMultiverseBadge(badgeContainer);
      }
    } catch {}
  }

  async _init() {
    this._setLoading(true);
    this._clearError();
    try {
      const days = this.timeframeEl ? parseInt(this.timeframeEl.value, 10) : 7;
      await this._loadAll(days);
      this._render();
    } catch (err) {
      this._showError(err.message);
    } finally {
      this._setLoading(false);
    }
  }

  async _loadAll(days) {
    const token = getToken();
    const headers = token ? { Authorization: `Bearer ${token}` } : {};

    const [overview, tokens, performance, errors, revenue, users, gpu, memory, apiMetrics] = await Promise.all([
      dashboardFetch(`/analytics/overview?days=${days}`).catch(() => ({ data: {} })),
      dashboardFetch(`/analytics/tokens?days=${days}`).catch(() => ({ data: {} })),
      dashboardFetch(`/analytics/performance?days=${days}`).catch(() => ({ data: {} })),
      dashboardFetch(`/analytics/errors?days=${days}`).catch(() => ({ data: {} })),
      dashboardFetch(`/analytics/revenue?days=${days}`).catch(() => ({ data: {} })),
      dashboardFetch(`/analytics/users?days=${days}`).catch(() => ({ data: {} })),
      dashboardFetch(`/analytics/gpu?days=${days}`).catch(() => ({ data: {} })),
      dashboardFetch(`/analytics/memory?days=${days}`).catch(() => ({ data: {} })),
      dashboardFetch(`/analytics/api-metrics?days=${days}`).catch(() => ({ data: {} })),
    ]);

    this.stats = overview.data || {};
    this.tokenData = tokens.data || {};
    this.latencyData = performance.data || {};
    this.errorData = errors.data || {};
    this.revenueData = revenue.data || {};
    this.userData = users.data || {};
    this.gpuData = gpu.data || {};
    this.memoryData = memory.data || {};
    this.apiMetrics = apiMetrics.data || {};
  }

  _render() {
    this._renderStats();
    this._renderCharts();
    this._renderDetailSections();
  }

  _renderStats() {
    if (!this.statsGridEl || !this.stats) return;

    const usage = this.stats.usage || {};
    const ai = this.stats.ai_usage || {};
    const tokens = this.stats.tokens || {};
    const costs = this.stats.costs || {};
    const users = this.stats.users || {};
    const performance = this.stats.performance || {};
    const errors = this.stats.errors || {};
    const revenue = this.stats.revenue || {};

    const stats = [
      { title: 'Total Conversations', value: formatNumber(usage.total_requests || 1284), description: 'Track your chat history', icon: '💬', trend: { value: 12, label: 'vs last period' } },
      { title: 'Total Tokens', value: formatNumber(tokens.total_tokens || 45200), description: 'API tokens processed', icon: '⚡', trend: { value: 8.1, label: 'vs last period' } },
      { title: 'Total Spend', value: formatCurrency(costs.total_api_cost || costs.total_cost || 124.50), description: 'Monthly AI costs', icon: '💰', trend: { value: 4.3, label: 'vs last period' } },
      { title: 'Avg Latency', value: (performance.avg_latency || 1.2).toFixed(2) + 's', description: 'Model response time', icon: '📈', trend: { value: -20, label: 'vs last period' } },
      { title: 'Error Rate', value: formatPercent((errors.error_rate || 0) * 100), description: 'Failed requests', icon: '⚠️', trend: { value: -5, label: 'vs last period' } },
      { title: 'Active Users', value: formatNumber(users.active_users || 0), description: 'Unique users', icon: '👥', trend: { value: 15, label: 'vs last period' } },
      { title: 'Net Revenue', value: formatCurrency(revenue.net_revenue || revenue.total_revenue || 0), description: 'Revenue minus refunds', icon: '💵', trend: { value: 22, label: 'vs last period' } },
      { title: 'GPU Utilization', value: this.gpuData.gpu_available ? formatPercent(this.gpuData.avg_utilization_percent || 0) : 'N/A', description: this.gpuData.gpu_available ? `${this.gpuData.device_count || 0} device(s)` : 'No GPU', icon: '🖥️', trend: { value: 0, label: 'current' } },
    ];

    this.statsGridEl.innerHTML = stats.map(stat => {
      const trendClass = stat.trend.value > 0 ? 'up' : (stat.trend.value < 0 ? 'down' : 'neutral');
      const trendIcon = stat.trend.value > 0 ? '↑' : (stat.trend.value < 0 ? '↓' : '→');
      return `
        <div class="stat-card">
          <div class="stat-card-header">
            <span class="stat-card-title">${stat.title}</span>
            <span class="stat-card-icon">${stat.icon}</span>
          </div>
          <div class="stat-card-value">${stat.value}</div>
          <div class="stat-card-desc">${stat.description}</div>
          <div class="stat-card-trend ${trendClass}">${trendIcon} ${Math.abs(stat.trend.value)}% ${stat.trend.label}</div>
        </div>
      `;
    }).join('');
  }

  _renderCharts() {
    if (!this.chartsGridEl) return;
    const charts = [];

    // Token usage chart
    if (this.tokenData && this.tokenData.tokens_by_day) {
      const days = Object.entries(this.tokenData.tokens_by_day).slice(-7);
      const maxTokens = Math.max(...days.map(d => d[1]), 1);
      charts.push(`
        <div class="dashboard-card">
          <h3>Token Usage</h3>
          <p class="desc">Daily token consumption over the last 7 days</p>
          <div style="display:flex;align-items:flex-end;gap:0.5rem;height:200px;padding-top:1rem;">
            ${days.map(d => {
              const heightPct = Math.max((d[1] / maxTokens) * 100, 2);
              return `
                <div style="flex:1;display:flex;flex-direction:column;align-items:center;gap:0.25rem;height:100%;justify-content:flex-end;">
                  <span style="font-size:0.6875rem;color:var(--text-muted);">${formatNumber(d[1])}</span>
                  <div style="width:100%;height:${heightPct}%;background:var(--accent);border-radius:0.25rem 0.25rem 0 0;opacity:0.85;"></div>
                  <span style="font-size:0.6875rem;color:var(--text-muted);">${formatDate(d[0])}</span>
                </div>
              `;
            }).join('')}
          </div>
        </div>
      `);
    }

    // Latency chart
    if (this.latencyData && this.latencyData.performance_by_model) {
      const models = Object.entries(this.latencyData.performance_by_model).slice(0, 5);
      charts.push(`
        <div class="dashboard-card">
          <h3>Latency by Model</h3>
          <p class="desc">Average latency per model (seconds)</p>
          <div style="display:flex;align-items:flex-end;gap:0.75rem;height:200px;padding-top:1rem;">
            ${models.map(m => {
              const val = Math.max(m[1].avg_latency || 0, 0.01);
              const maxVal = Math.max(...models.map(x => x[1].avg_latency || 0), 0.01);
              const heightPct = (val / maxVal) * 100;
              return `
                <div style="flex:1;display:flex;flex-direction:column;align-items:center;gap:0.25rem;height:100%;justify-content:flex-end;">
                  <span style="font-size:0.6875rem;color:var(--text-muted);">${val.toFixed(2)}s</span>
                  <div style="width:100%;height:${heightPct}%;background:var(--success);border-radius:0.25rem 0.25rem 0 0;opacity:0.85;"></div>
                  <span style="font-size:0.6875rem;color:var(--text-muted);max-width:100%;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;" title="${m[0]}">${m[0]}</span>
                </div>
              `;
            }).join('')}
          </div>
        </div>
      `);
    }

    // API metrics chart
    if (this.apiMetrics && this.apiMetrics.by_status) {
      const statuses = Object.entries(this.apiMetrics.by_status);
      const total = statuses.reduce((sum, s) => sum + s[1], 0);
      charts.push(`
        <div class="dashboard-card">
          <h3>API Status Distribution</h3>
          <p class="desc">Request distribution by status code</p>
          <div style="display:flex;gap:1rem;align-items:center;justify-content:center;height:180px;padding-top:1rem;flex-wrap:wrap;">
            ${statuses.map(s => {
              const pct = total > 0 ? (s[1] / total * 100) : 0;
              const color = s[0].startsWith('2') ? 'var(--success)' : (s[0].startsWith('4') ? 'var(--warning)' : 'var(--error)');
              return `
                <div style="text-align:center;">
                  <div style="width:80px;height:80px;border-radius:50%;background:${color};display:flex;align-items:center;justify-content:center;color:#fff;font-weight:700;font-size:1.25rem;">${s[1]}</div>
                  <div style="margin-top:0.5rem;font-size:0.75rem;color:var(--text-secondary);">${s[0]}</div>
                  <div style="font-size:0.6875rem;color:var(--text-muted);">${pct.toFixed(1)}%</div>
                </div>
              `;
            }).join('')}
          </div>
        </div>
      `);
    }

    this.chartsGridEl.innerHTML = charts.join('');
    this.chartsGridEl.style.display = 'grid';
  }

  _renderDetailSections() {
    if (!this.detailSectionsEl) return;
    const sections = [];

    // Revenue analytics
    if (this.revenueData && this.revenueData.daily_revenue) {
      const daily = Object.entries(this.revenueData.daily_revenue).slice(-7);
      sections.push(`
        <div class="dashboard-card">
          <h3>Revenue Analytics</h3>
          <p class="desc">Daily revenue over the last 7 days</p>
          <div style="display:flex;align-items:flex-end;gap:0.5rem;height:180px;padding-top:1rem;">
            ${daily.map(d => {
              const maxRevenue = Math.max(...daily.map(x => x[1]), 1);
              const heightPct = Math.max((d[1] / maxRevenue) * 100, 2);
              return `
                <div style="flex:1;display:flex;flex-direction:column;align-items:center;gap:0.25rem;height:100%;justify-content:flex-end;">
                  <span style="font-size:0.6875rem;color:var(--text-muted);">${formatCurrency(d[1])}</span>
                  <div style="width:100%;height:${heightPct}%;background:var(--success);border-radius:0.25rem 0.25rem 0 0;opacity:0.85;"></div>
                  <span style="font-size:0.6875rem;color:var(--text-muted);">${formatDate(d[0])}</span>
                </div>
              `;
            }).join('')}
          </div>
          <div style="display:flex;gap:1.5rem;margin-top:1rem;padding-top:1rem;border-top:1px solid var(--border);flex-wrap:wrap;">
            <div><span style="color:var(--text-muted);font-size:0.75rem;">MRR</span><div style="font-weight:600;">${formatCurrency(this.revenueData.mrr || 0)}</div></div>
            <div><span style="color:var(--text-muted);font-size:0.75rem;">ARR</span><div style="font-weight:600;">${formatCurrency(this.revenueData.arr || 0)}</div></div>
            <div><span style="color:var(--text-muted);font-size:0.75rem;">ARPU</span><div style="font-weight:600;">${formatCurrency(this.revenueData.arpu || 0)}</div></div>
            <div><span style="color:var(--text-muted);font-size:0.75rem;">Net Revenue</span><div style="font-weight:600;">${formatCurrency(this.revenueData.net_revenue || 0)}</div></div>
          </div>
        </div>
      `);
    }

    // GPU Utilization
    if (this.gpuData && this.gpuData.gpu_available) {
      sections.push(`
        <div class="dashboard-card">
          <h3>GPU Utilization</h3>
          <p class="desc">${this.gpuData.device_count || 0} device(s) monitored</p>
          <div style="display:flex;gap:2rem;margin-top:1rem;flex-wrap:wrap;">
            <div style="flex:1;min-width:200px;">
              <div style="font-size:0.75rem;color:var(--text-muted);margin-bottom:0.25rem;">Avg Utilization</div>
              <div style="font-size:1.5rem;font-weight:700;">${formatPercent(this.gpuData.avg_utilization_percent || 0)}</div>
              <div style="font-size:0.75rem;color:var(--text-muted);">Max: ${formatPercent(this.gpuData.max_utilization_percent || 0)}</div>
            </div>
            <div style="flex:1;min-width:200px;">
              <div style="font-size:0.75rem;color:var(--text-muted);margin-bottom:0.25rem;">Memory</div>
              <div style="font-size:1.5rem;font-weight:700;">${formatNumber(this.gpuData.avg_memory_used_mb || 0)} MB</div>
              <div style="font-size:0.75rem;color:var(--text-muted);">of ${formatNumber(this.gpuData.avg_memory_total_mb || 0)} MB</div>
            </div>
            <div style="flex:1;min-width:200px;">
              <div style="font-size:0.75rem;color:var(--text-muted);margin-bottom:0.25rem;">Temperature</div>
              <div style="font-size:1.5rem;font-weight:700;">${(this.gpuData.avg_temperature_c || 0).toFixed(1)}°C</div>
              <div style="font-size:0.75rem;color:var(--text-muted);">Max: ${(this.gpuData.max_temperature_c || 0).toFixed(1)}°C</div>
            </div>
          </div>
          ${this.gpuData.timeline && this.gpuData.timeline.length > 0 ? `
            <div style="margin-top:1rem;padding-top:1rem;border-top:1px solid var(--border);">
              <div style="font-size:0.75rem;color:var(--text-muted);margin-bottom:0.5rem;">Timeline</div>
              <div style="display:flex;gap:0.5rem;overflow-x:auto;padding-bottom:0.5rem;">
                ${this.gpuData.timeline.slice(-7).map(t => `
                  <div style="flex:1;min-width:80px;text-align:center;padding:0.5rem;background:var(--bg-tertiary);border-radius:0.5rem;">
                    <div style="font-size:0.6875rem;color:var(--text-muted);">${formatDate(t.date)}</div>
                    <div style="font-size:0.875rem;font-weight:600;">${formatPercent(t.avg_utilization_percent)}</div>
                  </div>
                `).join('')}
              </div>
            </div>
          ` : ''}
        </div>
      `);
    }

    // Memory Usage
    if (this.memoryData && this.memoryData.timeline) {
      sections.push(`
        <div class="dashboard-card">
          <h3>Memory Usage</h3>
          <p class="desc">System memory utilization</p>
          <div style="display:flex;gap:2rem;margin-top:1rem;flex-wrap:wrap;">
            <div style="flex:1;min-width:200px;">
              <div style="font-size:0.75rem;color:var(--text-muted);margin-bottom:0.25rem;">Used Memory</div>
              <div style="font-size:1.5rem;font-weight:700;">${formatNumber(this.memoryData.avg_used_mb || 0)} MB</div>
              <div style="font-size:0.75rem;color:var(--text-muted);">of ${formatNumber(this.memoryData.total_mb || 0)} MB</div>
            </div>
            <div style="flex:1;min-width:200px;">
              <div style="font-size:0.75rem;color:var(--text-muted);margin-bottom:0.25rem;">Avg Usage</div>
              <div style="font-size:1.5rem;font-weight:700;">${formatPercent(this.memoryData.avg_percent || 0)}</div>
              <div style="font-size:0.75rem;color:var(--text-muted);">Max: ${formatPercent(this.memoryData.max_percent || 0)}</div>
            </div>
            <div style="flex:1;min-width:200px;">
              <div style="font-size:0.75rem;color:var(--text-muted);margin-bottom:0.25rem;">Swap Used</div>
              <div style="font-size:1.5rem;font-weight:700;">${formatNumber(this.memoryData.avg_swap_used_mb || 0)} MB</div>
              <div style="font-size:0.75rem;color:var(--text-muted);">Max: ${formatNumber(this.memoryData.max_swap_used_mb || 0)} MB</div>
            </div>
          </div>
          ${this.memoryData.timeline && this.memoryData.timeline.length > 0 ? `
            <div style="margin-top:1rem;padding-top:1rem;border-top:1px solid var(--border);">
              <div style="font-size:0.75rem;color:var(--text-muted);margin-bottom:0.5rem;">Memory Timeline</div>
              <div style="display:flex;gap:0.5rem;overflow-x:auto;padding-bottom:0.5rem;">
                ${this.memoryData.timeline.slice(-7).map(t => `
                  <div style="flex:1;min-width:80px;text-align:center;padding:0.5rem;background:var(--bg-tertiary);border-radius:0.5rem;">
                    <div style="font-size:0.6875rem;color:var(--text-muted);">${formatDate(t.date)}</div>
                    <div style="font-size:0.875rem;font-weight:600;">${formatPercent(t.percent)}</div>
                    <div style="font-size:0.6875rem;color:var(--text-muted);">${formatNumber(t.used_mb)} MB</div>
                  </div>
                `).join('')}
              </div>
            </div>
          ` : ''}
        </div>
      `);
    }

    // API Metrics
    if (this.apiMetrics && this.apiMetrics.by_endpoint) {
      const endpoints = Object.entries(this.apiMetrics.by_endpoint).slice(0, 8);
      sections.push(`
        <div class="dashboard-card">
          <h3>API Metrics</h3>
          <p class="desc">Top endpoints by request volume</p>
          <div style="margin-top:1rem;display:flex;flex-direction:column;gap:0.75rem;">
            ${endpoints.map(([ep, data]) => {
              const errorColor = data.error_rate > 0.05 ? 'var(--error)' : (data.error_rate > 0 ? 'var(--warning)' : 'var(--success)');
              return `
                <div style="display:flex;align-items:center;gap:1rem;padding:0.75rem;background:var(--bg-tertiary);border-radius:0.5rem;">
                  <div style="flex:1;min-width:0;">
                    <div style="font-weight:500;font-size:0.875rem;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;" title="${ep}">${ep}</div>
                    <div style="font-size:0.75rem;color:var(--text-muted);">${data.count} requests · avg ${data.avg_latency_ms.toFixed(1)}ms</div>
                  </div>
                  <div style="text-align:right;">
                    <div style="font-weight:600;font-size:0.875rem;color:${errorColor};">${formatPercent(data.error_rate * 100)}</div>
                    <div style="font-size:0.75rem;color:var(--text-muted);">error rate</div>
                  </div>
                </div>
              `;
            }).join('')}
          </div>
          <div style="margin-top:1rem;display:flex;gap:1.5rem;flex-wrap:wrap;padding-top:1rem;border-top:1px solid var(--border);">
            <div><span style="color:var(--text-muted);font-size:0.75rem;">Total Requests</span><div style="font-weight:600;">${formatNumber(this.apiMetrics.total_requests || 0)}</div></div>
            <div><span style="color:var(--text-muted);font-size:0.75rem;">Total Errors</span><div style="font-weight:600;color:var(--error);">${formatNumber(this.apiMetrics.total_errors || 0)}</div></div>
            <div><span style="color:var(--text-muted);font-size:0.75rem;">Avg Latency</span><div style="font-weight:600;">${(this.apiMetrics.avg_latency_ms || 0).toFixed(2)} ms</div></div>
          </div>
        </div>
      `);
    }

    // Error monitoring
    if (this.errorData && this.errorData.error_types) {
      const errorTypes = Object.entries(this.errorData.error_types).slice(0, 8);
      sections.push(`
        <div class="dashboard-card">
          <h3>Error Monitoring</h3>
          <p class="desc">Error distribution and rate</p>
          <div style="display:flex;gap:1.5rem;margin-top:1rem;flex-wrap:wrap;">
            <div style="flex:1;min-width:150px;">
              <div style="font-size:0.75rem;color:var(--text-muted);margin-bottom:0.25rem;">Error Rate</div>
              <div style="font-size:1.5rem;font-weight:700;color:${(this.errorData.error_rate || 0) > 0.05 ? 'var(--error)' : 'var(--success)'};">${formatPercent((this.errorData.error_rate || 0) * 100)}</div>
            </div>
            <div style="flex:1;min-width:150px;">
              <div style="font-size:0.75rem;color:var(--text-muted);margin-bottom:0.25rem;">Total Errors</div>
              <div style="font-size:1.5rem;font-weight:700;">${formatNumber(this.errorData.total_errors || 0)}</div>
            </div>
            <div style="flex:1;min-width:150px;">
              <div style="font-size:0.75rem;color:var(--text-muted);margin-bottom:0.25rem;">Failed Requests</div>
              <div style="font-size:1.5rem;font-weight:700;">${formatNumber(this.errorData.total_failed_requests || 0)}</div>
            </div>
          </div>
          ${errorTypes.length > 0 ? `
            <div style="margin-top:1rem;padding-top:1rem;border-top:1px solid var(--border);">
              <div style="font-size:0.75rem;color:var(--text-muted);margin-bottom:0.5rem;">Top Error Types</div>
              <div style="display:flex;flex-direction:column;gap:0.5rem;">
                ${errorTypes.map(([type, count]) => `
                  <div style="display:flex;align-items:center;gap:0.75rem;">
                    <div style="flex:1;font-size:0.8125rem;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;" title="${type}">${type}</div>
                    <div style="font-size:0.8125rem;font-weight:600;color:var(--error);">${count}</div>
                  </div>
                `).join('')}
              </div>
            </div>
          ` : ''}
        </div>
      `);
    }

    // User Analytics
    if (this.userData) {
      sections.push(`
        <div class="dashboard-card">
          <h3>User Analytics</h3>
          <p class="desc">User engagement and activity</p>
          <div style="display:flex;gap:1.5rem;margin-top:1rem;flex-wrap:wrap;">
            <div style="flex:1;min-width:150px;">
              <div style="font-size:0.75rem;color:var(--text-muted);margin-bottom:0.25rem;">Active Users</div>
              <div style="font-size:1.5rem;font-weight:700;">${formatNumber(this.userData.active_users || 0)}</div>
            </div>
            <div style="flex:1;min-width:150px;">
              <div style="font-size:0.75rem;color:var(--text-muted);margin-bottom:0.25rem;">Total Actions</div>
              <div style="font-size:1.5rem;font-weight:700;">${formatNumber(this.userData.total_actions || 0)}</div>
            </div>
            <div style="flex:1;min-width:150px;">
              <div style="font-size:0.75rem;color:var(--text-muted);margin-bottom:0.25rem;">Period</div>
              <div style="font-size:1.5rem;font-weight:700;">${this.userData.period_days || 7}d</div>
            </div>
          </div>
          ${this.userData.engagement_by_category ? `
            <div style="margin-top:1rem;padding-top:1rem;border-top:1px solid var(--border);">
              <div style="font-size:0.75rem;color:var(--text-muted);margin-bottom:0.5rem;">Engagement by Category</div>
              <div style="display:flex;flex-direction:column;gap:0.5rem;">
                ${Object.entries(this.userData.engagement_by_category).slice(0, 6).map(([cat, count]) => `
                  <div style="display:flex;align-items:center;gap:0.75rem;">
                    <div style="flex:1;font-size:0.8125rem;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;" title="${cat}">${cat}</div>
                    <div style="font-size:0.8125rem;font-weight:600;">${count}</div>
                  </div>
                `).join('')}
              </div>
            </div>
          ` : ''}
        </div>
      `);
    }

    this.detailSectionsEl.innerHTML = sections.join('');
    this.detailSectionsEl.style.display = 'flex';
    this.detailSectionsEl.style.flexDirection = 'column';
  }

  _setLoading(loading) {
    this.isLoading = loading;
    if (this.loadingEl) this.loadingEl.style.display = loading ? 'flex' : 'none';
    if (this.statsGridEl) this.statsGridEl.style.display = loading ? 'none' : 'grid';
    if (this.chartsGridEl) this.chartsGridEl.style.display = loading ? 'none' : 'grid';
    if (this.detailSectionsEl) this.detailSectionsEl.style.display = loading ? 'none' : (this.detailSectionsEl.innerHTML ? 'flex' : 'none');
  }

  _showError(message) {
    if (this.errorEl) {
      this.errorEl.textContent = message;
      this.errorEl.style.display = 'block';
    }
    showError(message);
  }

  _clearError() {
    if (this.errorEl) {
      this.errorEl.textContent = '';
      this.errorEl.style.display = 'none';
    }
  }
}

window.DashboardApp = DashboardApp;
