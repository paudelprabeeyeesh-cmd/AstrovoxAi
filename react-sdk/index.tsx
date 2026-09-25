import React, { useState, useRef, useEffect } from 'react'
import { AstrovoxClient, Message, Conversation } from '@astrovox/sdk'

export interface AstrovoxChatProps {
  apiKey: string
  theme?: 'dark' | 'light' | 'high-contrast'
  model?: string
  enableVoice?: boolean
  enableBranching?: boolean
  enableFileUpload?: boolean
  onMessageSent?: (message: Message) => void
  onMessageReceived?: (message: Message) => void
  onError?: (error: Error) => void
  placeholder?: string
  height?: string | number
  className?: string
}

export function AstrovoxChat({
  apiKey,
  theme = 'dark',
  model = 'gpt-4',
  enableVoice = false,
  enableBranching = false,
  enableFileUpload = true,
  onMessageSent,
  onMessageReceived,
  onError,
  placeholder = 'Type your message...',
  height = '600px',
  className = ''
}: AstrovoxChatProps) {
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [conversation, setConversation] = useState<Conversation | null>(null)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const clientRef = useRef<AstrovoxClient | null>(null)

  useEffect(() => {
    clientRef.current = new AstrovoxClient({ apiKey })
  }, [apiKey])

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const sendMessage = async () => {
    if (!input.trim() || loading) return
    if (!conversation) {
      const newConv = await clientRef.current!.createConversation({ model })
      setConversation(newConv)
    }

    const userMessage: Message = { role: 'user', content: input, timestamp: new Date().toISOString() }
    setMessages(prev => [...prev, userMessage])
    onMessageSent?.(userMessage)
    setInput('')
    setLoading(true)

    try {
      const response = await clientRef.current!.sendMessage({
        conversationId: conversation!.id,
        message: input,
        model
      })
      const aiMessage: Message = { role: 'assistant', ...response.ai_message }
      setMessages(prev => [...prev, aiMessage])
      onMessageReceived?.(aiMessage)
    } catch (error) {
      onError?.(error as Error)
    } finally {
      setLoading(false)
    }
  }

  const themeStyles = {
    dark: { background: '#02040a', surface: '#0f172a', border: '#1e293b', text: '#e2e8f0' },
    light: { background: '#ffffff', surface: '#f8fafc', border: '#e2e8f0', text: '#0f172a' },
    'high-contrast': { background: '#000000', surface: '#000000', border: '#ffffff', text: '#ffffff' }
  }[theme]

  return (
    <div
      className={`astrovox-chat ${className}`}
      style={{
        height,
        background: themeStyles.background,
        border: `1px solid ${themeStyles.border}`,
        borderRadius: '12px',
        overflow: 'hidden',
        display: 'flex',
        flexDirection: 'column'
      }}
    >
      <div style={{ padding: '12px 16px', borderBottom: `1px solid ${themeStyles.border}`, background: themeStyles.surface }}>
        <h3 style={{ margin: 0, fontSize: '14px', color: '#67e8f9', letterSpacing: '1px', fontWeight: 600 }}>
          ASTROVOX AI
        </h3>
      </div>
      <div
        style={{
          flex: 1,
          overflowY: 'auto',
          padding: '16px',
          display: 'flex',
          flexDirection: 'column',
          gap: '12px'
        }}
        role="log"
        aria-live="polite"
      >
        {messages.length === 0 && (
          <div style={{ textAlign: 'center', color: theme === 'dark' ? '#64748b' : '#64748b', padding: '40px 20px' }}>
            Start a conversation with Astrovox AI
          </div>
        )}
        {messages.map((msg, i) => (
          <div
            key={i}
            style={{
              alignSelf: msg.role === 'user' ? 'flex-end' : 'flex-start',
              maxWidth: '75%',
              padding: '12px 16px',
              borderRadius: '12px',
              background: msg.role === 'user' ? '#06b6d4' : themeStyles.surface,
              color: msg.role === 'user' ? '#02040a' : themeStyles.text,
              border: msg.role === 'user' ? 'none' : `1px solid ${themeStyles.border}`,
              fontSize: '13px',
              lineHeight: 1.6,
              wordWrap: 'break-word'
            }}
          >
            {msg.content}
          </div>
        ))}
        {loading && (
          <div style={{ display: 'flex', gap: '6px', padding: '12px 16px', background: themeStyles.surface, borderRadius: '12px', width: 'fit-content' }}>
            <span style={{ width: '8px', height: '8px', borderRadius: '50%', background: '#06b6d4', animation: 'bounce 1.4s infinite' }} />
            <span style={{ width: '8px', height: '8px', borderRadius: '50%', background: '#06b6d4', animation: 'bounce 1.4s infinite 0.2s' }} />
            <span style={{ width: '8px', height: '8px', borderRadius: '50%', background: '#06b6d4', animation: 'bounce 1.4s infinite 0.4s' }} />
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>
      <form
        onSubmit={(e) => { e.preventDefault(); sendMessage() }}
        style={{ padding: '12px 16px', borderTop: `1px solid ${themeStyles.border}`, background: themeStyles.surface, display: 'flex', gap: '8px' }}
      >
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder={placeholder}
          disabled={loading}
          style={{
            flex: 1,
            padding: '10px 14px',
            border: `1px solid ${themeStyles.border}`,
            borderRadius: '24px',
            background: themeStyles.background,
            color: themeStyles.text,
            fontSize: '13px',
            fontFamily: 'inherit',
            outline: 'none'
          }}
          aria-label="Message input"
        />
        <button
          type="submit"
          disabled={loading || !input.trim()}
          style={{
            padding: '0 20px',
            background: '#06b6d4',
            color: '#02040a',
            border: 'none',
            borderRadius: '24px',
            cursor: 'pointer',
            fontWeight: 700,
            fontSize: '12px',
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
