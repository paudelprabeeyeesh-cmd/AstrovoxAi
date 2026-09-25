import { useState, useCallback } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import Icon from '../../design/Iconography'

export default function MultiChatTabs({ conversations, activeId, onSelect, onNew, onClose }) {
  const [editingId, setEditingId] = useState(null)
  const [editTitle, setEditTitle] = useState('')

  const handleDoubleClick = useCallback((conv) => {
    setEditingId(conv.id)
    setEditTitle(conv.title)
  }, [])

  const handleSaveTitle = useCallback((id) => {
    if (editTitle.trim()) {
      onNew?.({ ...conversations.find(c => c.id === id), title: editTitle.trim() })
    }
    setEditingId(null)
    setEditTitle('')
  }, [editTitle, conversations, onNew])

  return (
    <div
      style={{
        display: 'flex',
        alignItems: 'center',
        gap: '2px',
        padding: '8px 8px 0',
        backgroundColor: 'var(--astrovox-surface)',
        borderBottom: '1px solid var(--astrovox-border)',
        overflowX: 'auto',
        minHeight: '44px'
      }}
      role="tablist"
      aria-label="Chat tabs"
    >
      <AnimatePresence>
        {conversations.map(conv => (
          <motion.div
            key={conv.id}
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.9 }}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              padding: '6px 12px',
              backgroundColor: activeId === conv.id ? 'var(--astrovox-surface-hover)' : 'transparent',
              border: `1px solid ${activeId === conv.id ? 'var(--astrovox-primary)' : 'transparent'}`,
              borderBottom: activeId === conv.id ? 'none' : '1px solid transparent',
              borderRadius: 'var(--astrovox-radius-md) var(--astrovox-radius-md) 0 0',
              cursor: 'pointer',
              fontSize: '12px',
              fontFamily: 'inherit',
              color: activeId === conv.id ? 'var(--astrovox-text)' : 'var(--astrovox-text-muted)',
              minWidth: '120px',
              maxWidth: '200px',
              position: 'relative'
            }}
            onClick={() => onSelect(conv.id)}
            onDoubleClick={() => handleDoubleClick(conv)}
            role="tab"
            aria-selected={activeId === conv.id}
            aria-label={`Chat: ${conv.title}`}
          >
            {editingId === conv.id ? (
              <input
                autoFocus
                value={editTitle}
                onChange={(e) => setEditTitle(e.target.value)}
                onBlur={() => handleSaveTitle(conv.id)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter') handleSaveTitle(conv.id)
                  if (e.key === 'Escape') setEditingId(null)
                }}
                style={{
                  background: 'transparent',
                  border: 'none',
                  borderBottom: '1px solid var(--astrovox-primary)',
                  color: 'var(--astrovox-text)',
                  fontSize: '12px',
                  fontFamily: 'inherit',
                  width: '100%',
                  outline: 'none'
                }}
              />
            ) : (
              <>
                <span
                  style={{
                    overflow: 'hidden',
                    textOverflow: 'ellipsis',
                    whiteSpace: 'nowrap',
                    flex: 1
                  }}
                >
                  {conv.title}
                </span>
                <button
                  onClick={(e) => { e.stopPropagation(); onClose?.(conv.id) }}
                  style={{
                    background: 'transparent',
                    border: 'none',
                    color: 'var(--astrovox-text-muted)',
                    cursor: 'pointer',
                    padding: '2px',
                    borderRadius: 'var(--astrovox-radius-sm)',
                    display: 'flex',
                    alignItems: 'center',
                    flexShrink: 0
                  }}
                  aria-label={`Close ${conv.title}`}
                >
                  <Icon name="x" size={12} />
                </button>
              </>
            )}
          </motion.div>
        ))}
      </AnimatePresence>
      <button
        onClick={onNew}
        style={{
          padding: '6px 12px',
          backgroundColor: 'transparent',
          border: '1px dashed var(--astrovox-border)',
          borderRadius: 'var(--astrovox-radius-md)',
          color: 'var(--astrovox-text-muted)',
          cursor: 'pointer',
          fontSize: '16px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          flexShrink: 0
        }}
        aria-label="New chat tab"
      >
        <Icon name="plus" size={16} />
      </button>
    </div>
  )
}
