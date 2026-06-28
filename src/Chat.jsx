import { useState, useEffect, useRef } from 'react'
import { supabase } from './supabase'

export default function Chat({ session, conversationId, onConversationChange }) {
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [typing, setTyping] = useState(false)
  const messagesEndRef = useRef(null)
  const [error, setError] = useState(null)

  // Auto-scroll to bottom
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  // Load messages when conversation changes
  useEffect(() => {
    if (conversationId) {
      loadMessages()
    }
  }, [conversationId])

  async function loadMessages() {
    try {
      setLoading(true)
      const { data, error: fetchError } = await supabase
        .from('messages')
        .select('*')
        .eq('conversation_id', conversationId)
        .order('created_at', { ascending: true })

      if (fetchError) throw fetchError
      setMessages(data || [])
      setError(null)
    } catch (err) {
      setError(`Failed to load messages: ${err.message}`)
      console.error(err)
    } finally {
      setLoading(false)
    }
  }

  async function handleSendMessage(e) {
    e.preventDefault()
    if (!input.trim() || !conversationId) return

    const userMessage = input.trim()
    setInput('')
    setError(null)

    try {
      // Add user message to UI immediately
      const userMsg = {
        id: Date.now(),
        conversation_id: conversationId,
        user_id: session.user.id,
        role: 'user',
        content: userMessage,
        created_at: new Date().toISOString()
      }
      setMessages(prev => [...prev, userMsg])

      // Show typing indicator
      setTyping(true)

      // Get access token
      const { data: { session: currentSession } } = await supabase.auth.getSession()
      const token = currentSession?.access_token

      if (!token) {
        throw new Error('No authentication token available')
      }

      // Send to backend. Set VITE_API_URL at build time for production.
      // The "/api" fallback only works where a proxy routes /api/* to the
      // backend (the Vite dev server, or an nginx/CDN rule in production).
      const apiBase = import.meta.env.VITE_API_URL || '/api'
      const response = await fetch(`${apiBase}/chat/message`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
          conversation_id: conversationId,
          message: userMessage,
          model: 'gpt-4'
        })
      })

      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.detail || 'Failed to send message')
      }

      const result = await response.json()

      // Add AI message
      if (result.ai_message) {
        setMessages(prev => [...prev, {
          ...result.ai_message,
          created_at: new Date(result.ai_message.created_at).toISOString()
        }])
      }

      setTyping(false)
    } catch (err) {
      setError(`Error: ${err.message}`)
      setTyping(false)
      console.error(err)
    }
  }

  return (
    <div style={{
      display: 'flex',
      flexDirection: 'column',
      height: '100%',
      backgroundColor: '#02040a',
      borderRadius: '12px',
      border: '1px solid #1e293b',
      overflow: 'hidden'
    }}>
      {/* Header */}
      <div style={{
        padding: '16px 20px',
        borderBottom: '1px solid #1e293b',
        backgroundColor: 'rgba(4, 8, 20, 0.5)',
        backdropFilter: 'blur(8px)'
      }}>
        <h3 style={{
          margin: 0,
          fontSize: '14px',
          color: '#67e8f9',
          letterSpacing: '1px',
          fontWeight: '600'
        }}>
          🤖 AI CHAT INTERFACE
        </h3>
      </div>

      {/* Messages Container */}
      <div style={{
        flex: 1,
        overflowY: 'auto',
        padding: '20px',
        display: 'flex',
        flexDirection: 'column',
        gap: '12px'
      }}>
        {error && (
          <div style={{
            backgroundColor: 'rgba(239, 68, 68, 0.1)',
            border: '1px solid #ef4444',
            borderRadius: '8px',
            padding: '12px',
            fontSize: '12px',
            color: '#f87171'
          }}>
            ⚠️ {error}
          </div>
        )}

        {loading && (
          <div style={{
            display: 'flex',
            alignItems: 'center',
            gap: '12px',
            color: '#06b6d4',
            fontSize: '13px'
          }}>
            <span style={{
              display: 'inline-block',
              width: '16px',
              height: '16px',
              border: '2px solid #06b6d4',
              borderTopColor: 'transparent',
              borderRadius: '50%',
              animation: 'spin 0.8s linear infinite'
            }} />
            Loading conversation...
          </div>
        )}

        {messages.length === 0 && !loading && (
          <div style={{
            textAlign: 'center',
            color: '#64748b',
            fontSize: '13px',
            padding: '40px 20px'
          }}>
            No messages yet. Start a conversation!
          </div>
        )}

        {messages.map((msg) => (
          <div
            key={msg.id}
            style={{
              display: 'flex',
              justifyContent: msg.role === 'user' ? 'flex-end' : 'flex-start',
              marginBottom: '8px'
            }}
          >
            <div style={{
              maxWidth: '70%',
              padding: '12px 16px',
              borderRadius: '12px',
              backgroundColor: msg.role === 'user' ? '#06b6d4' : '#1e293b',
              color: msg.role === 'user' ? '#02040a' : '#cbd5e1',
              fontSize: '13px',
              lineHeight: '1.5',
              wordWrap: 'break-word'
            }}>
              {msg.content}
              <div style={{
                fontSize: '10px',
                color: msg.role === 'user' ? 'rgba(0,0,0,0.5)' : '#64748b',
                marginTop: '6px'
              }}>
                {new Date(msg.created_at).toLocaleTimeString()}
              </div>
            </div>
          </div>
        ))}

        {typing && (
          <div style={{
            display: 'flex',
            gap: '6px',
            padding: '12px 16px',
            backgroundColor: '#1e293b',
            borderRadius: '12px',
            width: 'fit-content'
          }}>
            <span style={{
              width: '8px',
              height: '8px',
              borderRadius: '50%',
              backgroundColor: '#67e8f9',
              animation: 'bounce 1.4s infinite'
            }} />
            <span style={{
              width: '8px',
              height: '8px',
              borderRadius: '50%',
              backgroundColor: '#67e8f9',
              animation: 'bounce 1.4s infinite 0.2s'
            }} />
            <span style={{
              width: '8px',
              height: '8px',
              borderRadius: '50%',
              backgroundColor: '#67e8f9',
              animation: 'bounce 1.4s infinite 0.4s'
            }} />
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input Area */}
      <form onSubmit={handleSendMessage} style={{
        display: 'flex',
        gap: '12px',
        padding: '16px 20px',
        borderTop: '1px solid #1e293b',
        backgroundColor: 'rgba(4, 8, 20, 0.5)',
        backdropFilter: 'blur(8px)'
      }}>
        <input
          type="text"
          placeholder="Type your message..."
          value={input}
          onChange={(e) => setInput(e.target.value)}
          disabled={loading || !conversationId}
          style={{
            flex: 1,
            padding: '12px 16px',
            borderRadius: '40px',
            backgroundColor: '#050a18',
            border: '1px solid #1e293b',
            color: '#67e8f9',
            fontFamily: 'monospace',
            fontSize: '13px',
            outline: 'none',
            transition: 'border-color 0.2s',
            opacity: loading ? 0.5 : 1
          }}
          onFocus={(e) => e.target.style.borderColor = '#06b6d4'}
          onBlur={(e) => e.target.style.borderColor = '#1e293b'}
        />
        <button
          type="submit"
          disabled={loading || !input.trim() || !conversationId}
          style={{
            padding: '0 24px',
            backgroundColor: '#06b6d4',
            color: '#02040a',
            border: 'none',
            borderRadius: '40px',
            cursor: 'pointer',
            fontWeight: '700',
            fontSize: '12px',
            letterSpacing: '0.5px',
            transition: 'all 0.2s',
            opacity: loading || !input.trim() ? 0.5 : 1
          }}
          onMouseEnter={(e) => {
            if (!loading && input.trim()) {
              e.target.style.transform = 'scale(1.02)'
              e.target.style.boxShadow = '0 0 20px rgba(6,182,212,0.4)'
            }
          }}
          onMouseLeave={(e) => {
            e.target.style.transform = 'scale(1)'
            e.target.style.boxShadow = 'none'
          }}
        >
          SEND
        </button>
      </form>

      <style>{`
        @keyframes spin {
          to { transform: rotate(360deg); }
        }
        @keyframes bounce {
          0%, 80%, 100% { transform: translateY(0); }
          40% { transform: translateY(-8px); }
        }
      `}</style>
    </div>
  )
}
