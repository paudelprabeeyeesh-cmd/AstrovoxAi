import { useState, useEffect, useRef, useCallback } from 'react'
import { supabase } from './supabase'
import MessageContent from './MessageContent'
import PredictiveText from './components/transcendent/PredictiveText'
import ThoughtPrediction from './components/transcendent/ThoughtPrediction'
import UniversalTranslation from './components/transcendent/UniversalTranslation'
import AnticipatoryUI from './components/transcendent/AnticipatoryUI'
import { mathCompute, getMathOperations } from './services/mathService'

export default function Chat({ session, conversationId, model = 'gpt-4' }) {
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [typing, setTyping] = useState(false)
  const messagesEndRef = useRef(null)
  const lastPromptRef = useRef('')
  const [error, setError] = useState(null)
  const [editingMessageId, setEditingMessageId] = useState(null)
  const [editedContent, setEditedContent] = useState('')
  const [copiedMessageId, setCopiedMessageId] = useState(null)
  const [mathMode, setMathMode] = useState(false)
  const [selectedMathOp, setSelectedMathOp] = useState(null)
  const mathOperations = getMathOperations()

  // Auto-scroll to bottom
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  // Load messages when conversation changes
  useEffect(() => {
    if (conversationId) {
      loadMessages()
    }
  }, [conversationId, loadMessages])

  const loadMessages = useCallback(async () => {
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
  }, [conversationId])

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

      let aiContent = ''
      let aiRole = 'assistant'

      if (mathMode && selectedMathOp) {
        // Call math engine
        try {
          // Parse input as JSON for math engine inputs, or use simple key-value
          let inputs = {}
          try {
            inputs = JSON.parse(userMessage)
          } catch {
            // If not JSON, try to parse as simple key=value pairs or use the whole string
            // For now, pass the raw input as 'expression' for operations that accept it
            inputs = { expression: userMessage }
          }

          const result = await mathCompute(selectedMathOp.topicId, selectedMathOp.operationId, inputs)

          if (result.ok && result.data) {
            const data = result.data
            if (data.error) {
              aiContent = `?? **Math Error**: ${data.error}`
            } else {
              // Format result nicely
              const resultItems = Object.entries(data).filter(([k]) => k !== 'error')
              if (resultItems.length === 1) {
                aiContent = `?? **${selectedMathOp.name} Result**: \`${resultItems[0][1]}\``
              } else {
                aiContent = `?? **${selectedMathOp.name} Result**:\n` +
                  resultItems.map(([k, v]) => `- **${k}**: \`${v}\``).join('\n')
              }
            }
          } else {
            aiContent = `?? **Math Error**: ${result.data?.error || 'Unknown error'}`
          }
        } catch (mathErr) {
          aiContent = `?? **Math Error**: ${mathErr.message}`
        }
      } else {
        // Regular chat mode - call LLM backend
        const { data: { session: currentSession } } = await supabase.auth.getSession()
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
            message: userMessage,
            model: model
          })
        })

        if (!response.ok) {
          const errorData = await response.json()
          throw new Error(errorData.detail || 'Failed to send message')
        }

        const result = await response.json()

        if (result.ai_message) {
          aiContent = result.ai_message.content
        } else {
          aiContent = 'No response from AI'
        }
      }

      // Add AI message
      const aiMsg = {
        id: Date.now() + 1,
        conversation_id: conversationId,
        user_id: session.user.id,
        role: aiRole,
        content: aiContent,
        created_at: new Date().toISOString()
      }
      setMessages(prev => [...prev, aiMsg])

      setTyping(false)
    } catch (err) {
      setError(`Error: ${err.message}`)
      setTyping(false)
      console.error(err)
    }
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
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '12px' }}>
          <h3 style={{
            margin: 0,
            fontSize: '14px',
            color: '#67e8f9',
            letterSpacing: '1px',
            fontWeight: '600'
          }}>
            ?? AI CHAT INTERFACE
          </h3>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <label style={{
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
              fontSize: '12px',
              color: '#cbd5e1',
              cursor: 'pointer'
            }}>
              <input
                type="checkbox"
                checked={mathMode}
                onChange={(e) => setMathMode(e.target.checked)}
                style={{
                  width: '16px',
                  height: '16px',
                  accentColor: '#06b6d4'
                }}
              />
              <span>?? MATH MODE</span>
            </label>
            {mathMode && selectedMathOp && (
              <span style={{
                fontSize: '11px',
                color: '#06b6d4',
                background: 'rgba(6,182,212,0.1)',
                padding: '2px 8px',
                borderRadius: '4px',
                fontFamily: 'monospace'
              }}>
                {selectedMathOp.name}
              </span>
            )}
          </div>
        </div>
        {mathMode && (
          <select
            value={selectedMathOp ? selectedMathOp.topicId : ''}
            onChange={(e) => {
              const op = mathOperations.find(o => o.topicId === e.target.value)
              setSelectedMathOp(op || null)
            }}
            style={{
              marginTop: '12px',
              padding: '8px 12px',
              backgroundColor: '#050a18',
              border: '1px solid #1e293b',
              borderRadius: '6px',
              color: '#67e8f9',
              fontFamily: 'monospace',
              fontSize: '12px',
              width: '100%',
              maxWidth: '400px'
            }}
            aria-label="Select math operation"
          >
            <option value="">-- Select math operation --</option>
            {mathOperations.map(op => (
              <option key={op.topicId} value={op.topicId}>
                [{op.topicId}] {op.name}
              </option>
            ))}
          </select>
        )}
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
            ?? {error}
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
        flexDirection: 'column',
        gap: '8px',
        padding: '16px 20px',
        borderTop: '1px solid #1e293b',
        backgroundColor: 'rgba(4, 8, 20, 0.5)',
        backdropFilter: 'blur(8px)'
      }}>
        <div style={{ display: 'flex', gap: '12px', alignItems: 'flex-end' }}>
          <textarea
            placeholder={mathMode ? 'Enter JSON inputs (e.g., {"a": 2, "b": 3}) or expression...' : 'Type your message...'}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleComposerKeyDown}
            disabled={loading || !conversationId || (mathMode && !selectedMathOp)}
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
            type="submit"
            disabled={loading || !input.trim() || !conversationId || (mathMode && !selectedMathOp)}
            style={{
              padding: '0 24px',
              height: '46px',
              backgroundColor: '#06b6d4',
              color: '#02040a',
              border: 'none',
              borderRadius: '40px',
              cursor: 'pointer',
              fontWeight: '700',
              fontSize: '12px',
              letterSpacing: '0.5px',
              transition: 'all 0.2s',
              opacity: loading || !input.trim() || (mathMode && !selectedMathOp) ? 0.5 : 1
            }}
            onMouseEnter={(e) => {
              if (!loading && input.trim() && (!mathMode || selectedMathOp)) {
                e.target.style.transform = 'scale(1.02)'
                e.target.style.boxShadow = '0 0 20px rgba(6,182,212,0.4)'
              }
            }}
            onMouseLeave={(e) => {
              e.target.style.transform = 'scale(1)'
              e.target.style.boxShadow = 'none'
            }}
          >
            {mathMode ? 'COMPUTE' : 'SEND'}
          </button>
        </div>
        {mathMode && selectedMathOp && (
          <div style={{
            fontSize: '11px',
            color: '#64748b',
            padding: '4px 12px',
            fontFamily: 'monospace'
          }}>
            Topic: {selectedMathOp.topicId} | Operation: {selectedMathOp.operationId} | Input format: JSON object or raw expression
          </div>
        )}
      </form>

      {/* Transcendent overlays */}
      <PredictiveText interface="chat" onSelectSuggestion={(s) => setInput(s.text)} />
      {session && <ThoughtPrediction userId={session.user.id} />}
      {input && <UniversalTranslation text={input} />}
      {conversationId && <AnticipatoryUI userId={session.user.id} interface="chat" context={{ conversationId }} />}

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
