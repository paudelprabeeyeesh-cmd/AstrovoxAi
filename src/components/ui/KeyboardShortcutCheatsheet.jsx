import React, { useState, useMemo } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { A11Y_SPECS } from '../../design/AccessibilitySpecs'
import Icon from '../../design/Iconography.jsx'

const CATEGORIES = {
  navigation: 'Navigation',
  editing: 'Editing',
  actions: 'Actions',
  accessibility: 'Accessibility'
}

const SHORTCUT_CATEGORIES = {
  sendMessage: 'editing',
  newMessage: 'navigation',
  search: 'navigation',
  toggleTheme: 'actions',
  focusInput: 'editing',
  help: 'accessibility',
  escape: 'accessibility'
}

export function KeyboardShortcutCheatsheet({ isOpen, onClose }) {
  const [filter, setFilter] = useState('all')
  const [searchQuery, setSearchQuery] = useState('')

  const shortcuts = useMemo(() => {
    const all = Object.entries(A11Y_SPECS.KEYBOARD_SHORTCUTS || {}).map(([id, shortcut]) => ({
      id,
      ...shortcut,
      category: SHORTCUT_CATEGORIES[id] || 'actions'
    }))

    let filtered = all
    if (filter !== 'all') {
      filtered = filtered.filter(s => s.category === filter)
    }
    if (searchQuery) {
      filtered = filtered.filter(s =>
        (s.description || '').toLowerCase().includes(searchQuery.toLowerCase()) ||
        s.id.toLowerCase().includes(searchQuery.toLowerCase())
      )
    }
    return filtered
  }, [filter, searchQuery])

  return (
    <AnimatePresence>
      {isOpen && (
        <div style={{ position: 'fixed', inset: 0, zIndex: 9997 }}>
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
            style={{
              position: 'absolute',
              inset: 0,
              backgroundColor: 'rgba(0, 0, 0, 0.7)',
              backdropFilter: 'blur(4px)'
            }}
          />
          <div
            style={{
              position: 'relative',
              zIndex: 1,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              padding: '20px',
              minHeight: '100vh'
            }}
          >
            <motion.div
              initial={{ opacity: 0, scale: 0.95, y: 10 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.95, y: 10 }}
              style={{
                backgroundColor: 'var(--astrovox-surface)',
                border: '1px solid var(--astrovox-border)',
                borderRadius: '16px',
                width: '100%',
                maxWidth: '640px',
                maxHeight: '80vh',
                display: 'flex',
                flexDirection: 'column',
                boxShadow: '0 24px 80px rgba(0,0,0,0.5)'
              }}
            >
              <div style={{
                padding: '20px 24px',
                borderBottom: '1px solid var(--astrovox-border)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between'
              }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                  <Icon name="keyboard" size={20} />
                  <h2 style={{ margin: 0, fontSize: '16px', fontWeight: '600' }}>
                    Keyboard Shortcuts
                  </h2>
                </div>
                <button
                  onClick={onClose}
                  style={{
                    background: 'transparent',
                    border: 'none',
                    color: 'var(--astrovox-text-muted)',
                    cursor: 'pointer',
                    display: 'flex'
                  }}
                  aria-label="Close"
                >
                  <Icon name="x" size={18} />
                </button>
              </div>

              <div style={{ padding: '16px 24px', borderBottom: '1px solid var(--astrovox-border)' }}>
                <input
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  placeholder="Search shortcuts..."
                  aria-label="Search shortcuts"
                  style={{
                    width: '100%',
                    padding: '8px 12px',
                    backgroundColor: 'var(--astrovox-bg)',
                    border: '1px solid var(--astrovox-border)',
                    borderRadius: '8px',
                    color: 'var(--astrovox-text)',
                    fontSize: '13px',
                    fontFamily: 'inherit',
                    outline: 'none',
                    boxSizing: 'border-box'
                  }}
                />
                <div style={{ display: 'flex', gap: '8px', marginTop: '12px', flexWrap: 'wrap' }}>
                  <FilterButton active={filter === 'all'} onClick={() => setFilter('all')}>All</FilterButton>
                  {Object.entries(CATEGORIES).map(([key, label]) => (
                    <FilterButton key={key} active={filter === key} onClick={() => setFilter(key)}>
                      {label}
                    </FilterButton>
                  ))}
                </div>
              </div>

              <div style={{ overflowY: 'auto', padding: '16px 24px' }}>
                {shortcuts.length === 0 ? (
                  <div style={{ textAlign: 'center', padding: '24px', color: 'var(--astrovox-text-muted)', fontSize: '13px' }}>
                    No shortcuts found
                  </div>
                ) : (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                    {shortcuts.map(s => (
                      <div key={s.id} style={{
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'space-between',
                        padding: '8px 12px',
                        borderRadius: '6px'
                      }}>
                        <span style={{ fontSize: '13px', color: 'var(--astrovox-text)' }}>
                          {s.description}
                        </span>
                        <div style={{ display: 'flex', gap: '4px' }}>
                          {(s.keys || []).map((key, i) => (
                            <kbd key={i} style={{
                              padding: '2px 8px',
                              backgroundColor: 'var(--astrovox-bg)',
                              border: '1px solid var(--astrovox-border)',
                              borderRadius: '4px',
                              fontSize: '11px',
                              color: 'var(--astrovox-text-muted)',
                              fontFamily: 'monospace'
                            }}>
                              {key}
                            </kbd>
                          ))}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </motion.div>
          </div>
        </div>
      )}
    </AnimatePresence>
  )
}

function FilterButton({ active, onClick, children }) {
  return (
    <button
      onClick={onClick}
      style={{
        padding: '4px 12px',
        backgroundColor: active ? 'var(--astrovox-primary)' : 'transparent',
        border: `1px solid ${active ? 'var(--astrovox-primary)' : 'var(--astrovox-border)'}`,
        borderRadius: '6px',
        color: active ? 'var(--astrovox-bg)' : 'var(--astrovox-text-muted)',
        cursor: 'pointer',
        fontSize: '12px',
        fontFamily: 'inherit'
      }}
    >
      {children}
    </button>
  )
}
