import React, { useState, useEffect, useRef, useCallback } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { useKeyboardShortcuts } from './KeyboardShortcuts'
import Icon from '../../design/Iconography.jsx'
import { useReducedMotion } from '../../design/DesignTokens.js'
import { useA11y } from './A11yProvider'

export function CommandPalette({ isOpen, onClose, onSelect, commands = [] }) {
  const [query, setQuery] = useState('')
  const [selectedIndex, setSelectedIndex] = useState(0)
  const inputRef = useRef(null)
  const listRef = useRef(null)
  const { announce } = useA11y()
  const reducedMotion = useReducedMotion()

  const allCommands = [
    { id: 'new-chat', label: 'New conversation', icon: 'chat', shortcut: ['N'], category: 'navigation', action: () => {} },
    { id: 'search', label: 'Search conversations', icon: 'search', shortcut: ['K'], category: 'navigation', action: () => {} },
    { id: 'settings', label: 'Open settings', icon: 'settings', shortcut: [',', 'Shift'], category: 'actions', action: () => {} },
    { id: 'theme', label: 'Toggle theme', icon: 'palette', shortcut: ['T'], category: 'actions', action: () => {} },
    { id: 'help', label: 'Keyboard shortcuts', icon: 'keyboard', shortcut: ['?'], category: 'accessibility', action: () => {} },
    { id: 'logout', label: 'Sign out', icon: 'x', shortcut: ['Q'], category: 'actions', action: () => {} },
    ...commands
  ]

  const filtered = allCommands.filter(cmd =>
    cmd.label.toLowerCase().includes(query.toLowerCase()) ||
    (cmd.category && cmd.category.toLowerCase().includes(query.toLowerCase()))
  )

  useEffect(() => {
    if (isOpen) {
      setQuery('')
      setSelectedIndex(0)
      inputRef.current?.focus()
    }
  }, [isOpen])

  useEffect(() => {
    if (filtered.length === 0) return
    setSelectedIndex(prev => Math.min(prev, filtered.length - 1))
  }, [filtered.length])

  const handleKeyDown = useCallback((e) => {
    if (e.key === 'ArrowDown') {
      e.preventDefault()
      setSelectedIndex(i => {
        const next = (i + 1) % filtered.length
        return next
      })
    } else if (e.key === 'ArrowUp') {
      e.preventDefault()
      setSelectedIndex(i => {
        const next = (i - 1 + filtered.length) % filtered.length
        return next
      })
    } else if (e.key === 'Enter') {
      e.preventDefault()
      const cmd = filtered[selectedIndex]
      if (cmd) {
        cmd.action?.()
        onSelect?.(cmd)
        onClose()
        announce(`Executed: ${cmd.label}`)
      }
    } else if (e.key === 'Escape') {
      onClose()
    }
  }, [filtered, selectedIndex, onClose, onSelect, announce])

  useKeyboardShortcuts({
    'Escape': { keys: ['Escape'], ctrl: false, shift: false, handler: onClose }
  })

  useEffect(() => {
    if (selectedIndex >= 0 && listRef.current) {
      const items = listRef.current.querySelectorAll('[role="option"]')
      items[selectedIndex]?.scrollIntoView({ block: 'nearest' })
      inputRef.current?.setAttribute('aria-activedescendant', `cmd-${filtered[selectedIndex]?.id || ''}`)
    }
  }, [selectedIndex, filtered])

  const selectedCommand = filtered[selectedIndex]

  return (
    <AnimatePresence>
      {isOpen && (
        <div style={{ position: 'fixed', inset: 0, zIndex: 9997 }}>
          <motion.div
            initial={reducedMotion ? { opacity: 0.5 } : { opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={reducedMotion ? { opacity: 0 } : { opacity: 0 }}
            transition={{ duration: reducedMotion ? 0 : 0.2 }}
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
              alignItems: 'flex-start',
              justifyContent: 'center',
              paddingTop: '15vh'
            }}
          >
            <motion.div
              initial={reducedMotion ? {} : { opacity: 0, scale: 0.95, y: -10 }}
              animate={reducedMotion ? {} : { opacity: 1, scale: 1, y: 0 }}
              exit={reducedMotion ? {} : { opacity: 0, scale: 0.95, y: -10 }}
              transition={reducedMotion ? { duration: 0 } : { type: 'spring', damping: 25, stiffness: 300 }}
              style={{
                backgroundColor: 'var(--astrovox-surface)',
                border: '1px solid var(--astrovox-border)',
                borderRadius: '16px',
                width: '100%',
                maxWidth: '560px',
                overflow: 'hidden',
                boxShadow: '0 24px 80px rgba(0,0,0,0.5)'
              }}
              role="dialog"
              aria-modal="true"
              aria-label="Command palette"
            >
              <div style={{
                display: 'flex',
                alignItems: 'center',
                gap: '12px',
                padding: '16px 20px',
                borderBottom: '1px solid var(--astrovox-border)'
              }}>
                <Icon name="search" size={18} color="var(--astrovox-text-muted)" />
                <input
                  ref={inputRef}
                  value={query}
                  onChange={(e) => { setQuery(e.target.value); setSelectedIndex(0) }}
                  onKeyDown={handleKeyDown}
                  placeholder="Type a command or search..."
                  aria-label="Search commands"
                  aria-autocomplete="list"
                  aria-controls="command-list"
                  aria-expanded={isOpen}
                  role="combobox"
                  style={{
                    flex: 1,
                    background: 'transparent',
                    border: 'none',
                    color: 'var(--astrovox-text)',
                    fontSize: '15px',
                    fontFamily: 'inherit',
                    outline: 'none'
                  }}
                />
                <kbd style={{
                  padding: '2px 8px',
                  backgroundColor: 'var(--astrovox-surface-hover)',
                  border: '1px solid var(--astrovox-border)',
                  borderRadius: '4px',
                  fontSize: '11px',
                  color: 'var(--astrovox-text-muted)'
                }}>
                  ESC
                </kbd>
              </div>
              <div
                ref={listRef}
                id="command-list"
                role="listbox"
                aria-label="Commands"
                aria-activedescendant={`cmd-${selectedCommand?.id || ''}`}
                style={{ maxHeight: '400px', overflowY: 'auto', padding: '8px' }}
              >
                {filtered.length === 0 ? (
                  <div style={{ padding: '24px', textAlign: 'center', color: 'var(--astrovox-text-muted)', fontSize: '13px' }}>
                    No commands found
                  </div>
                ) : (
                  filtered.map((cmd, i) => (
                    <button
                      key={cmd.id}
                      id={`cmd-${cmd.id}`}
                      role="option"
                      aria-selected={i === selectedIndex}
                      onClick={() => { cmd.action?.(); onSelect?.(cmd); onClose() }}
                      onMouseEnter={() => setSelectedIndex(i)}
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        gap: '12px',
                        width: '100%',
                        padding: '10px 12px',
                        backgroundColor: i === selectedIndex ? 'var(--astrovox-surface-hover)' : 'transparent',
                        border: 'none',
                        borderRadius: '8px',
                        color: 'var(--astrovox-text)',
                        cursor: 'pointer',
                        fontSize: '13px',
                        fontFamily: 'inherit',
                        textAlign: 'left',
                        transition: 'background-color 0.15s'
                      }}
                    >
                      <div style={{
                        width: '32px',
                        height: '32px',
                        borderRadius: '8px',
                        backgroundColor: 'var(--astrovox-surface-hover)',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        flexShrink: 0
                      }}>
                        <Icon name={cmd.icon} size={16} />
                      </div>
                      <span style={{ flex: 1 }}>{cmd.label}</span>
                      {cmd.shortcut && (
                        <div style={{ display: 'flex', gap: '4px' }}>
                          {cmd.shortcut.map((key, j) => (
                            <kbd key={j} style={{
                              padding: '2px 6px',
                              backgroundColor: 'var(--astrovox-surface-hover)',
                              border: '1px solid var(--astrovox-border)',
                              borderRadius: '4px',
                              fontSize: '10px',
                              color: 'var(--astrovox-text-muted)'
                            }}>
                              {key}
                            </kbd>
                          ))}
                        </div>
                      )}
                    </button>
                  ))
                )}
              </div>
            </motion.div>
          </div>
        </div>
      )}
    </AnimatePresence>
  )
}
