import { useState, useEffect, useCallback } from 'react'
import { supabase } from './supabase'

export default function MemoryPanel({ session }) {
  const [memory, setMemory] = useState([])
  const [loading, setLoading] = useState(false)
  const [newMemory, setNewMemory] = useState('')
  const [error, setError] = useState(null)

  useEffect(() => {
    if (session) {
      loadMemory()
    }
  }, [session, loadMemory])

  const loadMemory = useCallback(async () => {
    try {
      setLoading(true)
      const { data, error: fetchError } = await supabase
        .from('ai_memory')
        .select('*')
        .eq('user_id', session.user.id)
        .order('importance', { ascending: false })
        .order('created_at', { ascending: false })
        .limit(10)

      if (fetchError) throw fetchError
      setMemory(data || [])
      setError(null)
    } catch (err) {
      setError(`Failed to load memory: ${err.message}`)
      console.error(err)
    } finally {
      setLoading(false)
    }
  }, [session.user.id])

  async function handleSaveMemory(e) {
    e.preventDefault()
    if (!newMemory.trim()) return

    try {
      const { data, error: insertError } = await supabase
        .from('ai_memory')
        .insert([{
          user_id: session.user.id,
          content: newMemory.trim(),
          importance: 1
        }])
        .select()

      if (insertError) throw insertError
      
      setMemory(prev => [data[0], ...prev])
      setNewMemory('')
      setError(null)
    } catch (err) {
      setError(`Failed to save memory: ${err.message}`)
      console.error(err)
    }
  }

  async function handleDeleteMemory(id) {
    try {
      const { error: deleteError } = await supabase
        .from('ai_memory')
        .delete()
        .eq('id', id)

      if (deleteError) throw deleteError
      setMemory(prev => prev.filter(m => m.id !== id))
    } catch (err) {
      setError(`Failed to delete memory: ${err.message}`)
      console.error(err)
    }
  }

  const getImportanceColor = (importance) => {
    if (importance >= 3) return '#ef4444'
    if (importance === 2) return '#eab308'
    return '#34d399'
  }

  return (
    <div style={{
      backgroundColor: '#040814',
      border: '1px solid #1e293b',
      borderRadius: '12px',
      padding: '16px',
      fontFamily: 'monospace'
    }}>
      <h3 style={{
        margin: '0 0 12px 0',
        fontSize: '12px',
        color: '#94a3b8',
        letterSpacing: '1px',
        textTransform: 'uppercase'
      }}>
        🧠 AI MEMORY BANK
      </h3>

      {/* Add Memory Form */}
      <form onSubmit={handleSaveMemory} style={{
        display: 'flex',
        gap: '8px',
        marginBottom: '12px'
      }}>
        <input
          type="text"
          placeholder="Save important info..."
          value={newMemory}
          onChange={(e) => setNewMemory(e.target.value)}
          style={{
            flex: 1,
            padding: '8px 12px',
            borderRadius: '6px',
            backgroundColor: '#050a18',
            border: '1px solid #1e293b',
            color: '#67e8f9',
            fontFamily: 'monospace',
            fontSize: '11px',
            outline: 'none'
          }}
        />
        <button
          type="submit"
          disabled={!newMemory.trim()}
          style={{
            padding: '8px 12px',
            backgroundColor: '#06b6d4',
            color: '#02040a',
            border: 'none',
            borderRadius: '6px',
            cursor: 'pointer',
            fontWeight: '600',
            fontSize: '10px',
            opacity: newMemory.trim() ? 1 : 0.5
          }}
        >
          SAVE
        </button>
      </form>

      {error && (
        <div style={{
          backgroundColor: 'rgba(239, 68, 68, 0.1)',
          border: '1px solid #ef4444',
          borderRadius: '6px',
          padding: '8px',
          fontSize: '10px',
          color: '#f87171',
          marginBottom: '12px'
        }}>
          ⚠️ {error}
        </div>
      )}

      {/* Memory List */}
      <div style={{
        maxHeight: '200px',
        overflowY: 'auto',
        display: 'flex',
        flexDirection: 'column',
        gap: '8px'
      }}>
        {loading && (
          <div style={{
            color: '#06b6d4',
            fontSize: '11px'
          }}>
            Loading memory...
          </div>
        )}

        {memory.length === 0 && !loading && (
          <div style={{
            color: '#64748b',
            fontSize: '11px',
            textAlign: 'center',
            padding: '12px'
          }}>
            No memory entries yet
          </div>
        )}

        {memory.map((entry) => (
          <div
            key={entry.id}
            style={{
              backgroundColor: '#02040a',
              border: `1px solid ${getImportanceColor(entry.importance)}`,
              borderRadius: '6px',
              padding: '8px',
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'flex-start',
              gap: '8px'
            }}
          >
            <div style={{ flex: 1, minWidth: 0 }}>
              <div style={{
                fontSize: '10px',
                color: '#cbd5e1',
                wordWrap: 'break-word',
                lineHeight: '1.3'
              }}>
                {entry.content.substring(0, 80)}
                {entry.content.length > 80 ? '...' : ''}
              </div>
              <div style={{
                fontSize: '9px',
                color: '#64748b',
                marginTop: '4px'
              }}>
                {new Date(entry.created_at).toLocaleDateString()}
              </div>
            </div>
            <button
              onClick={() => handleDeleteMemory(entry.id)}
              style={{
                padding: '4px 6px',
                backgroundColor: 'transparent',
                border: '1px solid #334155',
                color: '#94a3b8',
                borderRadius: '4px',
                cursor: 'pointer',
                fontSize: '9px',
                transition: 'all 0.2s',
                flexShrink: 0
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
    </div>
  )
}
