import React, { useState, useEffect, useRef, useCallback } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { useKeyboardShortcuts } from './KeyboardShortcuts'
import Icon from '../design/Iconography'

const COMMANDS = [
  { id: 'new-chat', label: 'New conversation', icon: 'chat', shortcut: ['N'], action: () => {} },
  { id: 'search', label: 'Search conversations', icon: 'search', shortcut: ['K'], action: () => {} },
  { id: 'settings', label: 'Open settings', icon: 'settings', shortcut: [',', 'Shift'], action: () => {} },
  { id: 'theme', label: 'Toggle theme', icon: 'palette', shortcut: ['T'], action: () => {} },
  { id: 'help', label: 'Keyboard shortcuts', icon: 'keyboard', shortcut: ['?'], action: () => {} },
  { id: 'logout', label: 'Sign out', icon: 'x', shortcut: ['Q'], action: () => {} }
]

export function CommandPalette({ isOpen, onClose, onSelect }) {
  const [query, setQuery] = useState('')
  const [selectedIndex, setSelectedIndex] = useState(0)
  const inputRef = useRef(null)
  const listRef = useRef(null)

  const filtered = COMMANDS.filter(cmd =>
    cmd.label.toLowerCase().includes(query.toLowerCase())
  )

  useEffect(() => {
    if (isOpen) {
      setQuery('')
      setSelectedIndex(0)
      inputRef.current?.focus()
    }
  }, [isOpen])

  const handleKeyDown = useCallback((e) => {
    if (e.key === 'ArrowDown') {
      e.preventDefault()
      setSelectedIndex(i => Math.min(i + 1, filtered.length - 1))
    } else if (e.key === 'ArrowUp') {
      e.preventDefault()
      setSelectedIndex(i => Math.max(i - 1, 0))
    } else if (e.key === 'Enter') {
      e.preventDefault()
      const cmd = filtered[selectedIndex]
      if (cmd) {
        cmd.action()
        onSelect?.(cmd)
        onClose()
      }
    }
  }, [filtered, selectedIndex, onClose, onSelect])

  useKeyboardShortcuts({
    'Escape': { keys: ['Escape'], ctrl: false, shift: false, handler: onClose }
  })

  useEffect(() => {
    if (selectedIndex >= 0 && listRef.current) {
      const items = listRef.current.querySelectorAll('[role="option"]')
      items[selectedIndex]?.scrollIntoView({ block: 'nearest' })
    }
  }, [selectedIndex])

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
              alignItems: 'flex-start',
              justifyContent: 'center',
              paddingTop: '15vh'
            }}
          >
            <motion.div
              initial={{ opacity: 0, scale: 0.95, y: -10 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.95, y: -10 }}
              transition={{ type: 'spring', damping: 25, stiffness: 300 }}
              style={{
                backgroundColor: 'var(--astrovox-surface)',
                border: '1px solid var(--astrovox-border)',
                borderRadius: '16px',
                width: '100%',
                maxWidth: '560px',
                overflow: 'hidden',
                boxShadow: '0 24px 80px rgba(0,0,0,0.5)'
              }}
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
                role="listbox"
                aria-label="Commands"
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
                      role="option"
                      aria-selected={i === selectedIndex}
                      onClick={() => { cmd.action(); onSelect?.(cmd); onClose() }}
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
