import { useState, useEffect, useCallback } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { searchOmniscient, getSearchHistory } from '../../services/omniscientService'

export default function OmniscientSearch({ onResultSelect }) {
  const [query, setQuery] = useState('')
  const [results, setResults] = useState([])
  const [isSearching, setIsSearching] = useState(false)
  const [realityMode, setRealityMode] = useState('standard')
  const [searchHistory, setSearchHistory] = useState([])
  const [activeIndex, setActiveIndex] = useState(-1)

  useEffect(() => {
    loadSearchHistory()
  }, [])

  const loadSearchHistory = async () => {
    try {
      const data = await getSearchHistory()
      setSearchHistory(data.history || [])
    } catch (e) {
      console.error('Failed to load search history:', e)
    }
  }

  useEffect(() => {
    if (!query.trim()) {
      setResults([])
      return
    }
    const timer = setTimeout(async () => {
      setIsSearching(true)
      try {
        const data = await searchOmniscient(query, null, 20)
        setResults(data.results || [])
        setActiveIndex(-1)
      } catch (e) {
        console.error('Omniscient search failed:', e)
      } finally {
        setIsSearching(false)
      }
    }, 300)
    return () => clearTimeout(timer)
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
    }
  }, [results, activeIndex, onResultSelect])

  return (
    <div style={{ position: 'relative', width: '100%' }}>
      <div style={{
        display: 'flex',
        alignItems: 'center',
        gap: '8px',
        padding: '10px 14px',
        backgroundColor: 'var(--astrovox-bg)',
        border: '1px solid var(--astrovox-border)',
        borderRadius: 'var(--astrovox-radius-md)',
        transition: 'border-color 0.2s'
      }}>
        <span style={{ color: '#f59e0b', fontSize: '16px' }}>👁️</span>
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Search across all realities, timelines, and data..."
          aria-label="Omniscient search"
          style={{
            flex: 1,
            background: 'transparent',
            border: 'none',
            color: 'var(--astrovox-text)',
            fontSize: '13px',
            outline: 'none',
            fontFamily: 'inherit'
          }}
        />
        <select
          value={realityMode}
          onChange={(e) => setRealityMode(e.target.value)}
          style={{
            background: 'var(--astrovox-surface)',
            border: '1px solid var(--astrovox-border)',
            color: 'var(--astrovox-text)',
            borderRadius: '4px',
            padding: '2px 6px',
            fontSize: '10px',
            cursor: 'pointer'
          }}
        >
          <option value="standard">Standard</option>
          <option value="omniscient">Omniscient</option>
          <option value="transcendent">Transcendent</option>
          <option value="quantum">Quantum</option>
          <option value="holographic">Holographic</option>
        </select>
        {isSearching && <span style={{ color: '#f59e0b', fontSize: '10px' }}>Searching...</span>}
      </div>

      {searchHistory.length > 0 && !query && (
        <div style={{
          position: 'absolute',
          top: '100%',
          left: 0,
          right: 0,
          marginTop: '4px',
          backgroundColor: 'var(--astrovox-bg)',
          border: '1px solid var(--astrovox-border)',
          borderRadius: 'var(--astrovox-radius-md)',
          maxHeight: '200px',
          overflow: 'auto',
          zIndex: 1000
        }}>
          <div style={{ padding: '8px 12px', fontSize: '10px', color: '#64748b', textTransform: 'uppercase', letterSpacing: '1px' }}>
            Recent Searches
          </div>
          {searchHistory.slice(0, 10).map((item, idx) => (
            <div
              key={idx}
              onClick={() => { setQuery(item.query); loadSearchHistory() }}
              style={{
                padding: '6px 12px',
                cursor: 'pointer',
                fontSize: '12px',
                color: 'var(--astrovox-text)',
                borderBottom: '1px solid var(--astrovox-border)'
              }}
            >
              {item.query}
            </div>
          ))}
        </div>
      )}

      {results.length > 0 && (
        <div style={{
          position: 'absolute',
          top: '100%',
          left: 0,
          right: 0,
          marginTop: '4px',
          backgroundColor: 'var(--astrovox-bg)',
          border: '1px solid var(--astrovox-border)',
          borderRadius: 'var(--astrovox-radius-md)',
          maxHeight: '400px',
          overflow: 'auto',
          zIndex: 1000
        }}>
          <AnimatePresence>
            {results.map((result, idx) => (
              <motion.div
                key={result.result_id}
                initial={{ opacity: 0, y: -5 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0 }}
                onClick={() => onResultSelect?.(result)}
                style={{
                  padding: '10px 14px',
                  cursor: 'pointer',
                  borderBottom: '1px solid var(--astrovox-border)',
                  backgroundColor: idx === activeIndex ? 'rgba(245,158,11,0.1)' : 'transparent',
                  transition: 'background-color 0.15s'
                }}
              >
                <div style={{ fontSize: '13px', color: 'var(--astrovox-text)', marginBottom: '2px' }}>
                  {result.content}
                </div>
                <div style={{ display: 'flex', gap: '8px', fontSize: '10px', color: '#64748b' }}>
                  <span>Score: {(result.score * 100).toFixed(1)}%</span>
                  <span>Source: {result.source}</span>
                  {result.reality_layer > 0 && <span>Layer: {result.reality_layer}</span>}
                </div>
              </motion.div>
            ))}
          </AnimatePresence>
        </div>
      )}
    </div>
  )
}
