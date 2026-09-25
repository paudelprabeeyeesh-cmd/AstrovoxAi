import React, { useState, useRef, useCallback, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'

export function DragDropList({
  items = [],
  onReorder,
  renderItem,
  keyExtractor = (item, index) => index,
  dragHandleSelector = null,
  emptyMessage = 'No items to display'
}) {
  const [draggedIndex, setDraggedIndex] = useState(null)
  const [dragOverIndex, setDragOverIndex] = useState(null)
  const dragRef = useRef(null)
  const startPosRef = useRef({ x: 0, y: 0 })

  const handleDragStart = useCallback((e, index) => {
    setDraggedIndex(index)
    startPosRef.current = { x: e.clientX, y: e.clientY }
    if (e.dataTransfer) {
      e.dataTransfer.effectAllowed = 'move'
      e.dataTransfer.setData('text/plain', String(index))
    }
  }, [])

  const handleDragOver = useCallback((e, index) => {
    e.preventDefault()
    if (e.dataTransfer) {
      e.dataTransfer.dropEffect = 'move'
    }
    setDragOverIndex(index)
  }, [])

  const handleDragLeave = useCallback(() => {
    setDragOverIndex(null)
  }, [])

  const handleDrop = useCallback((e, dropIndex) => {
    e.preventDefault()
    const dragIndex = draggedIndex
    if (dragIndex === null || dragIndex === dropIndex) {
      setDraggedIndex(null)
      setDragOverIndex(null)
      return
    }

    const newItems = [...items]
    const [moved] = newItems.splice(dragIndex, 1)
    newItems.splice(dropIndex, 0, moved)

    setDraggedIndex(null)
    setDragOverIndex(null)
    onReorder?.(newItems)
  }, [draggedIndex, items, onReorder])

  const handleDragEnd = useCallback(() => {
    setDraggedIndex(null)
    setDragOverIndex(null)
  }, [])

  useEffect(() => {
    return () => {
      setDraggedIndex(null)
      setDragOverIndex(null)
    }
  }, [])

  if (!items || items.length === 0) {
    return (
      <div style={{
        padding: '40px 20px',
        textAlign: 'center',
        color: 'var(--astrovox-text-muted)',
        fontSize: '13px'
      }}>
        {emptyMessage}
      </div>
    )
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
      <AnimatePresence>
        {items.map((item, index) => {
          const key = keyExtractor(item, index)
          const isDragging = draggedIndex === index
          const isDragOver = dragOverIndex === index && draggedIndex !== index

          return (
            <motion.div
              key={key}
              layout
              initial={{ opacity: 0, y: 10 }}
              animate={{
                opacity: isDragging ? 0.4 : 1,
                y: 0,
                scale: isDragging ? 0.98 : 1
              }}
              exit={{ opacity: 0, x: -20 }}
              transition={{ type: 'spring', damping: 20, stiffness: 300 }}
              draggable
              onDragStart={(e) => handleDragStart(e, index)}
              onDragOver={(e) => handleDragOver(e, index)}
              onDragLeave={handleDragLeave}
              onDrop={(e) => handleDrop(e, index)}
              onDragEnd={handleDragEnd}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '12px',
                padding: '12px 16px',
                backgroundColor: isDragOver ? 'var(--astrovox-surface-hover)' : 'transparent',
                border: isDragOver ? '1px dashed var(--astrovox-primary)' : '1px solid transparent',
                borderRadius: '8px',
                cursor: 'grab',
                transition: 'background-color 0.15s, border-color 0.15s',
                position: 'relative'
              }}
            >
              {dragHandleSelector && (
                <div
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    color: 'var(--astrovox-text-muted)',
                    cursor: 'grab',
                    padding: '4px'
                  }}
                >
                  <svg width="12" height="12" viewBox="0 0 12 12" fill="currentColor">
                    <circle cx="3" cy="3" r="1.5" />
                    <circle cx="9" cy="3" r="1.5" />
                    <circle cx="3" cy="9" r="1.5" />
                    <circle cx="9" cy="9" r="1.5" />
                  </svg>
                </div>
              )}
              <div style={{ flex: 1, minWidth: 0 }}>
                {renderItem ? renderItem(item, index) : (
                  <div style={{ fontSize: '13px', color: 'var(--astrovox-text)' }}>
                    {String(item)}
                  </div>
                )}
              </div>
              <div style={{
                fontSize: '10px',
                color: 'var(--astrovox-text-muted)',
                fontFamily: 'monospace'
              }}>
                {index + 1}
              </div>
            </motion.div>
          )
        })}
      </AnimatePresence>
    </div>
  )
}
