import React, { useState, useRef, useCallback, useEffect } from 'react'

export function SplitPane({
  direction = 'horizontal',
  minSize = 200,
  maxSize = 800,
  defaultLeftSize = 50,
  left,
  right
}) {
  const [leftSize, setLeftSize] = useState(defaultLeftSize)
  const [isDragging, setIsDragging] = useState(false)
  const containerRef = useRef(null)
  const startPosRef = useRef(0)
  const startSizeRef = useRef(0)

  const handleMouseDown = useCallback((e) => {
    e.preventDefault()
    setIsDragging(true)
    startPosRef.current = direction === 'horizontal' ? e.clientX : e.clientY
    startSizeRef.current = leftSize
  }, [direction, leftSize])

  useEffect(() => {
    if (!isDragging) return

    const handleMouseMove = (e) => {
      if (!containerRef.current) return
      const containerRect = containerRef.current.getBoundingClientRect()
      const currentPos = direction === 'horizontal' ? e.clientX : e.clientY
      const containerSize = direction === 'horizontal' ? containerRect.width : containerRect.height
      const delta = currentPos - startPosRef.current
      const newSize = Math.max(minSize, Math.min(maxSize, startSizeRef.current + delta))
      const percentage = (newSize / containerSize) * 100
      setLeftSize(percentage)
    }

    const handleMouseUp = () => {
      setIsDragging(false)
    }

    document.addEventListener('mousemove', handleMouseMove)
    document.addEventListener('mouseup', handleMouseUp)
    return () => {
      document.removeEventListener('mousemove', handleMouseMove)
      document.removeEventListener('mouseup', handleMouseUp)
    }
  }, [isDragging, direction, minSize, maxSize])

  const isHorizontal = direction === 'horizontal'
  const cursor = isHorizontal ? 'col-resize' : 'row-resize'

  return (
    <div
      ref={containerRef}
      style={{
        display: 'flex',
        flexDirection: isHorizontal ? 'row' : 'column',
        width: '100%',
        height: '100%',
        position: 'relative'
      }}
    >
      <div style={{
        width: isHorizontal ? `${leftSize}%` : '100%',
        height: isHorizontal ? '100%' : `${leftSize}%`,
        overflow: 'hidden',
        minWidth: isHorizontal ? minSize : undefined,
        minHeight: isHorizontal ? undefined : minSize
      }}>
        {left}
      </div>
      <div
        onMouseDown={handleMouseDown}
        style={{
          width: isHorizontal ? '6px' : '100%',
          height: isHorizontal ? '100%' : '6px',
          cursor: cursor,
          backgroundColor: isDragging ? 'var(--astrovox-primary)' : 'transparent',
          border: isDragging ? 'none' : '1px solid transparent',
          transition: isDragging ? 'none' : 'background-color 0.2s, border-color 0.2s',
          position: 'relative',
          zIndex: 10,
          flexShrink: 0
        }}
        onMouseEnter={(e) => {
          if (!isDragging) {
            e.currentTarget.style.borderColor = 'var(--astrovox-border)'
            e.currentTarget.style.backgroundColor = 'var(--astrovox-surface-hover)'
          }
        }}
        onMouseLeave={(e) => {
          if (!isDragging) {
            e.currentTarget.style.borderColor = 'transparent'
            e.currentTarget.style.backgroundColor = 'transparent'
          }
        }}
      />
      <div style={{
        width: isHorizontal ? `${100 - leftSize}%` : '100%',
        height: isHorizontal ? '100%' : `${100 - leftSize}%`,
        overflow: 'hidden',
        minWidth: isHorizontal ? minSize : undefined,
        minHeight: isHorizontal ? undefined : minSize
      }}>
        {right}
      </div>
    </div>
  )
}
