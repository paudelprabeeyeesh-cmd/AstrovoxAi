import React from 'react'
import Icon from '../../design/Iconography.jsx'

const ILLUSTRATIONS = {
  chat: (
    <svg viewBox="0 0 120 120" fill="none" style={{ width: '120px', height: '120px' }}>
      <rect x="20" y="25" width="80" height="55" rx="12" stroke="var(--astrovox-border)" strokeWidth="2" />
      <path d="M40 55 L50 65 L65 45" stroke="var(--astrovox-primary)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
      <circle cx="95" cy="30" r="6" fill="var(--astrovox-primary)" opacity="0.2" />
      <circle cx="25" cy="35" r="4" fill="var(--astrovox-secondary)" opacity="0.2" />
    </svg>
  ),
  search: (
    <svg viewBox="0 0 120 120" fill="none" style={{ width: '120px', height: '120px' }}>
      <circle cx="50" cy="50" r="28" stroke="var(--astrovox-border)" strokeWidth="2" />
      <line x1="70" y1="70" x2="90" y2="90" stroke="var(--astrovox-primary)" strokeWidth="2" strokeLinecap="round" />
      <line x1="40" y1="40" x2="60" y2="60" stroke="var(--astrovox-text-muted)" strokeWidth="1.5" strokeLinecap="round" opacity="0.3" />
    </svg>
  ),
  folder: (
    <svg viewBox="0 0 120 120" fill="none" style={{ width: '120px', height: '120px' }}>
      <path d="M25 35 L45 35 L55 45 L95 45 L95 85 L25 85 Z" stroke="var(--astrovox-border)" strokeWidth="2" fill="none" />
      <path d="M25 45 L25 35 L45 35" stroke="var(--astrovox-border)" strokeWidth="2" fill="none" />
      <path d="M40 65 L80 65" stroke="var(--astrovox-text-muted)" strokeWidth="2" strokeLinecap="round" opacity="0.4" />
      <path d="M40 75 L65 75" stroke="var(--astrovox-text-muted)" strokeWidth="2" strokeLinecap="round" opacity="0.4" />
    </svg>
  ),
  error: (
    <svg viewBox="0 0 120 120" fill="none" style={{ width: '120px', height: '120px' }}>
      <circle cx="60" cy="60" r="30" stroke="var(--astrovox-error)" strokeWidth="2" />
      <line x1="50" y1="50" x2="70" y2="70" stroke="var(--astrovox-error)" strokeWidth="2" strokeLinecap="round" />
      <line x1="70" y1="50" x2="50" y2="70" stroke="var(--astrovox-error)" strokeWidth="2" strokeLinecap="round" />
    </svg>
  ),
  default: (
    <svg viewBox="0 0 120 120" fill="none" style={{ width: '120px', height: '120px' }}>
      <rect x="30" y="30" width="60" height="60" rx="12" stroke="var(--astrovox-border)" strokeWidth="2" />
      <line x1="45" y1="50" x2="75" y2="50" stroke="var(--astrovox-text-muted)" strokeWidth="2" strokeLinecap="round" opacity="0.4" />
      <line x1="45" y1="60" x2="65" y2="60" stroke="var(--astrovox-text-muted)" strokeWidth="2" strokeLinecap="round" opacity="0.4" />
      <circle cx="80" cy="75" r="8" fill="var(--astrovox-primary)" opacity="0.15" />
    </svg>
  )
}

export function EmptyState({
  illustration = 'default',
  title = 'Nothing here yet',
  description = 'Get started by creating your first item.',
  action,
  actionLabel
}) {
  return (
    <div style={{
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'center',
      padding: '48px 24px',
      textAlign: 'center',
      minHeight: '300px'
    }}>
      <div style={{ marginBottom: '24px', opacity: 0.8 }}>
        {ILLUSTRATIONS[illustration] || ILLUSTRATIONS.default}
      </div>
      <h3 style={{
        margin: '0 0 8px 0',
        fontSize: '16px',
        fontWeight: '600',
        color: 'var(--astrovox-text)'
      }}>
        {title}
      </h3>
      <p style={{
        margin: '0 0 24px 0',
        fontSize: '13px',
        color: 'var(--astrovox-text-muted)',
        maxWidth: '320px',
        lineHeight: '1.5'
      }}>
        {description}
      </p>
      {action && actionLabel && (
        <button
          onClick={action}
          style={{
            padding: '10px 20px',
            backgroundColor: 'var(--astrovox-primary)',
            color: 'var(--astrovox-bg)',
            border: 'none',
            borderRadius: '8px',
            cursor: 'pointer',
            fontSize: '13px',
            fontWeight: '600'
          }}
        >
          {actionLabel}
        </button>
      )}
    </div>
  )
}
