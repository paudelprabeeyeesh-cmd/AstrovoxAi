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

export default function HealthScore() {
  const [health, setHealth] = useState(null)
  const headers = useAuthHeaders()

  useEffect(() => {
    fetch(`${API_BASE}/cx/health`, { headers })
      .then(r => r.json())
      .then(d => { if (d.status === 'OK') setHealth(d.health) })
  }, [headers])

  if (!health) return <div style={{ color: '#64748b' }}>Loading health score...</div>

  const score = health.score || 0
  const color = score >= 70 ? '#22c55e' : score >= 40 ? '#f59e0b' : '#ef4444'
  const label = score >= 70 ? 'Healthy' : score >= 40 ? 'At Risk' : 'Critical'

  return (
    <div style={{ maxWidth: '600px' }}>
      <h3 style={{ marginTop: 0, color: '#06b6d4' }}>Customer Health</h3>
      <div style={{ padding: '24px', backgroundColor: 'rgba(30, 41, 59, 0.5)', border: '1px solid #1e293b', borderRadius: '12px', textAlign: 'center', marginBottom: '24px' }}>
        <div style={{ fontSize: '64px', fontWeight: 800, color, lineHeight: 1 }}>{Math.round(score)}</div>
        <div style={{ fontSize: '14px', color, marginTop: '8px', fontWeight: 600 }}>{label}</div>
        <div style={{ fontSize: '11px', color: '#64748b', marginTop: '4px' }}>Last calculated: {new Date(health.last_calculated).toLocaleString()}</div>
      </div>

      {health.factors && Object.keys(health.factors).length > 0 && (
        <div>
          <h4 style={{ color: '#94a3b8', fontSize: '14px', marginBottom: '12px' }}>Factors</h4>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
            {Object.entries(health.factors).map(([key, val]) => (
              <div key={key} style={{ display: 'flex', justifyContent: 'space-between', padding: '12px', backgroundColor: 'rgba(30, 41, 59, 0.5)', border: '1px solid #1e293b', borderRadius: '6px' }}>
                <span style={{ color: '#94a3b8', fontSize: '13px', textTransform: 'capitalize' }}>{key.replace(/_/g, ' ')}</span>
                <span style={{ color: '#e2e8f0', fontSize: '13px', fontWeight: 600 }}>{String(val)}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
