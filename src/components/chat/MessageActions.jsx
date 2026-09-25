import { useState, useCallback } from 'react'
import Icon from '../../design/Iconography'

export default function MessageActions({ message, onCopy, onEdit, onDelete, onRetry, onBranch, onShare }) {
  const [showMenu, setShowMenu] = useState(false)

  const handleCopy = useCallback(async () => {
    try {
      await navigator.clipboard.writeText(message.content)
      onCopy?.(message)
    } catch (err) {
      console.error('Failed to copy:', err)
    }
  }, [message.content, onCopy])

  const handleEdit = useCallback(() => {
    onEdit?.(message)
    setShowMenu(false)
  }, [message, onEdit])

  const handleDelete = useCallback(() => {
    if (window.confirm('Delete this message?')) {
      onDelete?.(message)
    }
    setShowMenu(false)
  }, [message, onDelete])

  const handleRetry = useCallback(() => {
    onRetry?.(message)
    setShowMenu(false)
  }, [message, onRetry])

  const handleBranch = useCallback(() => {
    onBranch?.(message)
    setShowMenu(false)
  }, [message, onBranch])

  const handleShare = useCallback(async () => {
    try {
      if (navigator.share) {
        await navigator.share({
          title: 'Astrovox Conversation',
          text: message.content
        })
      } else {
        await navigator.clipboard.writeText(message.content)
      }
      onShare?.(message)
    } catch (err) {
      console.error('Failed to share:', err)
    }
    setShowMenu(false)
  }, [message, onShare])

  return (
    <div
      style={{
        display: 'flex',
        gap: '4px',
        opacity: showMenu ? 1 : 0.5,
        transition: 'opacity 0.2s'
      }}
      onMouseEnter={(e) => { e.currentTarget.style.opacity = '1' }}
      onMouseLeave={(e) => { e.currentTarget.style.opacity = '0.5' }}
    >
      <button
        onClick={handleCopy}
        style={{
          background: 'transparent',
          border: 'none',
          color: 'var(--astrovox-text-muted)',
          cursor: 'pointer',
          padding: '4px',
          borderRadius: 'var(--astrovox-radius-sm)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center'
        }}
        aria-label="Copy message"
        title="Copy"
      >
        <Icon name="copy" size={14} />
      </button>
      {message.role === 'user' && onEdit && (
        <button
          onClick={handleEdit}
          style={{
            background: 'transparent',
            border: 'none',
            color: 'var(--astrovox-text-muted)',
            cursor: 'pointer',
            padding: '4px',
            borderRadius: 'var(--astrovox-radius-sm)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center'
          }}
          aria-label="Edit message"
          title="Edit"
        >
          <Icon name="edit" size={14} />
        </button>
      )}
      {message.role === 'assistant' && onRetry && (
        <button
          onClick={handleRetry}
          style={{
            background: 'transparent',
            border: 'none',
            color: 'var(--astrovox-text-muted)',
            cursor: 'pointer',
            padding: '4px',
            borderRadius: 'var(--astrovox-radius-sm)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center'
          }}
          aria-label="Retry"
          title="Retry"
        >
          <Icon name="refresh" size={14} />
        </button>
      )}
      <button
        onClick={() => setShowMenu(!showMenu)}
        style={{
          background: 'transparent',
          border: 'none',
          color: 'var(--astrovox-text-muted)',
          cursor: 'pointer',
          padding: '4px',
          borderRadius: 'var(--astrovox-radius-sm)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center'
        }}
        aria-label="More actions"
        aria-expanded={showMenu}
        title="More"
      >
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <circle cx="12" cy="12" r="1" />
          <circle cx="19" cy="12" r="1" />
          <circle cx="5" cy="12" r="1" />
        </svg>
      </button>
      {showMenu && (
        <div
          style={{
            position: 'absolute',
            top: '100%',
            right: 0,
            backgroundColor: 'var(--astrovox-surface)',
            border: '1px solid var(--astrovox-border)',
            borderRadius: 'var(--astrovox-radius-md)',
            padding: '4px',
            minWidth: '160px',
            boxShadow: '0 4px 12px rgba(0,0,0,0.2)',
            zIndex: 100
          }}
          role="menu"
        >
          {onBranch && (
            <button
              onClick={handleBranch}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                width: '100%',
                padding: '8px 12px',
                background: 'transparent',
                border: 'none',
                color: 'var(--astrovox-text)',
                cursor: 'pointer',
                fontSize: '12px',
                fontFamily: 'inherit',
                borderRadius: 'var(--astrovox-radius-sm)'
              }}
              role="menuitem"
            >
              <Icon name="branch" size={14} /> Branch from here
            </button>
          )}
          {onShare && (
            <button
              onClick={handleShare}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                width: '100%',
                padding: '8px 12px',
                background: 'transparent',
                border: 'none',
                color: 'var(--astrovox-text)',
                cursor: 'pointer',
                fontSize: '12px',
                fontFamily: 'inherit',
                borderRadius: 'var(--astrovox-radius-sm)'
              }}
              role="menuitem"
            >
              <Icon name="share" size={14} /> Share
            </button>
          )}
          {onDelete && (
            <button
              onClick={handleDelete}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                width: '100%',
                padding: '8px 12px',
                background: 'transparent',
                border: 'none',
                color: 'var(--astrovox-error)',
                cursor: 'pointer',
                fontSize: '12px',
                fontFamily: 'inherit',
                borderRadius: 'var(--astrovox-radius-sm)'
              }}
              role="menuitem"
            >
              <Icon name="trash" size={14} /> Delete
            </button>
          )}
        </div>
      )}
    </div>
  )
}
