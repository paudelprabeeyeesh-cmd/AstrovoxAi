import { useState, useEffect, useRef } from 'react'
import Icon from '../../design/Iconography'

export default function CodeBlock({ language, value }) {
  const [copied, setCopied] = useState(false)

  async function copyCode() {
    try {
      await navigator.clipboard.writeText(value)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    } catch (err) {
      console.error('Failed to copy code:', err)
    }
  }

  return (
    <div
      style={{
        marginTop: '12px',
        border: '1px solid var(--astrovox-border)',
        borderRadius: 'var(--astrovox-radius-lg)',
        overflow: 'hidden',
        backgroundColor: 'var(--astrovox-code)'
      }}
    >
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          padding: '8px 12px',
          backgroundColor: 'var(--astrovox-surface)',
          borderBottom: '1px solid var(--astrovox-border)'
        }}
      >
        <span
          style={{
            fontSize: '11px',
            color: 'var(--astrovox-text-muted)',
            fontFamily: 'var(--astrovox-font-mono)',
            textTransform: 'uppercase',
            letterSpacing: '0.5px'
          }}
        >
          {language || 'code'}
        </span>
        <button
          onClick={copyCode}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '4px',
            background: 'transparent',
            border: '1px solid var(--astrovox-border)',
            borderRadius: 'var(--astrovox-radius-sm)',
            padding: '4px 8px',
            color: 'var(--astrovox-text-muted)',
            cursor: 'pointer',
            fontSize: '10px',
            fontFamily: 'inherit'
          }}
          aria-label="Copy code"
        >
          <Icon name="copy" size={12} />
          {copied ? 'Copied' : 'Copy'}
        </button>
      </div>
      <pre
        style={{
          margin: 0,
          padding: '16px',
          overflowX: 'auto',
          fontSize: '12px',
          lineHeight: '1.6',
          color: 'var(--astrovox-code-text)',
          fontFamily: 'var(--astrovox-font-mono)'
        }}
      >
        <code>{value}</code>
      </pre>
    </div>
  )
}
