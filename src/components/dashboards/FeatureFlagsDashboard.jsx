import { useState, useMemo } from 'react'
import { motion } from 'framer-motion'
import Icon from '../../design/Iconography'

export default function FeatureFlagsDashboard({ flags, onToggle, onUpdate }) {
  const [filter, setFilter] = useState('all')
  const [searchQuery, setSearchQuery] = useState('')

  const filtered = flags?.filter(f => {
    if (filter === 'all') return true
    if (filter === 'enabled') return f.enabled
    if (filter === 'disabled') return !f.enabled
    return f.environment === filter
  }) || []

  const environments = [...new Set(flags?.map(f => f.environment) || [])]

  return (
    <div style={{ padding: '16px', display: 'flex', flexDirection: 'column', gap: '16px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <h2 style={{ margin: 0, fontSize: '18px', fontWeight: '700', color: 'var(--astrovox-text)', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Icon name="zap" size={22} style={{ color: 'var(--astrovox-warning)' }} />
            Feature Flags
          </h2>
          <p style={{ margin: '4px 0 0', fontSize: '11px', color: 'var(--astrovox-text-muted)' }}>
            Manage feature rollouts and experiments
          </p>
        </div>
        <div style={{ display: 'flex', gap: '8px' }}>
          <input
            type="search"
            placeholder="Search flags..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            style={{ padding: '6px 12px', backgroundColor: 'var(--astrovox-bg)', border: '1px solid var(--astrovox-border)', borderRadius: 'var(--astrovox-radius-md)', color: 'var(--astrovox-text)', fontSize: '12px', fontFamily: 'inherit', width: '200px' }}
          />
        </div>
      </div>

      <div
        style={{
          display: 'flex',
          gap: '4px',
          padding: '4px',
          backgroundColor: 'var(--astrovox-surface)',
          borderRadius: 'var(--astrovox-radius-lg)',
          border: '1px solid var(--astrovox-border)'
        }}
      >
        {['all', 'enabled', 'disabled', ...environments].map(f => (
          <button
            key={f}
            onClick={() => setFilter(f)}
            style={{
              flex: 1,
              padding: '6px 10px',
              backgroundColor: filter === f ? 'var(--astrovox-surface-hover)' : 'transparent',
              border: 'none',
              borderRadius: 'var(--astrovox-radius-md)',
              color: filter === f ? 'var(--astrovox-text)' : 'var(--astrovox-text-muted)',
              cursor: 'pointer',
              fontSize: '11px',
              fontFamily: 'inherit',
              textTransform: 'capitalize'
            }}
          >
            {f}
          </button>
        ))}
      </div>

      <div
        style={{
          backgroundColor: 'var(--astrovox-surface)',
          border: '1px solid var(--astrovox-border)',
          borderRadius: 'var(--astrovox-radius-lg)',
          overflow: 'hidden'
        }}
      >
        {filtered.length === 0 ? (
          <div style={{ padding: '32px', textAlign: 'center', color: 'var(--astrovox-text-muted)', fontSize: '13px' }}>
            No flags match your filter
          </div>
        ) : (
          <div>
            {filtered.map((flag, index) => (
              <motion.div
                key={flag.id}
                initial={{ opacity: 0, y: 5 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: index * 0.03 }}
                style={{
                  padding: '14px 16px',
                  borderBottom: '1px solid var(--astrovox-border)',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '12px'
                }}
              >
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ fontSize: '13px', fontWeight: '600', color: 'var(--astrovox-text)', marginBottom: '2px' }}>
                    {flag.name}
                  </div>
                  <div style={{ fontSize: '11px', color: 'var(--astrovox-text-muted)', marginBottom: '4px' }}>
                    {flag.description}
                  </div>
                  <div style={{ display: 'flex', gap: '6px', alignItems: 'center' }}>
                    <span
                      style={{
                        fontSize: '10px',
                        padding: '2px 6px',
                        borderRadius: 'var(--astrovox-radius-sm)',
                        backgroundColor: flag.environment === 'production' ? 'rgba(239, 68, 68, 0.15)' : 'rgba(6, 182, 212, 0.15)',
                        color: flag.environment === 'production' ? 'var(--astrovox-error)' : 'var(--astrovox-primary)',
                        border: `1px solid ${flag.environment === 'production' ? 'var(--astrovox-error)' : 'var(--astrovox-primary)'}`,
                        textTransform: 'uppercase',
                        fontWeight: '600'
                      }}
                    >
                      {flag.environment}
                    </span>
                    {flag.rollout && (
                      <span style={{ fontSize: '10px', color: 'var(--astrovox-text-muted)' }}>
                        {flag.rollout}% rollout
                      </span>
                    )}
                  </div>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '10px', flexShrink: 0 }}>
                  {flag.rollout !== undefined && (
                    <span style={{ fontSize: '11px', color: 'var(--astrovox-text-muted)', minWidth: '40px', textAlign: 'right' }}>
                      {flag.rollout}%
                    </span>
                  )}
                  <button
                    onClick={() => onToggle?.(flag.id, !flag.enabled)}
                    style={{
                      width: '44px',
                      height: '24px',
                      borderRadius: '12px',
                      backgroundColor: flag.enabled ? 'var(--astrovox-primary)' : 'var(--astrovox-border)',
                      border: 'none',
                      cursor: 'pointer',
                      position: 'relative',
                      transition: 'background-color 0.2s'
                    }}
                    role="switch"
                    aria-checked={flag.enabled}
                    aria-label={`Toggle ${flag.name}`}
                  >
                    <motion.div
                      animate={{ x: flag.enabled ? 20 : 0 }}
                      transition={{ type: 'spring', stiffness: 500, damping: 30 }}
                      style={{
                        width: '18px',
                        height: '18px',
                        borderRadius: '50%',
                        backgroundColor: 'white',
                        position: 'absolute',
                        top: '3px',
                        left: '3px',
                        boxShadow: '0 1px 3px rgba(0,0,0,0.3)'
                      }}
                    />
                  </button>
                </div>
              </motion.div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
