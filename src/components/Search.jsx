import { useState, useCallback, useEffect, useRef } from 'react'
import { motion } from 'framer-motion'
import Icon from '../design/Iconography'

export default function Search({ onResultSelect, placeholder = 'Search conversations, messages, files...' }) {
  const [query, setQuery] = useState('')
  const [results, setResults] = useState([])
  const [isSearching, setIsSearching] = useState(false)
  const [activeIndex, setActiveIndex] = useState(-1)
  const inputRef = useRef(null)
  const debounceRef = useRef(null)

  useEffect(() => {
    if (debounceRef.current) clearTimeout(debounceRef.current)
    if (!query.trim()) {
      setResults([])
      return
    }

    debounceRef.current = setTimeout(async () => {
      setIsSearching(true)
      try {
        const res = await fetch(`/api/search?q=${encodeURIComponent(query)}&limit=20`)
        if (res.ok) {
          const data = await res.json()
          setResults(data.results || [])
          setActiveIndex(-1)
        }
      } catch (e) {
        console.error('Search failed:', e)
      } finally {
        setIsSearching(false)
      }
    }, 300)

    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current)
    }
  }, [query])

  const handleKeyDown = useCallback((e) => {
    if (e.key === 'ArrowDown') {
      e.preventDefault()
      setActiveIndex(prev => Math.min(prev + 1, results.length - 1))
    } else if (e.key === 'ArrowUp') {
      e.preventDefault()
      setActiveIndex(prev => Math.max(prev - 1, -1))
    } else if (e.key === 'Enter' && activeIndex >= 0) {
      e.preventDefault()
      onResultSelect?.(results[activeIndex])
    } else if (e.key === 'Escape') {
      setQuery('')
      setResults([])
      inputRef.current?.blur()
    }
  }, [results, activeIndex, onResultSelect])

  return (
    <div style={{ position: 'relative', width: '100%' }}>
      <div style={{
        display: 'flex',
        alignItems: 'center',
        gap: '8px',
        padding: '8px 12px',
        backgroundColor: 'var(--astrovox-bg)',
        border: '1px solid var(--astrovox-border)',
        borderRadius: 'var(--astrovox-radius-md)',
        transition: 'border-color 0.2s'
      }}>
        <Icon name="search" size={16} style={{ color: 'var(--astrovox-text-muted)', flexShrink: 0 }} />
        <input
          ref={inputRef}
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={placeholder}
          aria-label="Search"
          style={{
            flex: 1,
            background: 'transparent',
            border: 'none',
            outline: 'none',
            color: 'var(--astrovox-text)',
            fontSize: '13px',
            fontFamily: 'inherit'
          }}
        />
        {isSearching && (
          <div style={{ width: '14px', height: '14px', border: '2px solid var(--astrovox-border)', borderTopColor: 'var(--astrovox-primary)', borderRadius: '50%', animation: 'spin 0.6s linear infinite' }} />
        )}
        {query && (
          <button
            onClick={() => { setQuery(''); setResults([]) }}
            aria-label="Clear search"
            style={{ background: 'none', border: 'none', color: 'var(--astrovox-text-muted)', cursor: 'pointer', padding: '2px' }}
          >
            <Icon name="x" size={14} />
          </button>
        )}
      </div>

      {results.length > 0 && (
        <motion.div
          initial={{ opacity: 0, y: -4 }}
          animate={{ opacity: 1, y: 0 }}
          style={{
            position: 'absolute',
            top: '100%',
            left: 0,
            right: 0,
            marginTop: '4px',
            backgroundColor: 'var(--astrovox-surface)',
            border: '1px solid var(--astrovox-border)',
            borderRadius: 'var(--astrovox-radius-md)',
            maxHeight: '320px',
            overflowY: 'auto',
            zIndex: 1000,
            boxShadow: '0 8px 24px rgba(0,0,0,0.4)'
          }}
        >
          {results.map((result, idx) => (
            <button
              key={result.id || idx}
              onMouseEnter={() => setActiveIndex(idx)}
              onClick={() => onResultSelect?.(result)}
              style={{
                display: 'flex',
                alignItems: 'flex-start',
                gap: '10px',
                width: '100%',
                padding: '10px 12px',
                background: idx === activeIndex ? 'var(--astrovox-surface-hover)' : 'transparent',
                border: 'none',
                borderBottom: idx < results.length - 1 ? '1px solid var(--astrovox-border)' : 'none',
                color: 'var(--astrovox-text)',
                cursor: 'pointer',
                textAlign: 'left',
                fontFamily: 'inherit'
              }}
            >
              <Icon name={result.type === 'conversation' ? 'chat' : result.type === 'message' ? 'message' : 'file'} size={16} style={{ color: 'var(--astrovox-primary)', marginTop: '2px', flexShrink: 0 }} />
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ fontSize: '13px', fontWeight: '500', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{result.title}</div>
                <div style={{ fontSize: '11px', color: 'var(--astrovox-text-muted)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis', marginTop: '2px' }}>{result.snippet}</div>
              </div>
              {result.type && (
                <span style={{ fontSize: '10px', color: 'var(--astrovox-text-muted)', textTransform: 'uppercase', letterSpacing: '0.5px', flexShrink: 0 }}>{result.type}</span>
              )}
            </button>
          ))}
        </motion.div>
      )}
    </div>
  )
}
