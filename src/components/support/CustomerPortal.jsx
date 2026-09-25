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

export default function CustomerPortal({ session }) {
  const [portal, setPortal] = useState(null)
  const [loading, setLoading] = useState(true)
  const headers = useAuthHeaders()

  useEffect(() => {
    fetch(`${API_BASE}/cx/portal`, { headers })
      .then(r => r.json())
      .then(d => { if (r.ok) setPortal(d.portal); setLoading(false) })
      .catch(() => setLoading(false))
  }, [headers])

  if (loading) return <div style={{ color: '#64748b' }}>Loading portal...</div>

  return (
    <div style={{ maxWidth: '800px' }}>
      <h3 style={{ marginTop: 0, color: '#06b6d4' }}>Customer Portal</h3>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '16px', marginBottom: '24px' }}>
        <div style={{ padding: '16px', backgroundColor: 'rgba(30, 41, 59, 0.5)', border: '1px solid #1e293b', borderRadius: '8px' }}>
          <div style={{ fontSize: '11px', color: '#64748b', textTransform: 'uppercase', letterSpacing: '0.5px' }}>Health Score</div>
          <div style={{ fontSize: '28px', fontWeight: 700, color: portal?.health?.score >= 70 ? '#22c55e' : portal?.health?.score >= 40 ? '#f59e0b' : '#ef4444', marginTop: '4px' }}>
            {Math.round(portal?.health?.score || 0)}
          </div>
        </div>
        <div style={{ padding: '16px', backgroundColor: 'rgba(30, 41, 59, 0.5)', border: '1px solid #1e293b', borderRadius: '8px' }}>
          <div style={{ fontSize: '11px', color: '#64748b', textTransform: 'uppercase', letterSpacing: '0.5px' }}>Open Tickets</div>
          <div style={{ fontSize: '28px', fontWeight: 700, color: '#e2e8f0', marginTop: '4px' }}>
            {portal?.tickets?.filter(t => t.status === 'open' || t.status === 'assigned').length || 0}
          </div>
        </div>
        <div style={{ padding: '16px', backgroundColor: 'rgba(30, 41, 59, 0.5)', border: '1px solid #1e293b', borderRadius: '8px' }}>
          <div style={{ fontSize: '11px', color: '#64748b', textTransform: 'uppercase', letterSpacing: '0.5px' }}>Onboarding</div>
          <div style={{ fontSize: '28px', fontWeight: 700, color: portal?.onboarding?.completed ? '#22c55e' : '#f59e0b', marginTop: '4px' }}>
            {portal?.onboarding?.completed ? 'Done' : `${portal?.onboarding?.current_step || 0}/4`}
          </div>
        </div>
      </div>

      {portal?.tickets?.length > 0 && (
        <div style={{ marginBottom: '24px' }}>
          <h4 style={{ color: '#94a3b8', fontSize: '14px', marginBottom: '12px' }}>Recent Tickets</h4>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
            {portal.tickets.slice(0, 5).map(t => (
              <div key={t.id} style={{ padding: '12px', backgroundColor: 'rgba(30, 41, 59, 0.5)', border: '1px solid #1e293b', borderRadius: '8px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div>
                  <div style={{ fontWeight: 600, fontSize: '13px' }}>{t.subject}</div>
                  <div style={{ fontSize: '11px', color: '#64748b', marginTop: '2px' }}>{t.category} · {new Date(t.created_at).toLocaleDateString()}</div>
                </div>
                <span style={{ padding: '2px 8px', borderRadius: '4px', fontSize: '10px', backgroundColor: t.status === 'open' ? 'rgba(239, 68, 68, 0.2)' : 'rgba(6, 182, 212, 0.2)', color: t.status === 'open' ? '#f87171' : '#06b6d4' }}>{t.status}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {portal?.health?.factors && Object.keys(portal.health.factors).length > 0 && (
        <div>
          <h4 style={{ color: '#94a3b8', fontSize: '14px', marginBottom: '12px' }}>Health Factors</h4>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
            {Object.entries(portal.health.factors).map(([key, val]) => (
              <div key={key} style={{ display: 'flex', justifyContent: 'space-between', padding: '8px 12px', backgroundColor: 'rgba(30, 41, 59, 0.5)', border: '1px solid #1e293b', borderRadius: '6px', fontSize: '13px' }}>
                <span style={{ color: '#94a3b8', textTransform: 'capitalize' }}>{key.replace(/_/g, ' ')}</span>
                <span style={{ color: '#e2e8f0' }}>{String(val)}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
