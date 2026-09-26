document.addEventListener('DOMContentLoaded', () => {
  const tabs = document.querySelectorAll('.tab');
  const contents = document.querySelectorAll('.tab-content');

  tabs.forEach(tab => {
    tab.addEventListener('click', () => {
      tabs.forEach(t => t.classList.remove('active'));
      contents.forEach(c => c.classList.add('hidden'));
      tab.classList.add('active');
      document.getElementById(tab.dataset.tab).classList.remove('hidden');
    });
  });

  const sampleSSO = [
    { key: 'saml:Okta', type: 'saml', metadata: 'https://dev-123.okta.com/metadata', entity: 'urn:astrovox' },
    { key: 'oidc:Google', type: 'oidc', metadata: 'Google Identity', entity: 'https://accounts.google.com' },
  ];
  const sampleOrgs = [
    { id: 'org-1', name: 'Acme Corp', plan: 'enterprise', members: 12 },
    { id: 'org-2', name: 'Globex Inc', plan: 'team', members: 8 },
    { id: 'org-3', name: 'Initech', plan: 'free', members: 5 },
  ];
  const sampleInvoices = [
    { id: 'inv-1', org: 'org-1', amount: 499.0, currency: 'USD', status: 'paid', created: '2026-09-01' },
    { id: 'inv-2', org: 'org-2', amount: 99.0, currency: 'USD', status: 'pending', created: '2026-09-10' },
  ];
  const sampleSubs = [
    { id: 'sub-1', org: 'org-1', plan: 'enterprise', seats: 50, status: 'active' },
    { id: 'sub-2', org: 'org-2', plan: 'team', seats: 10, status: 'active' },
  ];
  const sampleQuotas = [
    { id: 'q-1', org: 'org-1', resource: 'api_requests', limit: 100000, period: 'monthly' },
    { id: 'q-2', org: 'org-1', resource: 'tokens', limit: 500000, period: 'monthly' },
  ];
  const sampleKeys = [
    { id: 'key-1', name: 'CI/CD Pipeline', scopes: 'read, execute', expires: '2027-01-01', created: '2026-01-15' },
    { id: 'key-2', name: 'Monitoring Bot', scopes: 'read', expires: '2026-12-31', created: '2026-03-20' },
  ];
  const samplePerms = [
    { user: 'user-1', role: 'owner', permissions: 'org:read, org:write, billing:manage, team_manage' },
    { user: 'user-2', role: 'admin', permissions: 'org:read, org:write, team_manage' },
    { user: 'user-3', role: 'member', permissions: 'org:read, workspace:read, workspace:write' },
  ];
  const sampleCompliance = [
    { timestamp: '2026-09-26T02:00:00Z', actor: 'admin', action: 'update_organization', resource: 'org:org-1', tenant: 'org-1' },
    { timestamp: '2026-09-26T01:30:00Z', actor: 'system', action: 'api_call', resource: 'POST /api/v1/chat', tenant: 'org-2' },
    { timestamp: '2026-09-26T01:00:00Z', actor: 'user-2', action: 'login', resource: 'auth', tenant: 'org-1' },
  ];

  function renderTable(tableId, rows, fields) {
    const tbody = document.querySelector(`#${tableId} tbody`);
    if (!tbody) return;
    tbody.innerHTML = rows.map(r => `<tr>${fields.map(f => `<td>${r[f] ?? ''}</td>`).join('')}</tr>`).join('');
  }

  renderTable('ssoTable', sampleSSO, ['key', 'type', 'metadata']);
  renderTable('orgTable', sampleOrgs, ['id', 'name', 'plan', 'members']);
  renderTable('invoiceTable', sampleInvoices, ['id', 'org', 'amount', 'status', 'created']);
  renderTable('subTable', sampleSubs, ['id', 'org', 'plan', 'seats', 'status']);
  renderTable('quotaTable', sampleQuotas, ['id', 'org', 'resource', 'limit', 'period']);
  renderTable('apiKeyTable', sampleKeys, ['id', 'name', 'scopes', 'expires', 'created']);
  renderTable('permTable', samplePerms, ['user', 'role', 'permissions']);
  renderTable('complianceTable', sampleCompliance, ['timestamp', 'actor', 'action', 'resource', 'tenant']);

  const orgCtx = document.getElementById('orgChart')?.getContext('2d');
  if (orgCtx) {
    new Chart(orgCtx, {
      type: 'bar',
      data: {
        labels: sampleOrgs.map(o => o.name),
        datasets: [{ label: 'Members', data: sampleOrgs.map(o => o.members), backgroundColor: '#4299e1' }]
      }
    });
  }

  const billCtx = document.getElementById('billingChart')?.getContext('2d');
  if (billCtx) {
    new Chart(billCtx, {
      type: 'line',
      data: {
        labels: ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun'],
        datasets: [{ label: 'Revenue', data: [1200, 1900, 3000, 5000, 2300, 3400], borderColor: '#38a169', fill: false }]
      }
    });
  }

  const quotaCtx = document.getElementById('quotaChart')?.getContext('2d');
  if (quotaCtx) {
    new Chart(quotaCtx, {
      type: 'doughnut',
      data: {
        labels: sampleQuotas.map(q => q.resource),
        datasets: [{ data: sampleQuotas.map(q => q.limit), backgroundColor: ['#4299e1', '#38a169', '#d69e2e'] }]
      }
    });
  }

  document.getElementById('ldapForm')?.addEventListener('submit', e => {
    e.preventDefault();
    const result = { username: document.getElementById('ldapUser').value, authenticated: true, groups: ['developers', 'astrovox-users'] };
    document.getElementById('ldapResult').textContent = JSON.stringify(result, null, 2);
  });

  document.getElementById('orgForm')?.addEventListener('submit', e => {
    e.preventDefault();
    const name = document.getElementById('orgName').value;
    const owner = document.getElementById('orgOwner').value;
    const plan = document.getElementById('orgPlan').value;
    alert(`Created org: ${name} (owner: ${owner}, plan: ${plan})`);
    sampleOrgs.push({ id: 'org-new', name, plan, members: 1 });
    renderTable('orgTable', sampleOrgs, ['id', 'name', 'plan', 'members']);
    e.target.reset();
  });

  document.getElementById('invoiceForm')?.addEventListener('submit', e => {
    e.preventDefault();
    const org = document.getElementById('invOrg').value;
    const amount = document.getElementById('invAmount').value;
    alert(`Created invoice for ${org} amount ${amount}`);
    sampleInvoices.push({ id: 'inv-new', org, amount: parseFloat(amount), currency: document.getElementById('invCurrency').value, status: 'pending', created: new Date().toISOString().split('T')[0] });
    renderTable('invoiceTable', sampleInvoices, ['id', 'org', 'amount', 'status', 'created']);
    e.target.reset();
  });

  document.getElementById('subForm')?.addEventListener('submit', e => {
    e.preventDefault();
    const org = document.getElementById('subOrg').value;
    const plan = document.getElementById('subPlan').value;
    const seats = document.getElementById('subSeats').value;
    alert(`Created subscription for ${org} plan ${plan} seats ${seats}`);
    sampleSubs.push({ id: 'sub-new', org, plan, seats: parseInt(seats, 10), status: 'active' });
    renderTable('subTable', sampleSubs, ['id', 'org', 'plan', 'seats', 'status']);
    e.target.reset();
  });

  document.getElementById('quotaForm')?.addEventListener('submit', e => {
    e.preventDefault();
    const org = document.getElementById('quotaOrg').value;
    const resource = document.getElementById('quotaResource').value;
    const limit = document.getElementById('quotaLimit').value;
    alert(`Set quota for ${org} ${resource} limit ${limit}`);
    sampleQuotas.push({ id: 'q-new', org, resource, limit: parseInt(limit, 10), period: document.getElementById('quotaPeriod').value });
    renderTable('quotaTable', sampleQuotas, ['id', 'org', 'resource', 'limit', 'period']);
    e.target.reset();
  });

  document.getElementById('keyForm')?.addEventListener('submit', e => {
    e.preventDefault();
    const org = document.getElementById('keyOrg').value;
    const name = document.getElementById('keyName').value;
    const scopes = document.getElementById('keyScopes').value;
    alert(`Created API key ${name} for ${org} scopes: ${scopes}`);
    sampleKeys.push({ id: 'key-new', name, scopes, expires: '2027-12-31', created: new Date().toISOString().split('T')[0] });
    renderTable('apiKeyTable', sampleKeys, ['id', 'name', 'scopes', 'expires', 'created']);
    e.target.reset();
  });

  document.getElementById('permForm')?.addEventListener('submit', e => {
    e.preventDefault();
    const org = document.getElementById('permOrg').value;
    const user = document.getElementById('permUser').value;
    const role = document.getElementById('permRole').value;
    alert(`Assigned role ${role} to ${user} in ${org}`);
    samplePerms.push({ user, role, permissions: 'role assigned' });
    renderTable('permTable', samplePerms, ['user', 'role', 'permissions']);
    e.target.reset();
  });

  document.getElementById('compQuery')?.addEventListener('click', () => {
    const actor = document.getElementById('compActor').value;
    const action = document.getElementById('compAction').value;
    let results = sampleCompliance;
    if (actor) results = results.filter(r => r.actor === actor);
    if (action) results = results.filter(r => r.action === action);
    renderTable('complianceTable', results, ['timestamp', 'actor', 'action', 'resource', 'tenant']);
  });

  document.getElementById('compGenerate')?.addEventListener('click', () => {
    const report = { framework: 'SOC2', period_start: '2026-09-01', period_end: '2026-09-26', audit_logs_count: sampleCompliance.length, tamper_detected: false };
    document.getElementById('complianceResult').textContent = JSON.stringify(report, null, 2);
  });
});
