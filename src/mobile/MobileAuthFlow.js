import React, { useState, useEffect, useCallback } from 'react'
import { View, Text, TextInput, TouchableOpacity, Alert, Platform } from 'react-native'
import * as LocalAuthentication from 'expo-local-authentication'
import * as SecureStore from 'expo-secure-store'
import { supabase } from '../supabase'
import { isMobile, getDeviceType } from '../utils/platform'
import { createSecureStorage } from './storageAdapter'

const SECURE_STORAGE = createSecureStorage('mobile_auth')

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
  const [biometricType, setBiometricType] = useState('none')
  const [deviceType, setDeviceType] = useState(getDeviceType())

  useEffect(() => {
    checkBiometric()
  }, [])

  const checkBiometric = useCallback(async () => {
    try {
      const compatible = await LocalAuthentication.hasHardwareAsync()
      if (compatible) {
        const enrolled = await LocalAuthentication.isEnrolledAsync()
        const types = await LocalAuthentication.supportedAuthenticationTypesAsync()
        setBiometricAvailable(enrolled)
        setBiometricType(enrolled ? types[0]?.toString() || 'biometric' : 'none')
      } else {
        setBiometricAvailable(false)
      }
    } catch {
      setBiometricAvailable(false)
    }
  }, [])

  const handleAuth = useCallback(async (e) => {
    e?.preventDefault?.()
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
        const { error: signInError, data } = await supabase.auth.signInWithPassword({
          email,
          password
        })
        if (signInError) throw signInError
        setMessage('Login successful!')
        if (biometricAvailable && data?.session) {
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
    e?.preventDefault?.()
    setMessage('')
    setError('')

    if (!email) {
      setError('Email is required.')
      return
    }

    try {
      setLoading(true)
      const { error } = await supabase.auth.resetPasswordForEmail(email, {
        redirectTo: 'astrovoxai://reset-password'
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
      await SECURE_STORAGE.set('pending_credentials', { email, password })
    } catch (e) {
      console.warn('Biometric storage not available:', e)
    }
  }, [])

  const authenticateWithBiometric = useCallback(async () => {
    try {
      const result = await LocalAuthentication.authenticateAsync({
        promptMessage: 'Authenticate with biometrics',
        fallbackLabel: 'Use passcode',
        cancelLabel: 'Cancel'
      })

      if (result.success) {
        const pending = await SECURE_STORAGE.get('pending_credentials')
        if (pending) {
          setEmail(pending.email)
          setPassword(pending.password)
          await handleAuth({ preventDefault: () => {} })
        } else {
          setError('No saved credentials found. Please sign in first.')
        }
      } else if (result.error) {
        setError(`Biometric authentication failed: ${result.error}`)
      }
    } catch (err) {
      setError('Biometric authentication not available.')
    }
  }, [handleAuth])

  const signOut = useCallback(async () => {
    try {
      await supabase.auth.signOut()
      setEmail('')
      setPassword('')
      setFullName('')
      setMessage('')
      setError('')
      await SECURE_STORAGE.remove('pending_credentials')
    } catch (err) {
      setError(err.message)
    }
  }, [])

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
    biometricType,
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
    authenticateWithBiometric,
    signOut
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
    <View style={{
      flex: 1,
      backgroundColor: '#02040a',
      alignItems: 'center',
      justifyContent: 'center',
      padding: 20,
      fontFamily: Platform.select({ ios: 'Menlo', android: 'monospace' })
    }}>
      <View style={{
        backgroundColor: 'rgba(4, 8, 20, 0.85)',
        borderWidth: 1,
        borderColor: '#1e293b',
        borderRadius: 16,
        padding: isPhone ? 24 : 40,
        width: '100%',
        maxWidth: isPhone ? '100%' : 400
      }}>
        <View style={{ textAlign: 'center', marginBottom: 30 }}>
          <Text style={{
            fontSize: isPhone ? 18 : 20,
            fontWeight: '900',
            letterSpacing: 2,
            color: '#fff'
          }}>
            ASTROVOX <Text style={{ color: '#d946ef', fontSize: isPhone ? 12 : 14 }}>PRIME</Text>
          </Text>
          <Text style={{ fontSize: 10, color: '#64748b', letterSpacing: 1, marginTop: 5 }}>
            {isForgotPassword ? 'RESET SECURITY KEY' : isSignUp ? 'REGISTER NEW QUANTUM LINK' : 'SECURE IDENTITY VERIFICATION'}
          </Text>
        </View>

        {message ? (
          <View style={{
            backgroundColor: 'rgba(34, 197, 94, 0.1)',
            borderWidth: 1,
            borderColor: '#22c55e',
            borderRadius: 8,
            padding: 12,
            marginBottom: 20
          }}>
            <Text style={{ color: '#22c55e', fontSize: 12, textAlign: 'center' }}>{message}</Text>
          </View>
        ) : null}

        {error ? (
          <View style={{
            backgroundColor: 'rgba(239, 68, 68, 0.1)',
            borderWidth: 1,
            borderColor: '#ef4444',
            borderRadius: 8,
            padding: 12,
            marginBottom: 20
          }}>
            <Text style={{ color: '#f87171', fontSize: 12, textAlign: 'center' }}>{error}</Text>
          </View>
        ) : null}

        {isForgotPassword ? (
          <View>
            <Text style={{ fontSize: 11, color: '#94a3b8', letterSpacing: 1, marginBottom: 8 }}>
              ACCESS IDENTIFIER (EMAIL)
            </Text>
            <TextInput
              style={{
                width: fieldWidth,
                padding: 12,
                borderRadius: 8,
                backgroundColor: '#050a18',
                borderWidth: 1,
                borderColor: '#1e293b',
                color: '#67e8f9',
                fontFamily: Platform.select({ ios: 'Menlo', android: 'monospace' }),
                marginBottom: 20
              }}
              placeholder="name@domain.com"
              placeholderTextColor="#64748b"
              value={email}
              onChangeText={setEmail}
              autoCapitalize="none"
              keyboardType="email-address"
            />
            <TouchableOpacity
              onPress={handleForgotPassword}
              disabled={loading}
              style={{
                padding: 14,
                backgroundColor: '#06b6d4',
                borderRadius: 8,
                opacity: loading ? 0.7 : 1
              }}
            >
              <Text style={{
                color: '#02040a',
                fontWeight: 'bold',
                textAlign: 'center',
                letterSpacing: 1
              }}>
                {loading ? 'SENDING...' : 'SEND RESET LINK'}
              </Text>
            </TouchableOpacity>
          </View>
        ) : (
          <View>
            {isSignUp && (
              <View style={{ marginBottom: 20 }}>
                <Text style={{ fontSize: 11, color: '#94a3b8', letterSpacing: 1, marginBottom: 8 }}>
                  FULL NAME
                </Text>
                <TextInput
                  style={{
                    width: fieldWidth,
                    padding: 12,
                    borderRadius: 8,
                    backgroundColor: '#050a18',
                    borderWidth: 1,
                    borderColor: '#1e293b',
                    color: '#67e8f9',
                    fontFamily: Platform.select({ ios: 'Menlo', android: 'monospace' })
                  }}
                  placeholder="Your full name"
                  placeholderTextColor="#64748b"
                  value={fullName}
                  onChangeText={setFullName}
                />
              </View>
            )}

            <View style={{ marginBottom: 20 }}>
              <Text style={{ fontSize: 11, color: '#94a3b8', letterSpacing: 1, marginBottom: 8 }}>
                ACCESS IDENTIFIER (EMAIL)
              </Text>
              <TextInput
                style={{
                  width: fieldWidth,
                  padding: 12,
                  borderRadius: 8,
                  backgroundColor: '#050a18',
                  borderWidth: 1,
                  borderColor: '#1e293b',
                  color: '#67e8f9',
                  fontFamily: Platform.select({ ios: 'Menlo', android: 'monospace' })
                }}
                placeholder="name@domain.com"
                placeholderTextColor="#64748b"
                value={email}
                onChangeText={setEmail}
                autoCapitalize="none"
                keyboardType="email-address"
              />
            </View>

            <View style={{ marginBottom: 20 }}>
              <Text style={{ fontSize: 11, color: '#94a3b8', letterSpacing: 1, marginBottom: 8 }}>
                SECURITY KEY (PASSWORD)
              </Text>
              <TextInput
                style={{
                  width: fieldWidth,
                  padding: 12,
                  borderRadius: 8,
                  backgroundColor: '#050a18',
                  borderWidth: 1,
                  borderColor: '#1e293b',
                  color: '#67e8f9',
                  fontFamily: Platform.select({ ios: 'Menlo', android: 'monospace' })
                }}
                placeholder="••••••••"
                placeholderTextColor="#64748b"
                value={password}
                onChangeText={setPassword}
                secureTextEntry
              />
            </View>

            {!isSignUp && biometricAvailable && (
              <TouchableOpacity
                onPress={authenticateWithBiometric}
                style={{
                  padding: 10,
                  backgroundColor: 'rgba(6, 182, 212, 0.1)',
                  borderWidth: 1,
                  borderColor: '#06b6d4',
                  borderRadius: 8,
                  marginBottom: 12
                }}
              >
                <Text style={{
                  color: '#06b6d4',
                  fontSize: 12,
                  fontWeight: '600',
                  textAlign: 'center'
                }}>
                  Authenticate with Biometrics ({biometricType})
                </Text>
              </TouchableOpacity>
            )}

            <TouchableOpacity
              onPress={handleAuth}
              disabled={loading}
              style={{
                padding: 14,
                backgroundColor: '#06b6d4',
                borderRadius: 8,
                opacity: loading ? 0.7 : 1
              }}
            >
              <Text style={{
                color: '#02040a',
                fontWeight: 'bold',
                textAlign: 'center',
                letterSpacing: 1
              }}>
                {loading ? 'INITIALIZING...' : isSignUp ? 'CREATE NEXUS LINK' : 'ESTABLISH LINK'}
              </Text>
            </TouchableOpacity>
          </View>
        )}

        <View style={{ textAlign: 'center', marginTop: 25 }}>
          {!isForgotPassword && (
            <TouchableOpacity
              onPress={() => { setIsSignUp(!isSignUp); setError(''); setMessage('') }}
              style={{ padding: 8 }}
            >
              <Text style={{ color: '#06b6d4', fontSize: 12 }}>
                {isSignUp ? '>> Return to standard login secure gate' : '>> Request new credentials architecture'}
              </Text>
            </TouchableOpacity>
          )}

          {!isSignUp && !isForgotPassword && (
            <TouchableOpacity
              onPress={() => { setIsForgotPassword(true); setError(''); setMessage('') }}
              style={{ padding: 8 }}
            >
              <Text style={{ color: '#d946ef', fontSize: 12 }}>{'>> Forgot security key?'}</Text>
            </TouchableOpacity>
          )}

          {isForgotPassword && (
            <TouchableOpacity
              onPress={() => { setIsForgotPassword(false); setError(''); setMessage('') }}
              style={{ padding: 8 }}
            >
              <Text style={{ color: '#06b6d4', fontSize: 12 }}>{'>> Return to login'}</Text>
            </TouchableOpacity>
          )}
        </View>
      </View>
    </View>
  )
}
