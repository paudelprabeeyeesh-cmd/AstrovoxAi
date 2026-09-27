// Governance dashboard interactions
document.addEventListener('DOMContentLoaded', () => {
  const policiesList = document.getElementById('policies');
  const auditLog = document.getElementById('audit-log');

  if (policiesList) {
    const policies = [
      { name: 'Data Residency', status: 'Active' },
      { name: 'Access Control', status: 'Active' },
      { name: 'Audit Retention', status: 'Active' },
    ];
    policies.forEach(p => {
      const li = document.createElement('li');
      li.textContent = `${p.name} — ${p.status}`;
      policiesList.appendChild(li);
    });
  }

  if (auditLog) {
    const logs = [
      { action: 'policy_updated', actor: 'admin', timestamp: Date.now() },
      { action: 'audit_exported', actor: 'compliance_bot', timestamp: Date.now() - 1000 },
    ];
    logs.forEach(l => {
      const li = document.createElement('li');
      li.textContent = `${l.action} by ${l.actor} at ${new Date(l.timestamp).toISOString()}`;
      auditLog.appendChild(li);
    });
  }
});
