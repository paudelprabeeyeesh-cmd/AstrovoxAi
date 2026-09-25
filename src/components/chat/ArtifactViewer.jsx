import { useState, useRef } from 'react'
import { motion } from 'framer-motion'
import Icon from '../../design/Iconography'

export default function ArtifactViewer({ artifact }) {
  const [isExpanded, setIsExpanded] = useState(false)

  if (!artifact) return null

  const { type = 'code', title = 'Artifact', content = '', language = 'javascript' } = artifact

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
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
          padding: '10px 14px',
          backgroundColor: 'var(--astrovox-surface)',
          borderBottom: '1px solid var(--astrovox-border)',
          cursor: 'pointer'
        }}
        onClick={() => setIsExpanded(!isExpanded)}
        role="button"
        aria-expanded={isExpanded}
        tabIndex={0}
        onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') setIsExpanded(!isExpanded) }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <Icon name="code" size={16} />
          <span style={{ fontSize: '12px', fontWeight: '600', color: 'var(--astrovox-accent)' }}>
            {title}
          </span>
          <span
            style={{
              fontSize: '10px',
              padding: '2px 8px',
              backgroundColor: 'var(--astrovox-primary)',
              color: 'var(--astrovox-bg)',
              borderRadius: 'var(--astrovox-radius-sm)',
              textTransform: 'uppercase',
              fontWeight: '600'
            }}
          >
            {type}
          </span>
        </div>
        <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
          <span style={{ fontSize: '10px', color: 'var(--astrovox-text-muted)' }}>
            {language}
          </span>
          <motion.div
            animate={{ rotate: isExpanded ? 180 : 0 }}
            transition={{ duration: 0.2 }}
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" style={{ color: 'var(--astrovox-text-muted)' }}>
              <polyline points="6 9 12 15 18 9" />
            </svg>
          </motion.div>
        </div>
      </div>
      <AnimatePresence>
        {isExpanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.3 }}
            style={{ overflow: 'hidden' }}
          >
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
              <code>{content}</code>
            </pre>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  )
}

import { AnimatePresence } from 'framer-motion'
