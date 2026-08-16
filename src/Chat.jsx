import { useState, useEffect, useRef } from 'react'
import { supabase } from './supabase'
import MessageContent from './MessageContent'

export default function Chat({ session, conversationId, onConversationChange }) {
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [typing, setTyping] = useState(false)
  const messagesEndRef = useRef(null)
  const abortControllerRef = useRef(null)
  const lastPromptRef = useRef('')
  const [error, setError] = useState(null)
  const [editingMessageId, setEditingMessageId] = useState(null)
  const [editedContent, setEditedContent] = useState('')
  const [copiedMessageId, setCopiedMessageId] = useState(null)

  // Auto-scroll to bottom
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  // Load messages when conversation changes
  useEffect(() => {
    if (conversationId) {
      loadMessages()
    } else {
      setMessages([])
    }
    return () => abortControllerRef.current?.abort()
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
    lastPromptRef.current = userMessage
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

      // Stream tokens through the backend so model credentials remain server-side.
      const apiBase = import.meta.env.VITE_API_URL || '/api'
      abortControllerRef.current = new AbortController()
      const response = await fetch(`${apiBase}/chat/stream`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        signal: abortControllerRef.current.signal,
        body: JSON.stringify({
          conversation_id: conversationId,
          message: userMessage,
          model: 'gpt-4'
        })
      })

      if (!response.ok || !response.body) {
        const errorData = await response.json().catch(() => ({}))
        throw new Error(errorData.detail || 'Failed to start response stream')
      }

      const assistantMessageId = `stream-${Date.now()}`
      setMessages(prev => [...prev, {
        id: assistantMessageId,
        conversation_id: conversationId,
        user_id: session.user.id,
        role: 'assistant',
        content: '',
        created_at: new Date().toISOString()
      }])

      const reader = response.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ''

      while (true) {
        const { done, value } = await reader.read()
        buffer += decoder.decode(value || new Uint8Array(), { stream: !done })

        const events = buffer.split('\n\n')
        buffer = events.pop() || ''
        for (const eventBlock of events) {
          const event = eventBlock.match(/^event: (.+)$/m)?.[1]
          const dataLine = eventBlock.match(/^data: (.+)$/m)?.[1]
          if (!event || !dataLine) continue

          const data = JSON.parse(dataLine)
          if (event === 'token') {
            setMessages(prev => prev.map(message => (
              message.id === assistantMessageId
                ? { ...message, content: message.content + data.content }
                : message
            )))
          }
          if (event === 'error') {
            throw new Error(data.detail || 'The response stream ended unexpectedly')
          }
        }

        if (done) break
      }
    } catch (err) {
      if (err.name === 'AbortError') return
      setError(`Error: ${err.message}`)
      console.error(err)
    } finally {
      abortControllerRef.current = null
      setTyping(false)
    }
  }

  function stopResponse() {
    abortControllerRef.current?.abort()
    setTyping(false)
  }

  function retryLastPrompt() {
    if (!lastPromptRef.current || typing) return
    setInput(lastPromptRef.current)
  }

  async function copyMessage(message) {
    await navigator.clipboard?.writeText(message.content)
    setCopiedMessageId(message.id)
    window.setTimeout(() => setCopiedMessageId(null), 1500)
  }

  async function saveEditedMessage(message) {
    const content = editedContent.trim()
    if (!content || content === message.content) {
      setEditingMessageId(null)
      return
    }

    try {
      const { error: updateError } = await supabase
        .from('messages')
        .update({ content })
        .eq('id', message.id)
        .eq('user_id', session.user.id)

      if (updateError) throw updateError
      setMessages(prev => prev.map(item => item.id === message.id ? { ...item, content } : item))
      setEditingMessageId(null)
    } catch (err) {
      setError(`Unable to edit message: ${err.message}`)
    }
  }

  function handleComposerKeyDown(event) {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault()
      if (!typing && input.trim() && conversationId) handleSendMessage(event)
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
            <button type="button" onClick={retryLastPrompt} style={{ marginLeft: '10px', color: '#67e8f9', background: 'transparent', border: 0, cursor: 'pointer' }}>
              Retry
            </button>
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
              {editingMessageId === msg.id ? (
                <div>
                  <textarea
                    autoFocus
                    value={editedContent}
                    onChange={(event) => setEditedContent(event.target.value)}
                    style={{ width: '100%', minHeight: '72px', boxSizing: 'border-box', resize: 'vertical', background: '#020617', color: '#e2e8f0', border: '1px solid #67e8f9', borderRadius: '6px', padding: '8px', fontFamily: 'inherit' }}
                  />
                  <div style={{ display: 'flex', gap: '8px', marginTop: '8px' }}>
                    <button type="button" onClick={() => saveEditedMessage(msg)} style={{ border: 0, borderRadius: '5px', padding: '5px 8px', background: '#67e8f9', cursor: 'pointer', fontSize: '10px' }}>Save</button>
                    <button type="button" onClick={() => setEditingMessageId(null)} style={{ border: '1px solid #64748b', borderRadius: '5px', padding: '5px 8px', background: 'transparent', color: '#cbd5e1', cursor: 'pointer', fontSize: '10px' }}>Cancel</button>
                  </div>
                </div>
              ) : <MessageContent content={msg.content} />}
              <div style={{
                fontSize: '10px',
                color: msg.role === 'user' ? 'rgba(0,0,0,0.5)' : '#64748b',
                marginTop: '6px'
              }}>
                {new Date(msg.created_at).toLocaleTimeString()}
                <button type="button" onClick={() => copyMessage(msg)} style={{ marginLeft: '8px', border: 0, background: 'transparent', color: 'inherit', cursor: 'pointer', fontSize: '10px' }}>
                  {copiedMessageId === msg.id ? 'Copied' : 'Copy'}
                </button>
                {msg.role === 'user' && editingMessageId !== msg.id && (
                  <button type="button" onClick={() => { setEditedContent(msg.content); setEditingMessageId(msg.id) }} style={{ marginLeft: '8px', border: 0, background: 'transparent', color: 'inherit', cursor: 'pointer', fontSize: '10px' }}>
                    Edit
                  </button>
                )}
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
        <textarea
          placeholder="Type your message..."
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleComposerKeyDown}
          disabled={loading || typing || !conversationId}
          style={{
            flex: 1,
            padding: '12px 16px',
            minHeight: '46px',
            maxHeight: '140px',
            resize: 'vertical',
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
          type={typing ? 'button' : 'submit'}
          onClick={typing ? stopResponse : undefined}
          disabled={loading || (!typing && (!input.trim() || !conversationId))}
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
            if (!loading && !typing && input.trim()) {
              e.target.style.transform = 'scale(1.02)'
              e.target.style.boxShadow = '0 0 20px rgba(6,182,212,0.4)'
            }
          }}
          onMouseLeave={(e) => {
            e.target.style.transform = 'scale(1)'
            e.target.style.boxShadow = 'none'
          }}
        >
          {typing ? 'STOP' : 'SEND'}
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
