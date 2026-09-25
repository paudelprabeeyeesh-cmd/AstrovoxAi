import { useState, useRef, useCallback, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import Icon from '../../design/Iconography.jsx'

export default function NotificationCenter({ notifications = [] }) {
  const [isOpen, setIsOpen] = useState(false)
  const [filter, setFilter] = useState('all')
  const [internalNotifications, setInternalNotifications] = useState(notifications)
  const unreadCount = internalNotifications.filter(n => !n.read).length

  const filtered = internalNotifications.filter(n => {
    if (filter === 'all') return true
    if (filter === 'unread') return !n.read
    return n.type === filter
  })

  const markAsRead = useCallback((id) => {
    setInternalNotifications(prev => prev.map(n => n.id === id ? { ...n, read: true } : n))
  }, [])

  const markAllAsRead = useCallback(() => {
    setInternalNotifications(prev => prev.map(n => ({ ...n, read: true })))
  }, [])

  return (
    <div style={{ position: 'relative' }}>
      <button
        onClick={() => setIsOpen(!isOpen)}
        style={{
          position: 'relative',
          background: 'transparent',
          border: '1px solid var(--astrovox-border)',
          borderRadius: 'var(--astrovox-radius-md)',
          padding: '8px',
          color: 'var(--astrovox-text)',
          cursor: 'pointer',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center'
        }}
        aria-label={`Notifications ${unreadCount > 0 ? `(${unreadCount} unread)` : ''}`}
        aria-expanded={isOpen}
      >
        <Icon name="bell" size={20} />
        {unreadCount > 0 && (
          <span
            style={{
              position: 'absolute',
              top: '-4px',
              right: '-4px',
              backgroundColor: 'var(--astrovox-error)',
              color: 'white',
              fontSize: '10px',
              fontWeight: 'bold',
              padding: '2px 6px',
              borderRadius: '50%',
              minWidth: '18px',
              textAlign: 'center'
            }}
            aria-hidden="true"
          >
            {unreadCount > 99 ? '99+' : unreadCount}
          </span>
        )}
      </button>

      <AnimatePresence>
        {isOpen && (
          <motion.div
            initial={{ opacity: 0, y: -10, scale: 0.95 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -10, scale: 0.95 }}
            style={{
              position: 'absolute',
              top: 'calc(100% + 8px)',
              right: 0,
              width: '380px',
              maxHeight: '500px',
              backgroundColor: 'var(--astrovox-surface)',
              border: '1px solid var(--astrovox-border)',
              borderRadius: 'var(--astrovox-radius-lg)',
              boxShadow: '0 8px 32px rgba(0,0,0,0.3)',
              overflow: 'hidden',
              zIndex: 1000
            }}
            role="dialog"
            aria-label="Notifications"
          >
            <div style={{
              padding: '12px 16px',
              borderBottom: '1px solid var(--astrovox-border)',
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center'
            }}>
              <h3 style={{ margin: 0, fontSize: '14px', fontWeight: '600' }}>Notifications</h3>
              <div style={{ display: 'flex', gap: '8px' }}>
                <button
                  onClick={markAllAsRead}
                  style={{
                    background: 'transparent',
                    border: 'none',
                    color: 'var(--astrovox-primary)',
                    cursor: 'pointer',
                    fontSize: '11px',
                    fontFamily: 'inherit'
                  }}
                >
                  Mark all read
                </button>
                <select
                  value={filter}
                  onChange={(e) => setFilter(e.target.value)}
                  style={{
                    backgroundColor: 'var(--astrovox-bg)',
                    border: '1px solid var(--astrovox-border)',
                    borderRadius: 'var(--astrovox-radius-sm)',
                    color: 'var(--astrovox-text)',
                    padding: '4px 8px',
                    fontSize: '11px',
                    fontFamily: 'inherit'
                  }}
                  aria-label="Filter notifications"
                >
                  <option value="all">All</option>
                  <option value="unread">Unread</option>
                  <option value="info">Info</option>
                  <option value="warning">Warning</option>
                  <option value="error">Error</option>
                </select>
              </div>
            </div>
            <div
              style={{
                maxHeight: '400px',
                overflowY: 'auto',
                padding: '8px'
              }}
              role="list"
            >
              {filtered.length === 0 ? (
                <div style={{ padding: '24px', textAlign: 'center', color: 'var(--astrovox-text-muted)', fontSize: '13px' }}>
                  No notifications
                </div>
              ) : (
                filtered.map(notification => (
                  <NotificationItem
                    key={notification.id}
                    notification={notification}
                    onMarkAsRead={markAsRead}
                  />
                ))
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}

function NotificationItem({ notification, onMarkAsRead }) {
  const [isExpanded, setIsExpanded] = useState(false)

  useEffect(() => {
    if (!notification.read) {
      const timer = setTimeout(() => onMarkAsRead(notification.id), 5000)
      return () => clearTimeout(timer)
    }
  }, [notification.id, notification.read, onMarkAsRead])

  const typeColors = {
    info: 'var(--astrovox-accent)',
    warning: 'var(--astrovox-warning)',
    error: 'var(--astrovox-error)',
    success: 'var(--astrovox-success)'
  }

  return (
    <div
      style={{
        padding: '12px',
        marginBottom: '4px',
        backgroundColor: notification.read ? 'transparent' : 'var(--astrovox-surface-hover)',
        border: '1px solid var(--astrovox-border)',
        borderRadius: 'var(--astrovox-radius-md)',
        cursor: 'pointer',
        transition: 'background-color 0.2s'
      }}
      onClick={() => setIsExpanded(!isExpanded)}
      onMouseEnter={(e) => { e.currentTarget.style.backgroundColor = 'var(--astrovox-surface-hover)' }}
      onMouseLeave={(e) => { if (notification.read) e.currentTarget.style.backgroundColor = 'transparent' }}
      role="listitem"
      aria-live="polite"
    >
      <div style={{ display: 'flex', alignItems: 'flex-start', gap: '10px' }}>
        <div
          style={{
            width: '8px',
            height: '8px',
            borderRadius: '50%',
            backgroundColor: typeColors[notification.type] || typeColors.info,
            marginTop: '6px',
            flexShrink: 0
          }}
        />
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{
            fontSize: '12px',
            fontWeight: notification.read ? '400' : '600',
            color: 'var(--astrovox-text)',
            marginBottom: '2px'
          }}>
            {notification.title}
          </div>
          <div style={{
            fontSize: '11px',
            color: 'var(--astrovox-text-muted)',
            overflow: 'hidden',
            textOverflow: 'ellipsis',
            whiteSpace: isExpanded ? 'normal' : 'nowrap'
          }}>
            {notification.message}
          </div>
          <div style={{
            fontSize: '10px',
            color: 'var(--astrovox-text-muted)',
            marginTop: '4px',
            opacity: 0.7
          }}>
            {new Date(notification.timestamp).toLocaleString()}
          </div>
        </div>
      </div>
    </div>
  )
}
