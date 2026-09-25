import { useState } from 'react'

const API_BASE = import.meta.env.VITE_API_URL || '/api'

function useAuthHeaders() {
  const [headers, setHeaders] = useState({ 'Content-Type': 'application/json' })
  useState(() => {
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

export default function NpsSurvey() {
  const [score, setScore] = useState('')
  const [comment, setComment] = useState('')
  const [submitted, setSubmitted] = useState(false)
  const [stats, setStats] = useState(null)
  const headers = useAuthHeaders()

  const submit = async (e) => {
    e.preventDefault()
    await fetch(`${API_BASE}/cx/nps`, { method: 'POST', headers, body: JSON.stringify({ score: parseInt(score), comment: comment || null }) })
    setSubmitted(true)
    fetch(`${API_BASE}/cx/nps/stats`).then(r => r.json()).then(d => { if (d.status === 'OK') setStats(d.stats) })
  }

  if (submitted && !stats) return <div style={{ color: '#22c55e' }}>Thank you for your feedback!</div>

  return (
    <div style={{ maxWidth: '600px' }}>
      <h3 style={{ marginTop: 0, color: '#06b6d4' }}>Net Promoter Score</h3>
      {stats && (
        <div style={{ padding: '16px', backgroundColor: 'rgba(30, 41, 59, 0.5)', border: '1px solid #1e293b', borderRadius: '8px', marginBottom: '24px' }}>
          <div style={{ fontSize: '11px', color: '#64748b', textTransform: 'uppercase', letterSpacing: '0.5px' }}>Community NPS</div>
          <div style={{ fontSize: '32px', fontWeight: 700, color: '#e2e8f0', marginTop: '4px' }}>{stats.nps_score}</div>
          <div style={{ fontSize: '12px', color: '#64748b', marginTop: '4px' }}>Based on {stats.total_responses} responses · Avg score: {stats.average_score}</div>
        </div>
      )}
      {!submitted ? (
        <form onSubmit={submit} style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          <div>
            <label style={{ fontSize: '11px', color: '#64748b', display: 'block', marginBottom: '8px' }}>How likely are you to recommend AstrovoxAI to a friend? (0-10)</label>
            <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap' }}>
              {Array.from({ length: 11 }, (_, i) => i).map(n => (
                <button key={n} type="button" onClick={() => setScore(n)} style={{ width: '36px', height: '36px', borderRadius: '6px', border: `1px solid ${score === n ? '#06b6d4' : '#1e293b'}`, backgroundColor: score === n ? '#06b6d4' : 'transparent', color: score === n ? '#02040a' : '#94a3b8', cursor: 'pointer', fontWeight: 600, fontSize: '13px' }}>
                  {n}
                </button>
              ))}
            </div>
          </div>
          <div>
            <label style={{ fontSize: '11px', color: '#64748b', display: 'block', marginBottom: '4px' }}>Comment (optional)</label>
            <textarea value={comment} onChange={e => setComment(e.target.value)} rows={3} style={{ width: '100%', padding: '10px', backgroundColor: '#0f172a', border: '1px solid #1e293b', borderRadius: '6px', color: '#e2e8f0', fontSize: '13px', resize: 'vertical' }} />
          </div>
          <button type="submit" disabled={score === ''} style={{ padding: '10px 16px', backgroundColor: score === '' ? '#1e293b' : '#06b6d4', border: 'none', borderRadius: '6px', color: score === '' ? '#64748b' : '#02040a', fontWeight: 600, cursor: score === '' ? 'not-allowed' : 'pointer', alignSelf: 'flex-start' }}>
            Submit NPS
          </button>
        </form>
      ) : (
        <div style={{ color: '#22c55e' }}>Thank you for your feedback!</div>
      )}
    </div>
  )
}
