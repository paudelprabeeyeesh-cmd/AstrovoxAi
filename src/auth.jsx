import { useState } from 'react'
import { supabase } from './supabase'

export default function Auth() {
  const [loading, setLoading] = useState(false)
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [fullName, setFullName] = useState('')
  const [isSignUp, setIsSignUp] = useState(false)
  const [isForgotPassword, setIsForgotPassword] = useState(false)
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')

  async function handleAuth(e) {
    e.preventDefault()
    setMessage('')
    setError('')

    if (!email || !password) {
      setError('Email and password are required.')
      return
    }

    if (isSignUp && !fullName) {
      setError('Full name is required for sign up.')
      return
    }

    try {
      setLoading(true)
      if (isSignUp) {
        const { error: signUpError } = await supabase.auth.signUp({
          email,
          password,
          options: {
            data: {
              full_name: fullName,
              username: email.split('@')[0]
            }
          }
        })
        if (signUpError) throw signUpError
        setMessage('✅ Account created! Please check your email to confirm.')
        setEmail('')
        setPassword('')
        setFullName('')
        setTimeout(() => setIsSignUp(false), 2000)
      } else {
        const { error: signInError } = await supabase.auth.signInWithPassword({
          email,
          password
        })
        if (signInError) throw signInError
        setMessage('✅ Login successful!')
      }
    } catch (err) {
      setError(`❌ ${err.message}`)
    } finally {
      setLoading(false)
    }
  }

  async function handleForgotPassword(e) {
    e.preventDefault()
    setMessage('')
    setError('')

    if (!email) {
      setError('Email is required.')
      return
    }

    try {
      setLoading(true)
      const { error } = await supabase.auth.resetPasswordForEmail(email, {
        redirectTo: `${window.location.origin}/reset-password`
      })
      if (error) throw error
      setMessage('✅ Password reset link sent to your email!')
      setEmail('')
      setTimeout(() => setIsForgotPassword(false), 3000)
    } catch (err) {
      setError(`❌ ${err.message}`)
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
      padding: '20px',
      backgroundImage: 'radial-gradient(ellipse at 50% 0%, rgba(6, 182, 212, 0.05) 0%, transparent 70%)'
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
            {isForgotPassword ? 'RESET SECURITY KEY' : isSignUp ? 'REGISTER NEW QUANTUM LINK' : 'SECURE IDENTITY VERIFICATION'}
          </p>
        </div>

        {/* Messages */}
        {message && (
          <div style={{
            backgroundColor: 'rgba(34, 197, 94, 0.1)',
            border: '1px solid #22c55e',
            borderRadius: '8px',
            padding: '12px',
            marginBottom: '20px',
            fontSize: '12px',
            color: '#22c55e',
            textAlign: 'center'
          }}>
            {message}
          </div>
        )}
        
        {error && (
          <div style={{
            backgroundColor: 'rgba(239, 68, 68, 0.1)',
            border: '1px solid #ef4444',
            borderRadius: '8px',
            padding: '12px',
            marginBottom: '20px',
            fontSize: '12px',
            color: '#f87171',
            textAlign: 'center'
          }}>
            {error}
          </div>
        )}

        {/* Forms */}
        {isForgotPassword ? (
          <form onSubmit={handleForgotPassword} style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
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
                boxShadow: '0 4px 14px rgba(6, 182, 212, 0.3)',
                opacity: loading ? 0.7 : 1
              }}
            >
              {loading ? 'SENDING...' : 'SEND RESET LINK'}
            </button>
          </form>
        ) : (
          <form onSubmit={handleAuth} style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
            {isSignUp && (
              <div>
                <label style={{ display: 'block', marginBottom: '8px', fontSize: '11px', color: '#94a3b8', letterSpacing: '1px' }}>
                  FULL NAME
                </label>
                <input 
                  type="text" 
                  placeholder="Your full name" 
                  value={fullName}
                  onChange={(e) => setFullName(e.target.value)}
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
            )}

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
                boxShadow: '0 4px 14px rgba(6, 182, 212, 0.3)',
                opacity: loading ? 0.7 : 1
              }}
            >
              {loading ? 'INITIALIZING...' : isSignUp ? 'CREATE NEXUS LINK' : 'ESTABLISH LINK'}
            </button>
          </form>
        )}

        {/* Toggle Links */}
        <div style={{ textAlign: 'center', marginTop: '25px', fontSize: '12px', display: 'flex', flexDirection: 'column', gap: '10px' }}>
          {!isForgotPassword && (
            <button 
              onClick={() => setIsSignUp(!isSignUp)} 
              style={{ background: 'none', border: 'none', color: '#06b6d4', cursor: 'pointer', textDecoration: 'underline', fontFamily: 'monospace' }}
            >
              {isSignUp ? '>> Return to standard login secure gate' : '>> Request new credentials architecture'}
            </button>
          )}
          
          {!isSignUp && !isForgotPassword && (
            <button 
              onClick={() => setIsForgotPassword(true)} 
              style={{ background: 'none', border: 'none', color: '#d946ef', cursor: 'pointer', textDecoration: 'underline', fontFamily: 'monospace' }}
            >
              {'>> Forgot security key?'}
            </button>
          )}

          {isForgotPassword && (
            <button 
              onClick={() => setIsForgotPassword(false)} 
              style={{ background: 'none', border: 'none', color: '#06b6d4', cursor: 'pointer', textDecoration: 'underline', fontFamily: 'monospace' }}
            >
              {'>> Return to login'}
            </button>
          )}
        </div>
      </div>
    </div>
  )
}
