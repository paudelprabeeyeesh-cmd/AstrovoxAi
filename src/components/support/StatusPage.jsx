import { useState, useEffect } from 'react'

const API_BASE = import.meta.env.VITE_API_URL || '/api'

export default function StatusPage() {
  const [incidents, setIncidents] = useState([])
  const [summary, setSummary] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    Promise.all([
      fetch(`${API_BASE}/cx/incidents`).then(r => r.json()),
      fetch(`${API_BASE}/cx/status`).then(r => r.json()),
    ]).then(([incidentsData, statusData]) => {
      if (incidentsData.status === 'OK') setIncidents(incidentsData.incidents || [])
      if (statusData.status === 'OK') setSummary(statusData.summary)
      setLoading(false)
    }).catch(() => setLoading(false))
  }, [])

  if (loading) return <div style={{ color: '#64748b' }}>Loading status...</div>

  const statusColor = summary?.overall === 'operational' ? '#22c55e' : '#f59e0b'
  const statusLabel = summary?.overall === 'operational' ? 'All Systems Operational' : 'Some Systems Degraded'

  return (
    <div style={{ maxWidth: '800px' }}>
      <h3 style={{ marginTop: 0, color: '#06b6d4' }}>System Status</h3>
      <div style={{ padding: '20px', backgroundColor: 'rgba(30, 41, 59, 0.5)', border: '1px solid #1e293b', borderRadius: '12px', marginBottom: '24px', display: 'flex', alignItems: 'center', gap: '12px' }}>
        <span style={{ width: '12px', height: '12px', borderRadius: '50%', backgroundColor: statusColor, boxShadow: `0 0 8px ${statusColor}` }} />
        <div>
          <div style={{ fontWeight: 700, fontSize: '16px', color: statusColor }}>{statusLabel}</div>
          <div style={{ fontSize: '12px', color: '#64748b', marginTop: '2px' }}>Updated just now</div>
        </div>
      </div>

      <h4 style={{ color: '#94a3b8', fontSize: '14px', marginBottom: '12px' }}>Incidents</h4>
      {incidents.length === 0 && <p style={{ color: '#64748b' }}>No incidents reported.</p>}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
        {incidents.map(inc => (
          <div key={inc.id} style={{ padding: '16px', backgroundColor: 'rgba(30, 41, 59, 0.5)', border: '1px solid #1e293b', borderRadius: '8px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '8px' }}>
              <div style={{ fontWeight: 600, fontSize: '14px' }}>{inc.title}</div>
              <span style={{ padding: '2px 8px', borderRadius: '4px', fontSize: '10px', backgroundColor: inc.status === 'resolved' ? 'rgba(34, 197, 94, 0.2)' : 'rgba(245, 158, 11, 0.2)', color: inc.status === 'resolved' ? '#22c55e' : '#f59e0b', textTransform: 'capitalize' }}>
                {inc.status}
              </span>
            </div>
            <p style={{ fontSize: '13px', color: '#94a3b8', lineHeight: 1.5 }}>{inc.description}</p>
            <div style={{ fontSize: '11px', color: '#64748b', marginTop: '8px' }}>
              Started: {new Date(inc.started_at).toLocaleString()}
              {inc.resolved_at && ` · Resolved: ${new Date(inc.resolved_at).toLocaleString()}`}
            </div>
            {inc.affected_services?.length > 0 && (
              <div style={{ display: 'flex', gap: '6px', marginTop: '8px', flexWrap: 'wrap' }}>
                {inc.affected_services.map(s => (
                  <span key={s} style={{ padding: '2px 8px', borderRadius: '4px', fontSize: '10px', backgroundColor: 'rgba(100, 116, 139, 0.2)', color: '#94a3b8' }}>{s}</span>
                ))}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}
