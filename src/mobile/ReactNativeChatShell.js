import React, { useState, useEffect, useRef, useCallback } from 'react'
import { useChatHistory } from '../hooks/useChatHistory'
import { useOfflineMode } from '../offline/OfflineManager'
import { isMobile, getDeviceType } from '../utils/platform'
import { createStorage } from '../utils/storage'

const MOBILE_STORAGE = createStorage('mobile')

export function ReactNativeChatShell({
  session,
  conversationId,
  model = 'gpt-4',
  onConversationChange,
  onError
}) {
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [deviceType, setDeviceType] = useState(getDeviceType())
  const messagesEndRef = useRef(null)
  const inputRef = useRef(null)
  const { history } = useChatHistory()
  const { isOnline, saveMessageOffline } = useOfflineMode()

  useEffect(() => {
    const handleResize = () => setDeviceType(getDeviceType())
    window.addEventListener('resize', handleResize)
    return () => window.removeEventListener('resize', handleResize)
  }, [])

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const sendMessage = useCallback(async (e) => {
    e?.preventDefault()
    if (!input.trim() || loading) return

    const userMessage = {
      role: 'user',
      content: input.trim(),
      timestamp: new Date().toISOString(),
      id: Date.now(),
      offline: false
    }

    setMessages(prev => [...prev, userMessage])
    setInput('')
    setLoading(true)

    try {
      const { data: { session: currentSession } } = await MOBILE_STORAGE.get('supabase') || { data: { session: null } }
      const token = currentSession?.access_token

      if (!token) {
        throw new Error('No authentication token available')
      }

      const apiBase = import.meta.env.VITE_API_URL || '/api'
      const response = await fetch(`${apiBase}/chat/message`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
          conversation_id: conversationId,
          message: userMessage.content,
          model
        })
      })

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: response.statusText }))
        throw new Error(errorData.detail || 'Failed to send message')
      }

      const result = await response.json()
      if (result.ai_message) {
        setMessages(prev => [...prev, {
          ...result.ai_message,
          id: result.ai_message.id || Date.now() + 1,
          timestamp: new Date(result.ai_message.created_at).toISOString()
        }])
      }
    } catch (err) {
      if (!isOnline) {
        saveMessageOffline(userMessage)
      }
      onError?.(err)
    } finally {
      setLoading(false)
    }
  }, [input, loading, conversationId, model, isOnline, saveMessageOffline, onError])

  const isPhone = deviceType === 'phone'
  const fontSize = isPhone ? 14 : 13
  const padding = isPhone ? 16 : 20
  const borderRadius = isPhone ? 24 : 12

  return (
    <div style={{
      display: 'flex',
      flexDirection: 'column',
      height: '100%',
      backgroundColor: '#02040a',
      borderRadius,
      border: '1px solid #1e293b',
      overflow: 'hidden',
      fontFamily: 'monospace',
      maxWidth: isPhone ? '100%' : '100%'
    }}>
      <div style={{
        padding: '12px 16px',
        borderBottom: '1px solid #1e293b',
        backgroundColor: 'rgba(4, 8, 20, 0.9)',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center'
      }}>
        <h3 style={{
          margin: 0,
          fontSize: 13,
          color: '#67e8f9',
          letterSpacing: '1px',
          fontWeight: 600
        }}>
          ASTROVOX CHAT
        </h3>
        <span style={{
          fontSize: 10,
          color: isOnline ? '#34d399' : '#f87171',
          display: 'flex',
          alignItems: 'center',
          gap: '4px'
        }}>
          <span style={{
            width: 6,
            height: 6,
            borderRadius: '50%',
            backgroundColor: isOnline ? '#34d399' : '#f87171'
          }} />
          {isOnline ? 'ONLINE' : 'OFFLINE'}
        </span>
      </div>

      <div style={{
        flex: 1,
        overflowY: 'auto',
        padding: `${padding}px`,
        display: 'flex',
        flexDirection: 'column',
        gap: 12
      }}>
        {messages.length === 0 && (
          <div style={{
            textAlign: 'center',
            color: '#64748b',
            padding: '40px 20px',
            fontSize: 12
          }}>
            Start a conversation with Astrovox AI
          </div>
        )}
        {messages.map((msg) => (
          <div
            key={msg.id}
            style={{
              alignSelf: msg.role === 'user' ? 'flex-end' : 'flex-start',
              maxWidth: '80%',
              padding: '10px 14px',
              borderRadius,
              backgroundColor: msg.role === 'user' ? '#06b6d4' : '#0f172a',
              color: msg.role === 'user' ? '#02040a' : '#e2e8f0',
              border: msg.role === 'user' ? 'none' : '1px solid #1e293b',
              fontSize,
              lineHeight: 1.5,
              wordWrap: 'break-word'
            }}
          >
            <div>{msg.content}</div>
            <div style={{
              fontSize: 9,
              color: msg.role === 'user' ? 'rgba(0,0,0,0.5)' : '#64748b',
              marginTop: 4,
              textAlign: 'right'
            }}>
              {new Date(msg.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
            </div>
          </div>
        ))}
        {loading && (
          <div style={{
            display: 'flex',
            gap: 6,
            padding: '12px 16px',
            backgroundColor: '#0f172a',
            borderRadius,
            width: 'fit-content'
          }}>
            <span style={{ width: 8, height: 8, borderRadius: '50%', backgroundColor: '#06b6d4', animation: 'bounce 1.4s infinite' }} />
            <span style={{ width: 8, height: 8, borderRadius: '50%', backgroundColor: '#06b6d4', animation: 'bounce 1.4s infinite 0.2s' }} />
            <span style={{ width: 8, height: 8, borderRadius: '50%', backgroundColor: '#06b6d4', animation: 'bounce 1.4s infinite 0.4s' }} />
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      <form
        onSubmit={sendMessage}
        style={{
          padding: '12px 16px',
          borderTop: '1px solid #1e293b',
          backgroundColor: 'rgba(4, 8, 20, 0.9)',
          display: 'flex',
          gap: 8
        }}
      >
        <input
          ref={inputRef}
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Type your message..."
          disabled={loading}
          style={{
            flex: 1,
            padding: isPhone ? '12px 16px' : '10px 14px',
            border: '1px solid #1e293b',
            borderRadius: 24,
            backgroundColor: '#050a18',
            color: '#67e8f9',
            fontSize: isPhone ? 14 : 13,
            fontFamily: 'inherit',
            outline: 'none'
          }}
        />
        <button
          type="submit"
          disabled={loading || !input.trim()}
          style={{
            padding: '0 20px',
            background: '#06b6d4',
            color: '#02040a',
            border: 'none',
            borderRadius: 24,
            cursor: 'pointer',
            fontWeight: 700,
            fontSize: 12,
            fontFamily: 'inherit',
            opacity: loading || !input.trim() ? 0.5 : 1
          }}
        >
          SEND
        </button>
      </form>

      <style>{`
        @keyframes bounce {
          0%, 80%, 100% { transform: translateY(0); }
          40% { transform: translateY(-8px); }
        }
      `}</style>
    </div>
  )
}
