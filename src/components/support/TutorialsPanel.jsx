import { useState, useEffect, useCallback } from 'react'

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

export default function TutorialsPanel() {
  const [tutorials, setTutorials] = useState([])
  const [progress, setProgress] = useState([])
  const [selected, setSelected] = useState(null)
  const headers = useAuthHeaders()

  useEffect(() => {
    fetch(`${API_BASE}/cx/tutorials`, { headers })
      .then(r => r.json()).then(d => setTutorials(d.tutorials || []))
    fetch(`${API_BASE}/cx/tutorials/progress`, { headers })
      .then(r => r.json()).then(d => setProgress(d.progress || []))
  }, [headers])

  const startTutorial = async (tutorialId) => {
    await fetch(`${API_BASE}/cx/tutorials/${tutorialId}/start`, { method: 'POST', headers })
    setSelected(tutorialId)
  }

  const updateProgress = async (tutorialId, step) => {
    await fetch(`${API_BASE}/cx/tutorials/${tutorialId}/progress?current_step=${step}`, { method: 'POST', headers })
    setProgress(prev => prev.map(p => p.tutorial_id === tutorialId ? { ...p, current_step: step } : p))
  }

  if (selected) {
    const tutorial = tutorials.find(t => t.id === selected)
    const currentProgress = progress.find(p => p.tutorial_id === selected)
    if (!tutorial) return <div style={{ color: '#64748b' }}>Tutorial not found.</div>

    return (
      <div style={{ maxWidth: '700px' }}>
        <button onClick={() => setSelected(null)} style={{ marginBottom: '12px', background: 'transparent', border: '1px solid #1e293b', color: '#94a3b8', borderRadius: '6px', cursor: 'pointer', padding: '6px 12px', fontSize: '12px' }}>← Back</button>
        <h3 style={{ margin: '0 0 8px 0', color: '#06b6d4' }}>{tutorial.title}</h3>
        <p style={{ color: '#64748b', fontSize: '12px', marginBottom: '16px' }}>{tutorial.description} · {tutorial.difficulty} · {tutorial.estimated_time} min</p>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
          {tutorial.steps.map((step, idx) => {
            const isCompleted = (currentProgress?.current_step || 0) > idx
            const isCurrent = (currentProgress?.current_step || 0) === idx
            return (
              <div key={idx} style={{ padding: '16px', backgroundColor: isCurrent ? 'rgba(6, 182, 212, 0.1)' : 'rgba(30, 41, 59, 0.5)', border: `1px solid ${isCurrent ? '#06b6d4' : '#1e293b'}`, borderRadius: '8px' }}>
                <div style={{ fontWeight: 600, fontSize: '14px', marginBottom: '4px' }}>{isCompleted ? '✓ ' : ''}{step.title || `Step ${idx + 1}`}</div>
                <div style={{ fontSize: '13px', color: '#94a3b8' }}>{step.content || step.description || JSON.stringify(step)}</div>
                {isCurrent && (
                  <button onClick={() => updateProgress(tutorial.id, idx + 1)} style={{ marginTop: '12px', padding: '8px 16px', backgroundColor: '#06b6d4', border: 'none', borderRadius: '6px', color: '#02040a', fontWeight: 600, cursor: 'pointer', fontSize: '12px' }}>
                    Mark Complete
                  </button>
                )}
              </div>
            )
          })}
        </div>
      </div>
    )
  }

  return (
    <div>
      <h3 style={{ marginTop: 0, color: '#06b6d4' }}>Tutorials</h3>
      <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
        {tutorials.map(t => {
          const p = progress.find(pr => pr.tutorial_id === t.id)
          return (
            <div key={t.id} style={{ padding: '16px', backgroundColor: 'rgba(30, 41, 59, 0.5)', border: '1px solid #1e293b', borderRadius: '8px' }}>
              <div style={{ fontWeight: 600, fontSize: '14px' }}>{t.title}</div>
              <div style={{ fontSize: '12px', color: '#64748b', marginTop: '4px' }}>{t.description} · {t.difficulty} · {t.estimated_time} min</div>
              {p && (
                <div style={{ marginTop: '8px', fontSize: '11px', color: '#06b6d4' }}>
                  Progress: Step {p.current_step} {p.completed ? '· Completed ✓' : ''}
                </div>
              )}
              <button onClick={() => startTutorial(t.id)} style={{ marginTop: '12px', padding: '8px 16px', backgroundColor: '#06b6d4', border: 'none', borderRadius: '6px', color: '#02040a', fontWeight: 600, cursor: 'pointer', fontSize: '12px' }}>
                {p ? 'Continue' : 'Start Tutorial'}
              </button>
            </div>
          )
        })}
      </div>
    </div>
  )
}
