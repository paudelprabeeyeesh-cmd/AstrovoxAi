import { useState, useCallback } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import Icon from '../../design/Iconography'

export default function SharedConversations({ sharedConversations, onOpen, onUnshare }) {
  const [filter, setFilter] = useState('all')

  const filtered = sharedConversations.filter(conv => {
    if (filter === 'all') return true
    if (filter === 'shared') return conv.shared
    return conv.pending
  })

  const handleUnshare = useCallback((id) => {
    if (window.confirm('Stop sharing this conversation?')) {
      onUnshare?.(id)
    }
  }, [onUnshare])

  return (
    <div
      style={{
        padding: '16px',
        backgroundColor: 'var(--astrovox-surface)',
        border: '1px solid var(--astrovox-border)',
        borderRadius: 'var(--astrovox-radius-lg)'
      }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <Icon name="share" size={18} style={{ color: 'var(--astrovox-primary)' }} />
          <span style={{ fontSize: '13px', fontWeight: '600', color: 'var(--astrovox-text)' }}>
            Shared Conversations
          </span>
        </div>
        <select
          value={filter}
          onChange={(e) => setFilter(e.target.value)}
          style={{
            padding: '4px 8px',
            backgroundColor: 'var(--astrovox-bg)',
            border: '1px solid var(--astrovox-border)',
            borderRadius: 'var(--astrovox-radius-sm)',
            color: 'var(--astrovox-text)',
            fontSize: '11px',
            fontFamily: 'inherit'
          }}
        >
          <option value="all">All</option>
          <option value="shared">Shared</option>
          <option value="pending">Pending</option>
        </select>
      </div>

      {filtered.length === 0 ? (
        <div style={{ padding: '24px', textAlign: 'center', color: 'var(--astrovox-text-muted)', fontSize: '12px' }}>
          <Icon name="share" size={24} style={{ marginBottom: '8px', opacity: 0.5 }} />
          <div>No shared conversations yet</div>
          <div style={{ marginTop: '4px', fontSize: '11px' }}>
            Share conversations with team members to collaborate
          </div>
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
          {filtered.map((conv, index) => (
            <motion.div
              key={conv.id}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: index * 0.05 }}
              style={{
                padding: '12px',
                backgroundColor: 'var(--astrovox-surface-hover)',
                border: '1px solid var(--astrovox-border)',
                borderRadius: 'var(--astrovox-radius-md)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                gap: '12px'
              }}
            >
              <div
                style={{ flex: 1, minWidth: 0, cursor: 'pointer' }}
                onClick={() => onOpen?.(conv.id)}
              >
                <div style={{ fontSize: '12px', fontWeight: '600', color: 'var(--astrovox-text)', marginBottom: '2px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                  {conv.title}
                </div>
                <div style={{ fontSize: '10px', color: 'var(--astrovox-text-muted)', marginBottom: '4px' }}>
                  Shared with: {conv.sharedWith?.map(u => u.name || u.email).join(', ')}
                </div>
                <div style={{ display: 'flex', gap: '6px', alignItems: 'center' }}>
                  <span
                    style={{
                      fontSize: '10px',
                      padding: '2px 6px',
                      borderRadius: 'var(--astrovox-radius-sm)',
                      backgroundColor: conv.shared ? 'rgba(6, 182, 212, 0.15)' : 'rgba(251, 191, 36, 0.15)',
                      color: conv.shared ? 'var(--astrovox-primary)' : 'var(--astrovox-warning)',
                      border: `1px solid ${conv.shared ? 'var(--astrovox-primary)' : 'var(--astrovox-warning)'}`
                    }}
                  >
                    {conv.shared ? 'Active' : 'Pending'}
                  </span>
                  <span style={{ fontSize: '10px', color: 'var(--astrovox-text-muted)' }}>
                    {new Date(conv.sharedAt).toLocaleDateString()}
                  </span>
                </div>
              </div>
              <button
                onClick={() => handleUnshare(conv.id)}
                style={{
                  padding: '4px 8px',
                  backgroundColor: 'transparent',
                  color: 'var(--astrovox-error)',
                  border: '1px solid var(--astrovox-error)',
                  borderRadius: 'var(--astrovox-radius-sm)',
                  cursor: 'pointer',
                  fontSize: '10px',
                  fontFamily: 'inherit',
                  flexShrink: 0
                }}
              >
                Unshare
              </button>
            </motion.div>
          ))}
        </div>
      )}
    </div>
  )
}
