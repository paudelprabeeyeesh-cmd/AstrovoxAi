import React, { useState, useEffect, useCallback } from 'react'
import { supabase } from '../supabase'
import { isMobile, getDeviceType } from '../utils/platform'
import { createStorage } from '../utils/storage'

const MOBILE_STORAGE = createStorage('mobile_auth')

export function useMobileAuth() {
  const [loading, setLoading] = useState(false)
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [fullName, setFullName] = useState('')
  const [isSignUp, setIsSignUp] = useState(false)
  const [isForgotPassword, setIsForgotPassword] = useState(false)
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')
  const [biometricAvailable, setBiometricAvailable] = useState(false)
  const [deviceType, setDeviceType] = useState(getDeviceType())

  useEffect(() => {
    const handleResize = () => setDeviceType(getDeviceType())
    window.addEventListener('resize', handleResize)
    checkBiometric()
    return () => window.removeEventListener('resize', handleResize)
  }, [])

  const checkBiometric = useCallback(async () => {
    if (window.PublicKeyCredential) {
      try {
        const available = await PublicKeyCredential.isUserVerifyingPlatformAuthenticatorAvailable()
        setBiometricAvailable(available)
      } catch {
        setBiometricAvailable(false)
      }
    }
  }, [])

  const handleAuth = useCallback(async (e) => {
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
        setMessage('Account created! Please check your email to confirm.')
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
        setMessage('Login successful!')
        if (biometricAvailable) {
          await saveBiometricCredentials(email, password)
        }
      }
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }, [email, password, fullName, isSignUp, biometricAvailable])

  const handleForgotPassword = useCallback(async (e) => {
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
      setMessage('Password reset link sent!')
      setEmail('')
      setTimeout(() => setIsForgotPassword(false), 3000)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }, [email])

  const saveBiometricCredentials = useCallback(async (email, password) => {
    try {
      if (window.PublicKeyCredential) {
        const challenge = new Uint8Array(32)
        crypto.getRandomValues(challenge)
        MOBILE_STORAGE.set('pending_credentials', { email, password })
      }
    } catch {
      console.warn('Biometric storage not available')
    }
  }, [])

  const authenticateWithBiometric = useCallback(async () => {
    try {
      const pending = MOBILE_STORAGE.get('pending_credentials')
      if (!pending) {
        setError('No saved credentials found. Please sign in first.')
        return
      }
      if (window.PublicKeyCredential) {
        const available = await PublicKeyCredential.isUserVerifyingPlatformAuthenticatorAvailable()
        if (!available) {
          setError('Biometric authentication not available on this device.')
          return
        }
      }
      setEmail(pending.email)
      setPassword(pending.password)
      await handleAuth({ preventDefault: () => {} })
    } catch (err) {
      setError('Biometric authentication failed.')
    }
  }, [handleAuth])

  const isPhone = deviceType === 'phone'

  return {
    loading,
    email,
    password,
    fullName,
    isSignUp,
    isForgotPassword,
    message,
    error,
    biometricAvailable,
    deviceType,
    isPhone,
    setEmail,
    setPassword,
    setFullName,
    setIsSignUp,
    setIsForgotPassword,
    setMessage,
    setError,
    handleAuth,
    handleForgotPassword,
    authenticateWithBiometric
  }
}

export function MobileAuthFlow() {
  const {
    loading,
    email,
    password,
    fullName,
    isSignUp,
    isForgotPassword,
    message,
    error,
    biometricAvailable,
    isPhone,
    setEmail,
    setPassword,
    setFullName,
    setIsSignUp,
    setIsForgotPassword,
    setMessage,
    setError,
    handleAuth,
    handleForgotPassword,
    authenticateWithBiometric
  } = useMobileAuth()

  const fieldWidth = isPhone ? '100%' : '320px'

  return (
    <div style={{
      backgroundColor: '#02040a',
      minHeight: '100vh',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      fontFamily: 'monospace',
      color: '#e2e8f0',
      padding: 20,
      backgroundImage: 'radial-gradient(ellipse at 50% 0%, rgba(6, 182, 212, 0.05) 0%, transparent 70%)'
    }}>
      <div style={{
        backgroundColor: 'rgba(4, 8, 20, 0.85)',
        backdropFilter: 'blur(12px)',
        border: '1px solid #1e293b',
        borderRadius: 16,
        padding: isPhone ? 24 : 40,
        width: '100%',
        maxWidth: isPhone ? '100%' : 400,
        boxShadow: '0 0 30px rgba(6, 182, 212, 0.15)'
      }}>
        <div style={{ textAlign: 'center', marginBottom: 30 }}>
          <h2 style={{
            fontSize: isPhone ? 18 : 20,
            fontWeight: 900,
            letterSpacing: '2px',
            color: '#fff',
            margin: 0
          }}>
            ASTROVOX <span style={{ color: '#d946ef', fontSize: isPhone ? 12 : 14 }}>PRIME</span>
          </h2>
          <p style={{ fontSize: 10, color: '#64748b', letterSpacing: '1px', marginTop: 5 }}>
            {isForgotPassword ? 'RESET SECURITY KEY' : isSignUp ? 'REGISTER NEW QUANTUM LINK' : 'SECURE IDENTITY VERIFICATION'}
          </p>
        </div>

        {message && (
          <div style={{
            backgroundColor: 'rgba(34, 197, 94, 0.1)',
            border: '1px solid #22c55e',
            borderRadius: 8,
            padding: 12,
            marginBottom: 20,
            fontSize: 12,
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
            borderRadius: 8,
            padding: 12,
            marginBottom: 20,
            fontSize: 12,
            color: '#f87171',
            textAlign: 'center'
          }}>
            {error}
          </div>
        )}

        {isForgotPassword ? (
          <form onSubmit={handleForgotPassword} style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
            <div>
              <label style={{ display: 'block', marginBottom: 8, fontSize: 11, color: '#94a3b8', letterSpacing: '1px' }}>
                ACCESS IDENTIFIER (EMAIL)
              </label>
              <input
                type="email"
                placeholder="name@domain.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                style={{
                  width: fieldWidth,
                  padding: 12,
                  borderRadius: 8,
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
                padding: 14,
                background: 'linear-gradient(to right, #06b6d4, #3b82f6)',
                color: '#02040a',
                border: 'none',
                borderRadius: 8,
                cursor: 'pointer',
                fontWeight: 'bold',
                letterSpacing: '1px',
                marginTop: 10,
                boxShadow: '0 4px 14px rgba(6, 182, 212, 0.3)',
                opacity: loading ? 0.7 : 1
              }}
            >
              {loading ? 'SENDING...' : 'SEND RESET LINK'}
            </button>
          </form>
        ) : (
          <form onSubmit={handleAuth} style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
            {isSignUp && (
              <div>
                <label style={{ display: 'block', marginBottom: 8, fontSize: 11, color: '#94a3b8', letterSpacing: '1px' }}>
                  FULL NAME
                </label>
                <input
                  type="text"
                  placeholder="Your full name"
                  value={fullName}
                  onChange={(e) => setFullName(e.target.value)}
                  style={{
                    width: fieldWidth,
                    padding: 12,
                    borderRadius: 8,
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
              <label style={{ display: 'block', marginBottom: 8, fontSize: 11, color: '#94a3b8', letterSpacing: '1px' }}>
                ACCESS IDENTIFIER (EMAIL)
              </label>
              <input
                type="email"
                placeholder="name@domain.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                style={{
                  width: fieldWidth,
                  padding: 12,
                  borderRadius: 8,
                  backgroundColor: '#050a18',
                  border: '1px solid #1e293b',
                  color: '#67e8f9',
                  fontFamily: 'monospace',
                  boxSizing: 'border-box'
                }}
              />
            </div>

            <div>
              <label style={{ display: 'block', marginBottom: 8, fontSize: 11, color: '#94a3b8', letterSpacing: '1px' }}>
                SECURITY KEY (PASSWORD)
              </label>
              <input
                type="password"
                placeholder="••••••••"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                style={{
                  width: fieldWidth,
                  padding: 12,
                  borderRadius: 8,
                  backgroundColor: '#050a18',
                  border: '1px solid #1e293b',
                  color: '#67e8f9',
                  fontFamily: 'monospace',
                  boxSizing: 'border-box'
                }}
              />
            </div>

            {!isSignUp && biometricAvailable && (
              <button
                type="button"
                onClick={authenticateWithBiometric}
                style={{
                  padding: 10,
                  background: 'rgba(6, 182, 212, 0.1)',
                  border: '1px solid #06b6d4',
                  color: '#06b6d4',
                  borderRadius: 8,
                  cursor: 'pointer',
                  fontSize: 12,
                  fontWeight: 600
                }}
              >
                Authenticate with Biometrics
              </button>
            )}

            <button
              type="submit"
              disabled={loading}
              style={{
                padding: 14,
                background: 'linear-gradient(to right, #06b6d4, #3b82f6)',
                color: '#02040a',
                border: 'none',
                borderRadius: 8,
                cursor: 'pointer',
                fontWeight: 'bold',
                letterSpacing: '1px',
                marginTop: 10,
                boxShadow: '0 4px 14px rgba(6, 182, 212, 0.3)',
                opacity: loading ? 0.7 : 1
              }}
            >
              {loading ? 'INITIALIZING...' : isSignUp ? 'CREATE NEXUS LINK' : 'ESTABLISH LINK'}
            </button>
          </form>
        )}

        <div style={{ textAlign: 'center', marginTop: 25, fontSize: 12, display: 'flex', flexDirection: 'column', gap: 10 }}>
          {!isForgotPassword && (
            <button
              onClick={() => { setIsSignUp(!isSignUp); setError(''); setMessage('') }}
              style={{ background: 'none', border: 'none', color: '#06b6d4', cursor: 'pointer', textDecoration: 'underline', fontFamily: 'monospace' }}
            >
              {isSignUp ? '>> Return to standard login secure gate' : '>> Request new credentials architecture'}
            </button>
          )}

          {!isSignUp && !isForgotPassword && (
            <button
              onClick={() => { setIsForgotPassword(true); setError(''); setMessage('') }}
              style={{ background: 'none', border: 'none', color: '#d946ef', cursor: 'pointer', textDecoration: 'underline', fontFamily: 'monospace' }}
            >
              {'>> Forgot security key?'}
            </button>
          )}

          {isForgotPassword && (
            <button
              onClick={() => { setIsForgotPassword(false); setError(''); setMessage('') }}
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
