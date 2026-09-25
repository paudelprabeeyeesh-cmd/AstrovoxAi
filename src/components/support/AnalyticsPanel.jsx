import { useState, useEffect } from 'react'

const API_BASE = import.meta.env.VITE_API_URL || '/api'

function useAuthHeaders() {
  const [headers, setHeaders] = useState({ 'Content-Type': 'application/json' })
  useEffect(() => {
    const init = async () => {
      try {
        const { supabase } = await import('./supabase')
        const { data: { session } } = await supabase.auth.getSession()
        if (session?.access_token) setHeaders({ 'Content-Type': 'application/json', Authorization: `Bearer ${session.access_token}` })
      } catch { /* not authenticated */ }
    }
    init()
  }, [])
  return headers
}

export default function AnalyticsPanel() {
  const [analytics, setAnalytics] = useState([])
  const [stats, setStats] = useState(null)
  const headers = useAuthHeaders()

  useEffect(() => {
    fetch(`${API_BASE}/cx/analytics`, { headers })
      .then(r => r.json())
      .then(d => { if (d.status === 'OK') setAnalytics(d.analytics || []) })
    fetch(`${API_BASE}/cx/nps/stats`)
      .then(r => r.json())
      .then(d => { if (d.status === 'OK') setStats(d.stats) })
  }, [headers])

  const metricGroups = analytics.reduce((acc, a) => {
    if (!acc[a.metric_name]) acc[a.metric_name] = []
    acc[a.metric_name].push(a)
    return acc
  }, {})

  return (
    <div style={{ maxWidth: '800px' }}>
      <h3 style={{ marginTop: 0, color: '#06b6d4' }}>Support Analytics</h3>

      {stats && (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))', gap: '12px', marginBottom: '24px' }}>
          {Object.entries(stats).map(([key, val]) => (
            <div key={key} style={{ padding: '16px', backgroundColor: 'rgba(30, 41, 59, 0.5)', border: '1px solid #1e293b', borderRadius: '8px', textAlign: 'center' }}>
              <div style={{ fontSize: '11px', color: '#64748b', textTransform: 'uppercase', letterSpacing: '0.5px' }}>{key.replace(/_/g, ' ')}</div>
              <div style={{ fontSize: '24px', fontWeight: 700, color: '#e2e8f0', marginTop: '4px' }}>{typeof val === 'number' ? (Number.isInteger(val) ? val : val.toFixed(2)) : val}</div>
            </div>
          ))}
        </div>
      )}

      <h4 style={{ color: '#94a3b8', fontSize: '14px', marginBottom: '12px' }}>Metrics</h4>
      {Object.keys(metricGroups).length === 0 && <p style={{ color: '#64748b' }}>No analytics data yet.</p>}
      {Object.entries(metricGroups).map(([name, items]) => (
        <div key={name} style={{ marginBottom: '16px' }}>
          <div style={{ fontWeight: 600, fontSize: '13px', color: '#cbd5e1', marginBottom: '8px', textTransform: 'capitalize' }}>{name.replace(/_/g, ' ')}</div>
          <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
            {items.slice(0, 5).map(item => (
              <div key={item.id} style={{ padding: '8px 12px', backgroundColor: 'rgba(15, 23, 42, 0.6)', border: '1px solid #1e293b', borderRadius: '6px', fontSize: '12px' }}>
                <span style={{ color: '#64748b' }}>{item.period}: </span>
                <span style={{ color: '#e2e8f0', fontWeight: 600 }}>{item.metric_value}</span>
              </div>
            ))}
          </div>
        </div>
      ))}
    </div>
  )
}
