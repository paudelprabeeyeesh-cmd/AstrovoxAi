import { useState } from 'react'
import { supabase } from './supabase'

export default function Auth() {
  const [loading, setLoading] = useState(false)
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [isSignUp, setIsSignUp] = useState(false)

  async function handleAuth(e) {
    e.preventDefault()
    if (!email || !password) return alert('Input matrix incomplete.')

    try {
      setLoading(true)
      if (isSignUp) {
        const { error } = await supabase.auth.signUp({ email, password })
        if (error) throw error
        alert('Transmission sent! Confirm via your email hyperlink.')
      } else {
        const { error } = await supabase.auth.signInWithPassword({ email, password })
        if (error) throw error
      }
    } catch (err) {
      alert(`Access Denied: ${err.message}`)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div style={{
      backgroundColor: '#02040a',
      minHeight: '100vh',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      fontFamily: 'monospace',
      color: '#slate-200',
      padding: '20px'
    }}>
      <div style={{
        backgroundColor: 'rgba(4, 8, 20, 0.85)',
        backdropFilter: 'blur(12px)',
        border: '1px solid #1e293b',
        borderRadius: '16px',
        padding: '40px',
        width: '100%',
        maxWidth: '400px',
        boxShadow: '0 0 30px rgba(6, 182, 212, 0.15)'
      }}>
        {/* Futuristic Brand Header */}
        <div style={{ textAlign: 'center', marginBottom: '30px' }}>
          <h2 style={{
            fontSize: '20px',
            fontWeight: '900',
            letterSpacing: '2px',
            color: '#fff',
            margin: 0
          }}>
            ASTROVOX <span style={{ color: '#d946ef', fontSize: '14px' }}>PRIME</span>
          </h2>
          <p style={{ fontSize: '10px', color: '#64748b', letterSpacing: '1px', marginTop: '5px' }}>
            {isSignUp ? 'REGISTER NEW QUANTUM LINK' : 'SECURE IDENTITY VERIFICATION'}
          </p>
        </div>
        
        <form onSubmit={handleAuth} style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
          <div>
            <label style={{ display: 'block', marginBottom: '8px', fontSize: '11px', color: '#94a3b8', letterSpacing: '1px' }}>
              ACCESS IDENTIFIER (EMAIL)
            </label>
            <input 
              type="email" 
              placeholder="name@domain.com" 
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              style={{
                width: '100%',
                padding: '12px',
                borderRadius: '8px',
                backgroundColor: '#050a18',
                border: '1px solid #1e293b',
                color: '#67e8f9',
                fontFamily: 'monospace',
                boxSizing: 'border-box'
              }}
            />
          </div>

          <div>
            <label style={{ display: 'block', marginBottom: '8px', fontSize: '11px', color: '#94a3b8', letterSpacing: '1px' }}>
              SECURITY KEY (PASSWORD)
            </label>
            <input 
              type="password" 
              placeholder="••••••••" 
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              style={{
                width: '100%',
                padding: '12px',
                borderRadius: '8px',
                backgroundColor: '#050a18',
                border: '1px solid #1e293b',
                color: '#67e8f9',
                fontFamily: 'monospace',
                boxSizing: 'border-box'
              }}
            />
          </div>

          <button 
            type="submit" 
            disabled={loading}
            style={{
              padding: '14px',
              background: 'linear-gradient(to right, #06b6d4, #3b82f6)',
              color: '#02040a',
              border: 'none',
              borderRadius: '8px',
              cursor: 'pointer',
              fontWeight: 'bold',
              letterSpacing: '1px',
              marginTop: '10px',
              boxShadow: '0 4px 14px rgba(6, 182, 212, 0.3)'
            }}
          >
            {loading ? 'INITIALIZING...' : isSignUp ? 'CREATE NEXUS LINK' : 'ESTABLISH LINK'}
          </button>
        </form>

        <div style={{ textAlign: 'center', marginTop: '25px', fontSize: '12px' }}>
          <button 
            onClick={() => setIsSignUp(!isSignUp)} 
            style={{ background: 'none', border: 'none', color: '#06b6d4', cursor: 'pointer', textDecoration: 'underline', fontFamily: 'monospace' }}
          >
            {isSignUp ? '>> Return to standard login secure gate' : ">> Request new credentials architecture"}
          </button>
        </div>
      </div>
    </div>
  )
}