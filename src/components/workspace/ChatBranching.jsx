import { useState, useCallback } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import Icon from '../../design/Iconography'

export default function ChatBranching({ messages, activeBranch, onBranchSelect, onCreateBranch }) {
  const [selectedMessageId, setSelectedMessageId] = useState(null)

  const handleCreateBranch = useCallback((messageId) => {
    setSelectedMessageId(messageId)
    onCreateBranch?.(messageId)
  }, [onCreateBranch])

  const branchPoints = messages.filter(m => m.role === 'assistant')

  return (
    <div
      style={{
        padding: '12px',
        backgroundColor: 'var(--astrovox-surface)',
        border: '1px solid var(--astrovox-border)',
        borderRadius: 'var(--astrovox-radius-lg)'
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '12px' }}>
        <Icon name="branch" size={18} style={{ color: 'var(--astrovox-primary)' }} />
        <span style={{ fontSize: '13px', fontWeight: '600', color: 'var(--astrovox-text)' }}>
          Conversation Branches
        </span>
      </div>

      {branchPoints.length === 0 ? (
        <div style={{ padding: '16px', textAlign: 'center', color: 'var(--astrovox-text-muted)', fontSize: '12px' }}>
          No branches yet. Hover over assistant messages to create branches.
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
          {branchPoints.map((msg, index) => (
            <motion.div
              key={msg.id}
              initial={{ opacity: 0, x: -10 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: index * 0.05 }}
              style={{
                padding: '10px 12px',
                backgroundColor: 'var(--astrovox-surface-hover)',
                border: '1px solid var(--astrovox-border)',
                borderRadius: 'var(--astrovox-radius-md)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                gap: '8px'
              }}
            >
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{
                  fontSize: '11px',
                  fontWeight: '600',
                  color: 'var(--astrovox-accent)',
                  marginBottom: '2px',
                  textTransform: 'uppercase',
                  letterSpacing: '0.5px'
                }}>
                  Response {index + 1}
                </div>
                <div style={{
                  fontSize: '12px',
                  color: 'var(--astrovox-text)',
                  overflow: 'hidden',
                  textOverflow: 'ellipsis',
                  whiteSpace: 'nowrap'
                }}>
                  {msg.content.slice(0, 80)}...
                </div>
              </div>
              <div style={{ display: 'flex', gap: '4px', flexShrink: 0 }}>
                <button
                  onClick={() => handleCreateBranch(msg.id)}
                  style={{
                    padding: '4px 8px',
                    backgroundColor: 'var(--astrovox-primary)',
                    color: 'var(--astrovox-bg)',
                    border: 'none',
                    borderRadius: 'var(--astrovox-radius-sm)',
                    cursor: 'pointer',
                    fontSize: '10px',
                    fontFamily: 'inherit',
                    fontWeight: '600'
                  }}
                >
                  Branch
                </button>
                <button
                  onClick={() => onBranchSelect?.(msg.id)}
                  style={{
                    padding: '4px 8px',
                    backgroundColor: 'transparent',
                    color: 'var(--astrovox-text-muted)',
                    border: '1px solid var(--astrovox-border)',
                    borderRadius: 'var(--astrovox-radius-sm)',
                    cursor: 'pointer',
                    fontSize: '10px',
                    fontFamily: 'inherit'
                  }}
                >
                  View
                </button>
              </div>
            </motion.div>
          ))}
        </div>
      )}
    </div>
  )
}
