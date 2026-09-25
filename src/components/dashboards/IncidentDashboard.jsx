import { useState, useMemo } from 'react'
import { motion } from 'framer-motion'
import Icon from '../../design/Iconography'

const SEVERITY_COLORS = {
  critical: 'var(--astrovox-error)',
  high: 'var(--astrovox-warning)',
  medium: 'var(--astrovox-primary)',
  low: 'var(--astrovox-success)'
}

export default function IncidentDashboard({ incidents, onResolve, onInvestigate }) {
  const [filter, setFilter] = useState('all')
  const [selectedIncident, setSelectedIncident] = useState(null)

  const filtered = filter === 'all' ? incidents : incidents?.filter(i => i.severity === filter) || []
  const criticalCount = incidents?.filter(i => i.severity === 'critical' && i.status === 'active').length || 0

  return (
    <div style={{ padding: '16px', display: 'flex', flexDirection: 'column', gap: '16px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <h2 style={{ margin: 0, fontSize: '18px', fontWeight: '700', color: 'var(--astrovox-text)', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Icon name="alert" size={22} style={{ color: 'var(--astrovox-error)' }} />
            Incident Dashboard
            {criticalCount > 0 && (
              <span style={{
                padding: '2px 8px',
                backgroundColor: 'var(--astrovox-error)',
                color: 'white',
                borderRadius: 'var(--astrovox-radius-sm)',
                fontSize: '11px',
                fontWeight: '700'
              }}>
                {criticalCount} Active
              </span>
            )}
          </h2>
          <p style={{ margin: '4px 0 0', fontSize: '11px', color: 'var(--astrovox-text-muted)' }}>
            Monitor and resolve system incidents
          </p>
        </div>
        <div style={{ display: 'flex', gap: '8px' }}>
          {['all', 'active', 'resolved'].map(f => (
            <button
              key={f}
              onClick={() => setFilter(f)}
              style={{
                padding: '6px 12px',
                backgroundColor: filter === f ? 'var(--astrovox-primary)' : 'var(--astrovox-surface-hover)',
                color: filter === f ? 'var(--astrovox-bg)' : 'var(--astrovox-text-muted)',
                border: `1px solid ${filter === f ? 'var(--astrovox-primary)' : 'var(--astrovox-border)'}`,
                borderRadius: 'var(--astrovox-radius-md)',
                cursor: 'pointer',
                fontSize: '12px',
                fontFamily: 'inherit',
                textTransform: 'capitalize'
              }}
            >
              {f}
            </button>
          ))}
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))', gap: '12px' }}>
        {[
          { label: 'Active', value: incidents?.filter(i => i.status === 'active').length || 0, color: 'var(--astrovox-error)' },
          { label: 'Investigating', value: incidents?.filter(i => i.status === 'investigating').length || 0, color: 'var(--astrovox-warning)' },
          { label: 'Resolved', value: incidents?.filter(i => i.status === 'resolved').length || 0, color: 'var(--astrovox-success)' },
          { label: 'MTTR', value: '4.2m', color: 'var(--astrovox-text)' }
        ].map(stat => (
          <motion.div
            key={stat.label}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            style={{
              padding: '14px',
              backgroundColor: 'var(--astrovox-surface)',
              border: '1px solid var(--astrovox-border)',
              borderRadius: 'var(--astrovox-radius-lg)'
            }}
          >
            <div style={{ fontSize: '11px', color: 'var(--astrovox-text-muted)', marginBottom: '6px', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
              {stat.label}
            </div>
            <div style={{ fontSize: '22px', fontWeight: '700', color: stat.color }}>{stat.value}</div>
          </motion.div>
        ))}
      </div>

      <div
        style={{
          backgroundColor: 'var(--astrovox-surface)',
          border: '1px solid var(--astrovox-border)',
          borderRadius: 'var(--astrovox-radius-lg)',
          overflow: 'hidden'
        }}
      >
        <div style={{ padding: '12px 16px', borderBottom: '1px solid var(--astrovox-border)' }}>
          <h3 style={{ margin: 0, fontSize: '14px', fontWeight: '600' }}>Recent Incidents</h3>
        </div>
        {filtered.length === 0 ? (
          <div style={{ padding: '32px', textAlign: 'center', color: 'var(--astrovox-text-muted)', fontSize: '13px' }}>
            No incidents found
          </div>
        ) : (
          <div style={{ maxHeight: '400px', overflowY: 'auto' }}>
            {filtered.map((incident, index) => (
              <motion.div
                key={incident.id}
                initial={{ opacity: 0, x: -10 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: index * 0.05 }}
                style={{
                  padding: '12px 16px',
                  borderBottom: '1px solid var(--astrovox-border)',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '12px',
                  cursor: 'pointer'
                }}
                onClick={() => setSelectedIncident(incident)}
              >
                <div
                  style={{
                    width: '8px',
                    height: '8px',
                    borderRadius: '50%',
                    backgroundColor: SEVERITY_COLORS[incident.severity] || SEVERITY_COLORS.medium,
                    flexShrink: 0
                  }}
                />
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ fontSize: '12px', fontWeight: '600', color: 'var(--astrovox-text)', marginBottom: '2px' }}>
                    {incident.title}
                  </div>
                  <div style={{ fontSize: '11px', color: 'var(--astrovox-text-muted)' }}>
                    {incident.service} • {new Date(incident.timestamp).toLocaleString()}
                  </div>
                </div>
                <span
                  style={{
                    padding: '2px 8px',
                    borderRadius: 'var(--astrovox-radius-sm)',
                    fontSize: '10px',
                    fontWeight: '600',
                    backgroundColor: `${SEVERITY_COLORS[incident.severity]}20`,
                    color: SEVERITY_COLORS[incident.severity],
                    border: `1px solid ${SEVERITY_COLORS[incident.severity]}`,
                    textTransform: 'uppercase'
                  }}
                >
                  {incident.severity}
                </span>
              </motion.div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
