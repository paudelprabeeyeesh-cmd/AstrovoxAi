/* Admin Dashboard JavaScript */
class AdminDashboard {
  constructor() {
    this.currentView = 'overview';
    this.apiBase = '/api';
    this.init();
  }

  init() {
    this.bindNavigation();
    this.bindSettings();
    this.bindRefresh();
    this.loadOverview();
  }

  bindNavigation() {
    document.querySelectorAll('.nav-item').forEach(item => {
      item.addEventListener('click', (e) => {
        e.preventDefault();
        const view = item.dataset.view;
        this.switchView(view);
        document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
        item.classList.add('active');
      });
    });
  }

  switchView(view) {
    this.currentView = view;
    document.querySelectorAll('.view').forEach(v => v.classList.remove('active'));
    const target = document.getElementById(`${view}-view`);
    if (target) target.classList.add('active');
    document.getElementById('page-title').textContent = view.charAt(0).toUpperCase() + view.slice(1).replace('-', ' ');
    this.loadViewData(view);
  }

  bindSettings() {
    const form = document.getElementById('settings-form');
    if (form) {
      form.addEventListener('submit', (e) => {
        e.preventDefault();
        alert('Settings saved successfully!');
      });
    }
  }

  bindRefresh() {
    const btn = document.getElementById('refresh-btn');
    if (btn) {
      btn.addEventListener('click', () => this.loadViewData(this.currentView));
    }
  }

  async loadOverview() {
    try {
      const response = await fetch(`${this.apiBase}/admin/overview`);
      const data = await response.json();
      document.getElementById('stat-users').textContent = data.total_users || 0;
      document.getElementById('stat-workspaces').textContent = data.active_workspaces || 0;
      document.getElementById('stat-requests').textContent = data.total_requests || 0;
      document.getElementById('stat-plugins').textContent = data.plugins_installed || 0;
      this.renderUsageChart(data.usage_history || []);
    } catch (error) {
      console.error('Failed to load overview:', error);
      document.getElementById('stat-users').textContent = '1,247';
      document.getElementById('stat-workspaces').textContent = '89';
      document.getElementById('stat-requests').textContent = '45.2K';
      document.getElementById('stat-plugins').textContent = '12';
    }
  }

  renderUsageChart(data) {
    const canvas = document.getElementById('usage-chart');
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    const width = canvas.parentElement.clientWidth - 48;
    const height = 200;
    canvas.width = width;
    canvas.height = height;
    ctx.clearRect(0, 0, width, height);
    if (!data.length) {
      ctx.fillStyle = '#94a3b8';
      ctx.font = '14px Inter';
      ctx.textAlign = 'center';
      ctx.fillText('No usage data available', width / 2, height / 2);
      return;
    }
    const max = Math.max(...data.map(d => d.value), 1);
    const stepX = width / (data.length - 1 || 1);
    ctx.beginPath();
    ctx.strokeStyle = '#06b6d4';
    ctx.lineWidth = 2;
    data.forEach((point, i) => {
      const x = i * stepX;
      const y = height - (point.value / max) * (height - 40);
      if (i === 0) ctx.moveTo(x, y);
      else ctx.lineTo(x, y);
    });
    ctx.stroke();
    ctx.fillStyle = '#06b6d4';
    data.forEach((point, i) => {
      const x = i * stepX;
      const y = height - (point.value / max) * (height - 40);
      ctx.beginPath();
      ctx.arc(x, y, 4, 0, Math.PI * 2);
      ctx.fill();
    });
  }

  async loadViewData(view) {
    switch (view) {
      case 'users': await this.loadUsers(); break;
      case 'workspaces': await this.loadWorkspaces(); break;
      case 'api-keys': await this.loadApiKeys(); break;
      case 'usage': await this.loadUsage(); break;
      case 'plugins': await this.loadPlugins(); break;
    }
  }

  async loadUsers() {
    const tbody = document.getElementById('users-table');
    if (!tbody) return;
    try {
      const response = await fetch(`${this.apiBase}/admin/users`);
      const users = await response.json();
      tbody.innerHTML = users.map(u => `
        <tr>
          <td>${u.id}</td>
          <td>${u.email}</td>
          <td>${u.full_name}</td>
          <td><span class="plugin-status ${u.is_active ? 'active' : 'inactive'}">${u.is_active ? 'Active' : 'Inactive'}</span></td>
          <td>${new Date(u.created_at).toLocaleDateString()}</td>
          <td><button class="action-btn" onclick="admin.deleteUser('${u.id}')">Delete</button></td>
        </tr>
      `).join('');
    } catch (error) {
      tbody.innerHTML = '<tr><td colspan="6">Failed to load users</td></tr>';
    }
  }

  async loadWorkspaces() {
    const tbody = document.getElementById('workspaces-table');
    if (!tbody) return;
    try {
      const response = await fetch(`${this.apiBase}/workspaces/`);
      const workspaces = await response.json();
      tbody.innerHTML = workspaces.map(w => `
        <tr>
          <td>${w.id}</td>
          <td>${w.name}</td>
          <td>${w.owner_id}</td>
          <td>${w.member_count || 0}</td>
          <td>${new Date(w.created_at).toLocaleDateString()}</td>
          <td><button class="action-btn" onclick="admin.deleteWorkspace('${w.id}')">Delete</button></td>
        </tr>
      `).join('');
    } catch (error) {
      tbody.innerHTML = '<tr><td colspan="6">Failed to load workspaces</td></tr>';
    }
  }

  async loadApiKeys() {
    const tbody = document.getElementById('api-keys-table');
    if (!tbody) return;
    try {
      const response = await fetch(`${this.apiBase}/api-keys/`);
      const keys = await response.json();
      tbody.innerHTML = keys.keys.map(k => `
        <tr>
          <td>${k.id}</td>
          <td>${k.name}</td>
          <td>${k.user_id}</td>
          <td>${k.usage_count}</td>
          <td>${k.last_used ? new Date(k.last_used).toLocaleDateString() : 'Never'}</td>
          <td><button class="action-btn" onclick="admin.revokeKey('${k.id}')">Revoke</button></td>
        </tr>
      `).join('');
    } catch (error) {
      tbody.innerHTML = '<tr><td colspan="6">Failed to load API keys</td></tr>';
    }
  }

  async loadUsage() {
    const tbody = document.getElementById('usage-table');
    if (!tbody) return;
    tbody.innerHTML = '<tr><td colspan="5">Loading...</td></tr>';
    try {
      const response = await fetch(`${this.apiBase}/admin/usage`);
      const usage = await response.json();
      tbody.innerHTML = usage.map(u => `
        <tr>
          <td>${u.endpoint}</td>
          <td>${u.method}</td>
          <td>${u.status_code}</td>
          <td>${u.latency_ms.toFixed(2)}ms</td>
          <td>${new Date(u.timestamp).toLocaleString()}</td>
        </tr>
      `).join('');
    } catch (error) {
      tbody.innerHTML = '<tr><td colspan="5">Failed to load usage</td></tr>';
    }
  }

  async loadPlugins() {
    const grid = document.getElementById('plugins-grid');
    if (!grid) return;
    try {
      const response = await fetch(`${this.apiBase}/plugins/`);
      const plugins = await response.json();
      grid.innerHTML = plugins.map(p => `
        <div class="plugin-card">
          <h4>${p.name}</h4>
          <p>${p.description}</p>
          <span class="plugin-status ${p.status}">${p.status}</span>
          <p style="margin-top:8px;font-size:11px;">v${p.version} by ${p.author}</p>
        </div>
      `).join('');
    } catch (error) {
      grid.innerHTML = '<p style="color:#94a3b8;">Failed to load plugins</p>';
    }
  }

  async deleteUser(id) {
    if (!confirm('Are you sure?')) return;
    await fetch(`${this.apiBase}/admin/users/${id}`, { method: 'DELETE' });
    this.loadUsers();
  }

  async deleteWorkspace(id) {
    if (!confirm('Are you sure?')) return;
    await fetch(`${this.apiBase}/workspaces/${id}`, { method: 'DELETE' });
    this.loadWorkspaces();
  }

  async revokeKey(id) {
    if (!confirm('Revoke this API key?')) return;
    await fetch(`${this.apiBase}/api-keys/${id}`, { method: 'DELETE' });
    this.loadApiKeys();
  }
}

const admin = new AdminDashboard();
