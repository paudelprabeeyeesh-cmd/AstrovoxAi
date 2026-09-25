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

export default function OnboardingFlow({ onComplete }) {
  const [progress, setProgress] = useState(null)
  const [currentStep, setCurrentStep] = useState(0)
  const [completed, setCompleted] = useState(false)
  const headers = useAuthHeaders()

  const steps = [
    { id: 'welcome', title: 'Welcome', description: 'Welcome to AstrovoxAI! Let us show you around.' },
    { id: 'profile', title: 'Profile', description: 'Complete your profile to personalize your experience.' },
    { id: 'first-chat', title: 'First Chat', description: 'Send your first message to the AI assistant.' },
    { id: 'explore', title: 'Explore', description: 'Discover Memory, Settings, and advanced features.' },
  ]

  useEffect(() => {
    const init = async () => {
      const res = await fetch(`${API_BASE}/cx/onboarding`, { headers })
      const data = await res.json()
      if (res.ok && data.progress) {
        setProgress(data.progress)
        setCompleted(data.progress.completed)
        if (data.progress.completed_steps?.length > 0) {
          setCurrentStep(data.progress.completed_steps.length)
        }
      } else {
        await fetch(`${API_BASE}/cx/onboarding/start`, { method: 'POST', headers })
      }
    }
    init()
  }, [headers])

  const completeStep = async (stepId) => {
    await fetch(`${API_BASE}/cx/onboarding/step`, { method: 'POST', headers, body: JSON.stringify({ step: stepId }) })
    setCurrentStep(prev => prev + 1)
  }

  const finish = async () => {
    await fetch(`${API_BASE}/cx/onboarding/complete`, { method: 'POST', headers })
    setCompleted(true)
    onComplete?.()
  }

  if (completed) {
    return (
      <div style={{ textAlign: 'center', padding: '40px' }}>
        <div style={{ fontSize: '48px', marginBottom: '16px' }}>🎉</div>
        <h3 style={{ color: '#06b6d4', margin: '0 0 8px 0' }}>Onboarding Complete!</h3>
        <p style={{ color: '#64748b' }}>You're all set. Start exploring AstrovoxAI.</p>
      </div>
    )
  }

  const step = steps[currentStep] || steps[steps.length - 1]

  return (
    <div style={{ maxWidth: '600px', margin: '0 auto', padding: '20px' }}>
      <h3 style={{ marginTop: 0, color: '#06b6d4' }}>Getting Started</h3>
      <div style={{ display: 'flex', gap: '8px', marginBottom: '24px' }}>
        {steps.map((s, i) => (
          <div key={s.id} style={{ flex: 1, height: '4px', borderRadius: '2px', backgroundColor: i <= currentStep ? '#06b6d4' : '#1e293b' }} />
        ))}
      </div>
      <div style={{ padding: '24px', backgroundColor: 'rgba(30, 41, 59, 0.5)', border: '1px solid #1e293b', borderRadius: '12px', marginBottom: '24px' }}>
        <h4 style={{ margin: '0 0 8px 0', color: '#e2e8f0' }}>{step.title}</h4>
        <p style={{ color: '#94a3b8', fontSize: '14px', lineHeight: 1.6 }}>{step.description}</p>
      </div>
      <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '12px' }}>
        {currentStep < steps.length - 1 ? (
          <button onClick={() => completeStep(step.id)} style={{ padding: '10px 20px', backgroundColor: '#06b6d4', border: 'none', borderRadius: '6px', color: '#02040a', fontWeight: 600, cursor: 'pointer' }}>
            Next
          </button>
        ) : (
          <button onClick={finish} style={{ padding: '10px 20px', backgroundColor: '#22c55e', border: 'none', borderRadius: '6px', color: '#02040a', fontWeight: 600, cursor: 'pointer' }}>
            Finish
          </button>
        )}
      </div>
    </div>
  )
}
