import { useState, useEffect } from 'react'
import { supabase } from './supabase'

export default function Sidebar({ session, onSelectConversation, currentConversationId }) {
  const [conversations, setConversations] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  useEffect(() => {
    if (session) {
      loadConversations()
      // Subscribe to real-time updates
      const subscription = supabase
        .channel('conversations')
        .on('postgres_changes', {
          event: '*',
          schema: 'public',
          table: 'conversations',
          filter: `user_id=eq.${session.user.id}`
        }, () => {
          loadConversations()
        })
        .subscribe()

      return () => subscription.unsubscribe()
    }
  }, [session])

  async function loadConversations() {
    try {
      setLoading(true)
      const { data, error: fetchError } = await supabase
        .from('conversations')
        .select('*')
        .eq('user_id', session.user.id)
        .eq('is_deleted', false)
        .order('updated_at', { ascending: false })

      if (fetchError) throw fetchError
      setConversations(data || [])
      setError(null)
    } catch (err) {
      setError(`Failed to load conversations: ${err.message}`)
      console.error(err)
    } finally {
      setLoading(false)
    }
  }

  async function handleNewConversation() {
    try {
      const { data, error: insertError } = await supabase
        .from('conversations')
        .insert([{
          user_id: session.user.id,
          title: 'New Conversation',
          model: 'gpt-4'
        }])
        .select()

      if (insertError) throw insertError
      if (data && data[0]) {
        onSelectConversation(data[0].id)
      }
    } catch (err) {
      setError(`Failed to create conversation: ${err.message}`)
      console.error(err)
    }
  }

  async function handleDeleteConversation(id, e) {
    e.stopPropagation()
    try {
      const { error: updateError } = await supabase
        .from('conversations')
        .update({ is_deleted: true })
        .eq('id', id)

      if (updateError) throw updateError
      setConversations(prev => prev.filter(c => c.id !== id))
    } catch (err) {
      setError(`Failed to delete conversation: ${err.message}`)
      console.error(err)
    }
  }

  return (
    <div style={{
      width: '280px',
      backgroundColor: 'rgba(4, 8, 20, 0.8)',
      borderRight: '1px solid #1e293b',
      display: 'flex',
      flexDirection: 'column',
      height: '100%',
      backdropFilter: 'blur(8px)'
    }}>
      {/* Header */}
      <div style={{
        padding: '16px',
        borderBottom: '1px solid #1e293b',
        backgroundColor: 'rgba(4, 8, 20, 0.5)'
      }}>
        <h2 style={{
          margin: '0 0 12px 0',
          fontSize: '12px',
          color: '#94a3b8',
          letterSpacing: '1px',
          textTransform: 'uppercase'
        }}>
          📋 CONVERSATIONS
        </h2>
        <button
          onClick={handleNewConversation}
          style={{
            width: '100%',
            padding: '10px',
            backgroundColor: '#06b6d4',
            color: '#02040a',
            border: 'none',
            borderRadius: '8px',
            cursor: 'pointer',
            fontWeight: '600',
            fontSize: '12px',
            letterSpacing: '0.5px',
            transition: 'all 0.2s'
          }}
          onMouseEnter={(e) => {
            e.target.style.transform = 'scale(1.02)'
            e.target.style.boxShadow = '0 0 15px rgba(6,182,212,0.4)'
          }}
          onMouseLeave={(e) => {
            e.target.style.transform = 'scale(1)'
            e.target.style.boxShadow = 'none'
          }}
        >
          + NEW CHAT
        </button>
      </div>

      {/* Conversations List */}
      <div style={{
        flex: 1,
        overflowY: 'auto',
        padding: '12px'
      }}>
        {error && (
          <div style={{
            backgroundColor: 'rgba(239, 68, 68, 0.1)',
            border: '1px solid #ef4444',
            borderRadius: '6px',
            padding: '8px',
            fontSize: '11px',
            color: '#f87171',
            marginBottom: '12px'
          }}>
            ⚠️ {error}
          </div>
        )}

        {loading && (
          <div style={{
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            color: '#06b6d4',
            fontSize: '12px',
            padding: '12px'
          }}>
            <span style={{
              display: 'inline-block',
              width: '12px',
              height: '12px',
              border: '2px solid #06b6d4',
              borderTopColor: 'transparent',
              borderRadius: '50%',
              animation: 'spin 0.8s linear infinite'
            }} />
            Loading...
          </div>
        )}

        {conversations.length === 0 && !loading && (
          <div style={{
            textAlign: 'center',
            color: '#64748b',
            fontSize: '12px',
            padding: '20px 12px'
          }}>
            No conversations yet. Create one to start!
          </div>
        )}

        {conversations.map((conv) => (
          <div
            key={conv.id}
            onClick={() => onSelectConversation(conv.id)}
            style={{
              padding: '12px',
              marginBottom: '8px',
              backgroundColor: currentConversationId === conv.id ? '#1e293b' : 'transparent',
              border: currentConversationId === conv.id ? '1px solid #06b6d4' : '1px solid transparent',
              borderRadius: '8px',
              cursor: 'pointer',
              transition: 'all 0.2s',
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center'
            }}
            onMouseEnter={(e) => {
              if (currentConversationId !== conv.id) {
                e.currentTarget.style.backgroundColor = 'rgba(30, 41, 59, 0.5)'
              }
            }}
            onMouseLeave={(e) => {
              if (currentConversationId !== conv.id) {
                e.currentTarget.style.backgroundColor = 'transparent'
              }
            }}
          >
            <div style={{ flex: 1, minWidth: 0 }}>
              <div style={{
                fontSize: '12px',
                color: currentConversationId === conv.id ? '#67e8f9' : '#cbd5e1',
                fontWeight: currentConversationId === conv.id ? '600' : '400',
                whiteSpace: 'nowrap',
                overflow: 'hidden',
                textOverflow: 'ellipsis'
              }}>
                {conv.title}
              </div>
              <div style={{
                fontSize: '10px',
                color: '#64748b',
                marginTop: '4px'
              }}>
                {new Date(conv.updated_at).toLocaleDateString()}
              </div>
            </div>
            <button
              onClick={(e) => handleDeleteConversation(conv.id, e)}
              style={{
                padding: '4px 8px',
                backgroundColor: 'transparent',
                border: '1px solid #334155',
                color: '#94a3b8',
                borderRadius: '4px',
                cursor: 'pointer',
                fontSize: '10px',
                marginLeft: '8px',
                transition: 'all 0.2s'
              }}
              onMouseEnter={(e) => {
                e.target.style.borderColor = '#ef4444'
                e.target.style.color = '#f87171'
              }}
              onMouseLeave={(e) => {
                e.target.style.borderColor = '#334155'
                e.target.style.color = '#94a3b8'
              }}
            >
              ✕
            </button>
          </div>
        ))}
      </div>

      <style>{`
        @keyframes spin {
          to { transform: rotate(360deg); }
        }
      `}</style>
    </div>
  )
}
