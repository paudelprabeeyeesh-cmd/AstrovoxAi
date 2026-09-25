import { useState, useEffect, useRef, useCallback } from 'react'
import { motion, AnimatePresence } from 'framer-motion'

export default function InfiniteScroll({ streamId = 'default', renderItem, hasMore = true }) {
  const [items, setItems] = useState([])
  const [loading, setLoading] = useState(false)
  const [cursor, setCursor] = useState('0')
  const observerRef = useRef(null)
  const loadMoreRef = useRef(null)

  const loadChunk = useCallback(async () => {
    if (loading || !hasMore) return
    setLoading(true)
    try {
      const res = await fetch(`/omniscient/infinite-scroll/streams/${streamId}/chunk?cursor=${cursor}&limit=30`)
      if (res.ok) {
        const data = await res.json()
        setItems(prev => [...prev, ...data.data])
        setCursor(data.cursor)
        if (!data.has_more) {
          setHasMore(false)
        }
      }
    } catch (e) {
      console.error('Infinite scroll failed:', e)
    } finally {
      setLoading(false)
    }
  }, [cursor, loading, hasMore, streamId])

  const [hasMore, setHasMore] = useState(true)

  useEffect(() => {
    if (streamId) {
      fetch(`/omniscient/infinite-scroll/streams/${streamId}`, { method: 'POST' }).catch(() => {})
      loadChunk()
    }
  }, [streamId])

  useEffect(() => {
    if (observerRef.current) observerRef.current.disconnect()
    observerRef.current = new IntersectionObserver((entries) => {
      if (entries[0].isIntersecting && hasMore && !loading) {
        loadChunk()
      }
    })
    if (loadMoreRef.current) {
      observerRef.current.observe(loadMoreRef.current)
    }
    return () => observerRef.current?.disconnect()
  }, [loadChunk, hasMore, loading])

  return (
    <div style={{
      height: '100%',
      overflowY: 'auto',
      position: 'relative'
    }}>
      <AnimatePresence>
        {items.map((item, idx) => (
          <motion.div
            key={`${streamId}-${idx}`}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: Math.min(idx * 0.02, 0.5) }}
          >
            {renderItem ? renderItem(item, idx) : (
              <div style={{
                padding: '12px 16px',
                borderBottom: '1px solid var(--astrovox-border)',
                fontSize: '13px',
                color: 'var(--astrovox-text)'
              }}>
                {typeof item === 'string' ? item : JSON.stringify(item)}
              </div>
            )}
          </motion.div>
        ))}
      </AnimatePresence>

      <div ref={loadMoreRef} style={{ height: '40px', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        {loading && (
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: '#06b6d4', fontSize: '11px' }}>
            <span style={{
              width: '12px',
              height: '12px',
              border: '2px solid #06b6d4',
              borderTopColor: 'transparent',
              borderRadius: '50%',
              animation: 'spin 0.8s linear infinite'
            }} />
            Loading infinite data...
          </div>
        )}
        {!hasMore && items.length > 0 && (
          <div style={{ fontSize: '10px', color: '#64748b' }}>
            ∞ Endless data reached
          </div>
        )}
      </div>

      <style>{`
        @keyframes spin {
          to { transform: rotate(360deg); }
        }
      `}</style>
    </div>
  )
}
